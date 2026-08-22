from datetime import date
from decimal import Decimal
from typing import Optional
import pytest

from src.repository import SqlTable, PostgresRepository
from src import model
from tests.helpers.sample_data import (
    cash_account,
    petty_cash_account,
    work_income_account,
    base_salary_account,
    archived_account,
)


def test_entry_type_enum_and_db_alignment(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository
    WHEN the EntryType enum values are compared with the database's entry_types table
    THEN their IDs and names should be correctly aligned.
    """
    db_entry_types = repo_with_data.postgres_client.query(
        f"SELECT entry_type_id, entry_type_name FROM {repo_with_data.entry_types_table} ORDER BY entry_type_id"
    )

    enum_entry_types = sorted(
        [(entry.id, entry.display_name) for entry in model.EntryType],
        key=lambda x: x[0],
    )

    assert len(db_entry_types) == len(enum_entry_types)
    assert db_entry_types == enum_entry_types


def test_account_type_enum_and_db_alignment(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository
    WHEN the AccountType enum values are compared with the database's account_types table
    THEN their IDs and names should be correctly aligned.
    """
    db_account_types = repo_with_data.postgres_client.query(
        f"SELECT account_type_id, account_type_name FROM {repo_with_data.account_types_table} ORDER BY account_type_id"
    )

    enum_account_types = sorted(
        [(entry.id, entry.display_name) for entry in model.AccountType],
        key=lambda x: x[0],
    )

    assert len(db_account_types) == len(enum_account_types)
    assert db_account_types == enum_account_types


def test_sql_table_str():
    """
    GIVEN a SqlTable object with a schema and a name
    WHEN its string representation is requested
    THEN it should return the schema and name concatenated with a dot.
    """
    table = SqlTable(schema="test_schema", name="test_table")
    assert str(table) == "test_schema.test_table"


def test_get_accounts(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample account data
    WHEN the get_accounts method is called
    THEN it should return a list of all accounts,
    and specific accounts should match the expected sample data.
    """
    accounts = repo_with_data.get_accounts()

    assert len(accounts) == 5
    assert next((acc for acc in accounts if acc.id == 1), None) == cash_account
    assert next((acc for acc in accounts if acc.id == 2), None) == petty_cash_account
    assert next((acc for acc in accounts if acc.id == 3), None) == work_income_account
    assert next((acc for acc in accounts if acc.id == 4), None) == base_salary_account
    assert next((acc for acc in accounts if acc.id == 5), None) == archived_account


def test_get_max_transaction_id(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample transaction data
    WHEN the get_max_transaction_id method is called
    THEN it should return the maximum transaction ID present in the database.
    """
    assert repo_with_data.get_max_transaction_id() == 1


def test_get_max_account_id(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample account data
    WHEN the get_max_account_id method is called
    THEN it should return the maximum account ID present in the database.
    """
    assert repo_with_data.get_max_account_id() == 5


def test_record_new_transaction(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository with existing data and a valid Transaction object
    WHEN the post_new_transaction method is called with the Transaction object
    THEN the transaction should be successfully recorded in the database,
    and the transaction details and ledger entries should match the provided data.
    """
    transaction_date = date(2024, 6, 1)
    description = "Test Create Transaction"
    amount = Decimal("200.00")

    repo_with_data.post_new_transaction(
        model.Transaction(
            id=None,
            date=transaction_date,
            description=description,
            lines=[
                model.TransactionLine(
                    account=petty_cash_account,
                    amount=amount,
                    entry_type=model.EntryType.DEBIT,
                ),
                model.TransactionLine(
                    account=base_salary_account,
                    amount=amount,
                    entry_type=model.EntryType.CREDIT,
                ),
            ],
        )
    )
    transaction_id = repo_with_data.get_max_transaction_id()

    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_date, transaction_description FROM {repo_with_data.transactions_table} WHERE transaction_id = {transaction_id}"
    ) == [(transaction_id, transaction_date, description)]
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, account_id, entry_type_id, amount "
        f"FROM {repo_with_data.ledger_entries_table} "
        f"WHERE transaction_id = {transaction_id} ORDER BY entry_type_id"
    ) == [
        (transaction_id, base_salary_account.id, 1, amount),
        (transaction_id, petty_cash_account.id, 2, amount),
    ]


@pytest.mark.parametrize(
    "new_account_name, new_account_type, is_physical, is_archived, father_account",
    [
        ("New Savings Account", model.AccountType.ASSET, True, False, None),
        ("New Checking Account", model.AccountType.ASSET, True, False, cash_account),
    ],
)
def test_post_new_account(
    new_account_name: str,
    new_account_type: model.AccountType,
    is_physical: bool,
    is_archived: bool,
    father_account: Optional[model.Account],
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository and a new Account object
    WHEN the post_new_account method is called with the Account object
    THEN the account should be successfully recorded in the database,
    and its details should match the provided data.
    """
    new_account = model.Account(
        id=None,  # ID will be generated by the repository
        account_type=new_account_type,
        name=new_account_name,
        is_physical=is_physical,
        is_archived=is_archived,
        father_account=father_account,
    )

    repo_with_data.post_new_account(new_account)

    max_account_id = repo_with_data.get_max_account_id()
    retrieved_account_data = repo_with_data.postgres_client.query(
        f"SELECT account_id, account_type_id, account_name, is_physical, is_archived "
        f"FROM {repo_with_data.accounts_table} WHERE account_id = {max_account_id}"
    )

    assert len(retrieved_account_data) == 1
    assert retrieved_account_data[0] == (
        max_account_id,
        new_account_type.id,
        new_account_name,
        is_physical,
        is_archived,
    )
