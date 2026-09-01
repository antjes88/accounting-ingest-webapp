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


def test_get_chart_of_accounts(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample account data
    WHEN the get_chart_of_accounts method is called
    THEN it should return a ChartOfAccounts instance containing all accounts,
    and specific accounts should match the expected sample data.
    """
    chart = repo_with_data.get_chart_of_accounts()

    assert isinstance(chart, model.ChartOfAccounts)
    assert len(chart.accounts) == 5
    assert cash_account in chart.accounts
    assert petty_cash_account in chart.accounts
    assert work_income_account in chart.accounts
    assert base_salary_account in chart.accounts
    assert archived_account in chart.accounts
    assert chart.get_account_by_id(cash_account.id) == cash_account  # type: ignore


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
    THEN the transaction should be successfully recorded in the database and its ID returned,
    and the transaction details and ledger entries should match the provided data.
    """
    transaction_date = date(2024, 6, 1)
    description = "Test Create Transaction"
    amount = Decimal("200.00")

    transaction_id = repo_with_data.post_new_transaction(
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

    assert transaction_id == repo_with_data.get_max_transaction_id()
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


def test_get_transactions(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample transaction data
    WHEN the get_transactions method is called
    THEN it should return a list of Transaction entities with correct lines and attributes.
    """
    transactions = repo_with_data.get_transactions()
    t = transactions[0]

    assert len(transactions) == 1
    assert t.id == 1
    assert t.date == date(2024, 1, 1)
    assert t.description == "Test"
    assert t.amount == Decimal("100.00")
    assert len(t._lines) == 2
    assert t.get_debit_account_id() == petty_cash_account.id
    assert t.get_credit_account_id() == base_salary_account.id


def test_get_transactions_with_matching_date_filters(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository initialized with a transaction on 2024-01-01
    WHEN the get_transactions method is called with matching start_date and end_date filters
    THEN it should return the matching Transaction entity.
    """
    transactions_exact = repo_with_data.get_transactions(
        start_date=date(2024, 1, 1), end_date=date(2024, 1, 1)
    )
    transactions_from = repo_with_data.get_transactions(start_date=date(2023, 12, 31))
    transactions_to = repo_with_data.get_transactions(end_date=date(2024, 1, 2))

    assert len(transactions_exact) == 1
    assert transactions_exact[0].id == 1
    assert len(transactions_from) == 1
    assert len(transactions_to) == 1


def test_get_transactions_with_non_matching_date_filters(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository initialized with a transaction on 2024-01-01
    WHEN the get_transactions method is called with a date range outside the transaction date
    THEN it should return an empty list.
    """
    transactions_past = repo_with_data.get_transactions(
        start_date=date(2023, 1, 1), end_date=date(2023, 12, 31)
    )
    transactions_future = repo_with_data.get_transactions(start_date=date(2024, 1, 2))

    assert len(transactions_past) == 0
    assert len(transactions_future) == 0


@pytest.mark.parametrize(
    "start_date, end_date, expected_where_clause, expected_params",
    [
        pytest.param(
            None,
            None,
            "",
            None,
            id="no_dates",
        ),
        pytest.param(
            date(2024, 1, 1),
            None,
            "WHERE t.transaction_date >= %s",
            (date(2024, 1, 1),),
            id="start_date_only",
        ),
        pytest.param(
            None,
            date(2024, 12, 31),
            "WHERE t.transaction_date <= %s",
            (date(2024, 12, 31),),
            id="end_date_only",
        ),
        pytest.param(
            date(2024, 1, 1),
            date(2024, 12, 31),
            "WHERE t.transaction_date >= %s AND t.transaction_date <= %s",
            (date(2024, 1, 1), date(2024, 12, 31)),
            id="both_dates_different",
        ),
        pytest.param(
            date(2024, 6, 15),
            date(2024, 6, 15),
            "WHERE t.transaction_date >= %s AND t.transaction_date <= %s",
            (date(2024, 6, 15), date(2024, 6, 15)),
            id="same_start_and_end_date",
        ),
    ],
)
def test_where_clause_for_date_range(
    postgres_repo: PostgresRepository,
    start_date: Optional[date],
    end_date: Optional[date],
    expected_where_clause: str,
    expected_params: Optional[tuple[date, ...]],
):
    """
    GIVEN start_date and end_date parameters
    WHEN _where_clause_for_date_range is called on PostgresRepository
    THEN it should return the expected SQL WHERE clause string and parameter tuple.
    """
    where_clause, params = postgres_repo._where_clause_for_date_range(
        start_date=start_date, end_date=end_date
    )

    assert where_clause == expected_where_clause
    assert params == expected_params


def test_delete_transaction(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository initialized with sample transaction data
    WHEN the delete_transaction method is called with a transaction ID
    THEN the transaction and its ledger entries should be deleted from the database.
    """
    assert len(repo_with_data.get_transactions()) == 1

    repo_with_data.delete_transaction(transaction_id=1)

    assert len(repo_with_data.get_transactions()) == 0
    assert (
        repo_with_data.postgres_client.query(
            f"SELECT * FROM {repo_with_data.transactions_table} WHERE transaction_id = 1"
        )
        == []
    )
    assert (
        repo_with_data.postgres_client.query(
            f"SELECT * FROM {repo_with_data.ledger_entries_table} WHERE transaction_id = 1"
        )
        == []
    )
