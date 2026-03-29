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
    table = SqlTable(schema="test_schema", name="test_table")
    assert str(table) == "test_schema.test_table"


def test_get_entry_types(postgres_repo: PostgresRepository):
    entry_types = postgres_repo.get_entry_types()

    assert len(entry_types) == 2
    assert any(et.name == "Debit" for et in entry_types)
    assert any(et.name == "Credit" for et in entry_types)


def test_get_accounts(repo_with_data: PostgresRepository):
    accounts = repo_with_data.get_accounts()

    assert len(accounts) == 4
    assert next((acc for acc in accounts if acc.id == 1), None) == cash_account
    assert next((acc for acc in accounts if acc.id == 2), None) == petty_cash_account
    assert next((acc for acc in accounts if acc.id == 3), None) == work_income_account
    assert next((acc for acc in accounts if acc.id == 4), None) == base_salary_account


def test_get_max_transaction_id(repo_with_data: PostgresRepository):

    assert repo_with_data.get_max_transaction_id() == 1


def test_record_new_transaction(repo_with_data: PostgresRepository):
    transaction_id = 5
    transaction_date = date(2024, 6, 1)
    description = "Test Create Transaction"
    amount = Decimal("200.00")

    repo_with_data.record_new_transaction(
        model.Transaction(
            id=transaction_id,
            date=transaction_date,
            description=description,
            amount=amount,
        ),
        debit_account=petty_cash_account,
        credit_account=work_income_account,
    )

    assert repo_with_data.get_max_transaction_id() == transaction_id
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
