from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import dataclass

from src import model
from src.utils.postgresql_client import PostgresGCPClient
from src.utils import sql_queries


class AbstractRepository(ABC):

    @abstractmethod
    def get_accounts(self) -> List[model.Account]:
        raise NotImplementedError

    @abstractmethod
    def get_max_transaction_id(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_entry_types(self) -> List[model.EntryType]:
        raise NotImplementedError

    @abstractmethod
    def record_new_transaction(
        self,
        transaction: model.Transaction,
        debit_account: model.Account,
        credit_account: model.Account,
    ):

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

    def get_entry_types(self) -> List[model.EntryType]:
        rows = self.postgres_client.query(
            sql_queries.SELECT_ENTRY_TYPES.format(
                entry_types_table=self.entry_types_table
            )
        )

        return [model.EntryType(name=row[0], id=row[1]) for row in rows]

    def get_accounts(self) -> List[model.Account]:

        accounts = {}

        father_rows = self.postgres_client.query(
            sql_queries.SELECT_FATHER_ACCOUNTS.format(
                accounts_table=self.accounts_table,
                account_types_table=self.account_types_table,
            )
        )
        for row in father_rows:
            account = model.Account(
                id=row[0],
                account_type=model.AccountType(row[1], row[2]),
                name=row[3],
                is_physical=row[4],
                is_archived=row[5],
            )
            accounts[account.id] = account

        children_rows = self.postgres_client.query(
            sql_queries.SELECT_CHILDREN_ACCOUNTS.format(
                accounts_table=self.accounts_table,
                account_types_table=self.account_types_table,
            )
        )

        for row in children_rows:
            account = model.Account(
                id=row[0],
                account_type=model.AccountType(row[1], row[2]),
                name=row[3],
                is_physical=row[4],
                is_archived=row[5],
            )
            accounts[account.id] = account

        for row in children_rows:
            father_id = row[6]
            if father_id in accounts:
                accounts[row[0]].father_account = accounts[father_id]

        return list(accounts.values())

    def get_max_transaction_id(self) -> int:

        return self.postgres_client.query(
            sql_queries.SELECT_MAX_ID_TRANSACTIONS.format(
                transactions_table=self.transactions_table
            )
        )[0][0]

    def record_new_transaction(
        self,
        transaction: model.Transaction,
        debit_account: model.Account,
        credit_account: model.Account,
    ):
        entry_types = {
            entry_type.name.lower(): entry_type.id
            for entry_type in self.get_entry_types()
        }
        sql_statement = f"""
        INSERT INTO {self.transactions_table} 
        (transaction_id, transaction_date, transaction_description)
        VALUES 
        ({transaction.id}, '{transaction.date}', '{transaction.description}');

        INSERT INTO {self.ledger_entries_table} 
        (transaction_id, account_id, entry_type_id, amount)
        VALUES 
        ({transaction.id}, {debit_account.id}, {entry_types['debit']}, {transaction.amount}),
        ({transaction.id}, {credit_account.id}, {entry_types['credit']}, {transaction.amount});
        """

        self.postgres_client.execute(sql_statement)
