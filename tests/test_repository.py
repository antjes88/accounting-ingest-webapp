from datetime import date
from decimal import Decimal

from src.repository import SqlTable, PostgresRepository
from src import model
from tests.helpers.sample_data import (
    cash_account,
    petty_cash_account,
    work_income_account,
    base_salary_account,
)


def test_sql_table_str():
    """
    GIVEN a SqlTable object with a schema and a name
    WHEN its string representation is requested
    THEN it should return the schema and name concatenated with a dot.
    """
    table = SqlTable(schema="test_schema", name="test_table")
    assert str(table) == "test_schema.test_table"


def test_get_entry_types(postgres_repo: PostgresRepository):
    """
    GIVEN an initialized PostgresRepository
    WHEN the get_entry_types method is called
    THEN it should return a list containing exactly two EntryType objects,
    one for "Debit" and one for "Credit".
    """
    entry_types = postgres_repo.get_entry_types()

    assert len(entry_types) == 2
    assert any(et.name == "Debit" for et in entry_types)
    assert any(et.name == "Credit" for et in entry_types)


def test_get_accounts(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample account data
    WHEN the get_accounts method is called
    THEN it should return a list of all accounts,
    and specific accounts should match the expected sample data.
    """
    accounts = repo_with_data.get_accounts()

    assert len(accounts) == 4
    assert next((acc for acc in accounts if acc.id == 1), None) == cash_account
    assert next((acc for acc in accounts if acc.id == 2), None) == petty_cash_account
    assert next((acc for acc in accounts if acc.id == 3), None) == work_income_account
    assert next((acc for acc in accounts if acc.id == 4), None) == base_salary_account


def test_get_max_transaction_id(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample transaction data
    WHEN the get_max_transaction_id method is called
    THEN it should return the maximum transaction ID present in the database.
    """
    assert repo_with_data.get_max_transaction_id() == 1


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
            amount=amount,
            lines=[
                model.TransactionLine(
                    account=petty_cash_account,
                    amount=amount,
                    entry_type=model.EntryType(id=1, name="Debit"),
                ),
                model.TransactionLine(
                    account=work_income_account,
                    amount=amount,
                    entry_type=model.EntryType(id=2, name="Credit"),
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
        (transaction_id, work_income_account.id, 1, amount),
        (transaction_id, petty_cash_account.id, 2, amount),
    ]
