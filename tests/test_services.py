from datetime import date
from decimal import Decimal

from src.repository import PostgresRepository
from src.services import record_new_transaction
from src import model
from tests.helpers.sample_data import (
    petty_cash_account,
    work_income_account,
)


def test_record_new_transaction(repo_with_data: PostgresRepository):
    transaction_date = date(2001, 6, 1)
    description = "Test services new trans"
    amount = Decimal("123.98")

    record_new_transaction(
        repo_with_data,
        transaction=model.Transaction(
            id=None,
            date=transaction_date,
            description=description,
            amount=amount,
        ),
        debit_account=petty_cash_account,
        credit_account=work_income_account,
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
