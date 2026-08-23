from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

from src import model
from src.utils.postgresql_client import PostgresGCPClient
from src.utils import sql_queries


class AbstractRepository(ABC):

    @abstractmethod
    def get_chart_of_accounts(self) -> model.ChartOfAccounts:
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
