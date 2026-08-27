from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src import model
from src.utils.postgresql_client import PostgresGCPClient
from src.utils import sql_queries


class AbstractRepository(ABC):

    @abstractmethod
    def get_chart_of_accounts(self) -> model.ChartOfAccounts:
        raise NotImplementedError

    @abstractmethod
    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[model.Transaction]:
        raise NotImplementedError

    @abstractmethod
    def post_new_transaction(
        self,
        transaction: model.Transaction,
    ) -> None:

        raise NotImplementedError

    @abstractmethod
    def post_new_account(
        self,
        account: model.Account,
    ) -> None:
        raise NotImplementedError


@dataclass
class SqlTable:
    schema: str
    name: str

    def __str__(self) -> str:
        return f"{self.schema}.{self.name}"


class PostgresRepository(AbstractRepository):
    accounts_table = SqlTable(schema="accounting", name="accounts")
    account_types_table = SqlTable(schema="accounting", name="account_types")
    transactions_table = SqlTable(schema="accounting", name="transactions")
    entry_types_table = SqlTable(schema="accounting", name="entry_types")
    ledger_entries_table = SqlTable(schema="accounting", name="ledger_entries")

    def __init__(self, postgres_client: PostgresGCPClient):
        self.postgres_client = postgres_client

    def _load_accounts(self) -> List[model.Account]:

        accounts: dict[int, model.Account] = {}
        father_accounts: dict[int, model.Account] = {}

        father_rows = self.postgres_client.query(
            sql_queries.SELECT_FATHER_ACCOUNTS.format(
                accounts_table=self.accounts_table,
                account_types_table=self.account_types_table,
            )
        )
        for row in father_rows:
            account = model.Account(
                id=row[0],
                account_type=model.AccountType.from_id(row[1]),
                name=row[3],
                is_physical=row[4],
                is_archived=row[5],
            )
            father_accounts[account.id] = account  # type: ignore

        children_rows = self.postgres_client.query(
            sql_queries.SELECT_CHILDREN_ACCOUNTS.format(
                accounts_table=self.accounts_table,
                account_types_table=self.account_types_table,
            )
        )
        for row in children_rows:
            account = model.Account(
                id=row[0],
                account_type=model.AccountType.from_id(row[1]),
                name=row[3],
                is_physical=row[4],
                is_archived=row[5],
                father_account=father_accounts.get(row[6]),
            )
            accounts[account.id] = account  # type: ignore

        return list({**accounts, **father_accounts}.values())

    def get_chart_of_accounts(self) -> model.ChartOfAccounts:
        return model.ChartOfAccounts(self._load_accounts())

    def _where_clause_for_date_range(
        self, start_date: Optional[date], end_date: Optional[date]
    ) -> tuple[str, Optional[tuple[date, ...]]]:
        conditions: list[str] = []
        params_list: list[date] = []
        if start_date:
            conditions.append("t.transaction_date >= %s")
            params_list.append(start_date)
        if end_date:
            conditions.append("t.transaction_date <= %s")
            params_list.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params = tuple(params_list) if params_list else None

        return where_clause, params

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[model.Transaction]:

        where_clause, params = self._where_clause_for_date_range(start_date, end_date)
        rows = self.postgres_client.query(
            sql_queries.SELECT_ALL_TRANSACTIONS.format(
                transactions_table=self.transactions_table,
                ledger_entries_table=self.ledger_entries_table,
                where_clause=where_clause,
            ),
            params=params,
        )
        chart = self.get_chart_of_accounts()

        transactions_dict: dict[
            int, tuple[date, Optional[str], list[model.TransactionLine]]
        ] = {}
        for row in rows:
            t_id, t_date, t_desc, acc_id, entry_type_id, amount = row
            if t_id not in transactions_dict:
                transactions_dict[t_id] = (t_date, t_desc, [])
            account = chart.get_account_by_id(acc_id)
            entry_type = (
                model.EntryType.DEBIT
                if entry_type_id == model.EntryType.DEBIT.id
                else model.EntryType.CREDIT
            )
            transactions_dict[t_id][2].append(
                model.TransactionLine(
                    account=account,
                    amount=Decimal(str(amount)),
                    entry_type=entry_type,
                )
            )

        transactions: list[model.Transaction] = []
        for t_id, (t_date, t_desc, lines) in transactions_dict.items():
            transactions.append(
                model.Transaction(
                    id=t_id,
                    date=t_date,
                    description=t_desc,
                    lines=lines,
                )
            )
        return transactions

    def get_max_transaction_id(self) -> int:

        return self.postgres_client.query(
            sql_queries.SELECT_MAX_ID_TRANSACTIONS.format(
                transactions_table=self.transactions_table
            )
        )[0][0]

    def get_max_account_id(self) -> int:
        return self.postgres_client.query(
            sql_queries.SELECT_MAX_ID_ACCOUNTS.format(
                accounts_table=self.accounts_table
            )
        )[0][0]

    def post_new_transaction(self, transaction: model.Transaction) -> None:

        transaction_id = self.get_max_transaction_id() + 1

        self.postgres_client.execute(
            sql_queries.INSERT_NEW_TRANSACTION.format(
                transaction_table=self.transactions_table,
                ledger_entries_table=self.ledger_entries_table,
            ),
            params=(
                transaction_id,
                transaction.date,
                transaction.description,
                transaction_id,
                transaction.get_debit_account_id(),
                model.EntryType.DEBIT.id,
                transaction.amount,
                transaction_id,
                transaction.get_credit_account_id(),
                model.EntryType.CREDIT.id,
                transaction.amount,
            ),
        )

    def post_new_account(self, account: model.Account) -> None:
        account_id = self.get_max_account_id() + 1

        self.postgres_client.execute(
            sql_queries.INSERT_NEW_ACCOUNT.format(
                accounts_table=self.accounts_table,
            ),
            params=(
                account_id,
                account.father_account.id if account.father_account else None,
                account.account_type.id,
                account.name,
                account.is_physical,
                account.is_archived,
            ),
        )
