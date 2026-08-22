from flask.testing import FlaskClient
import pytest
import datetime as dt
from decimal import Decimal
from typing import Optional
from unittest.mock import patch

from repository import PostgresRepository
from src import model
from tests.helpers.sample_data import cash_account


def test_new_transaction_page_is_reached(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in client
    WHEN the client requests the new transaction page
    THEN the response status code should be 200 and the new transaction form HTML should be present.
    """
    response = client_logged_in.get(
        "/accounting/new_transaction",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--new_transaction_form this comment is to check that it is reached on test-->"
        in response.data
    )


def test_new_account_page_is_reached(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in client
    WHEN the client requests the new account page
    THEN the response status code should be 200 and the new account form HTML should be present.
    """
    response = client_logged_in.get(
        "/accounting/new_account",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--new_account_form this comment is to check that it is reached on test-->"
        in response.data
    )


def test_new_transaction_post(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and a repository with existing data
    WHEN the client posts valid transaction data to the new transaction endpoint
    THEN the response status code should be 200, a success message should be displayed, and the transaction should be correctly recorded in the database.
    """
    transaction_date = dt.date(2024, 1, 1)
    description = "Test Post new transaction"
    amount = Decimal("999.87")

    response = client_logged_in.post(
        "/accounting/new_transaction",
        data={
            "type_debit": str(model.AccountType.ASSET.id),
            "account_debit": "2",  # Petty Cash account ID
            "type_credit": str(model.AccountType.REVENUE.id),
            "account_credit": "4",  # Base Salary account ID
            "amount": amount,
            "description": description,
            "date": transaction_date.strftime("%Y-%m-%d"),
        },
        follow_redirects=True,
    )
    transaction_id = repo_with_data.get_max_transaction_id()

    assert response.status_code == 200
    assert b"Transaction recorded successfully!" in response.data
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_date, transaction_description FROM {repo_with_data.transactions_table} WHERE transaction_id = {transaction_id}"
    ) == [(transaction_id, transaction_date, description)]
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, account_id, entry_type_id, amount "
        f"FROM {repo_with_data.ledger_entries_table} "
        f"WHERE transaction_id = {transaction_id} ORDER BY entry_type_id"
    ) == [
        (transaction_id, 4, 1, amount),
        (transaction_id, 2, 2, amount),
    ]


@pytest.mark.parametrize(
    "new_account_name, new_account_type, is_physical, is_archived, father_account",
    [
        ("New Savings Account", model.AccountType.ASSET, True, False, None),
        ("New Checking Account", model.AccountType.ASSET, True, False, cash_account),
    ],
)
def test_new_account_post(
    new_account_name: str,
    new_account_type: model.AccountType,
    is_physical: bool,
    is_archived: bool,
    father_account: Optional[model.Account],
    client_logged_in: FlaskClient,
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a logged-in client and a repository with existing data
    WHEN the client posts valid account data to the new account endpoint
    THEN the response status code should be 200, a success message should be displayed,
    and the account should be correctly recorded in the database.
    """

    response = client_logged_in.post(
        "/accounting/new_account",
        data={
            "name": new_account_name,
            "account_type": str(new_account_type.id),
            "is_physical": "True" if is_physical else "False",
            "is_archived": "True" if is_archived else "False",
            "father_account": str(father_account.id) if father_account else None,
        },
        follow_redirects=True,
    )
    account_id = repo_with_data.get_max_account_id()

    assert response.status_code == 200
    assert b"Account created successfully!" in response.data
    assert repo_with_data.postgres_client.query(
        f"SELECT account_id, account_type_id, account_name, is_physical, is_archived, father_account_id "
        f"FROM {repo_with_data.accounts_table} WHERE account_id = {account_id}"
    ) == [
        (
            account_id,
            new_account_type.id,
            new_account_name,
            is_physical,
            is_archived,
            father_account.id if father_account else None,
        )
    ]


def test_new_transaction_post_handles_value_error(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client submitting transaction data
    WHEN the services layer raises a ValueError (business validation failure)
    THEN the response status should be 200
    and the warning flash message should be displayed.
    """
    with patch(
        "src.entrypoints.flaskapp.blueprints.accounting.routes.services.record_new_transaction",
        side_effect=ValueError("Test validation failure"),
    ):
        response = client_logged_in.post(
            "/accounting/new_transaction",
            data={
                "type_debit": str(model.AccountType.ASSET.id),
                "account_debit": "2",
                "type_credit": str(model.AccountType.REVENUE.id),
                "account_credit": "4",
                "amount": "100.00",
                "description": "Test failure",
                "date": "2024-01-01",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Error recording transaction: Test validation failure" in response.data


def test_new_transaction_post_handles_unexpected_exception(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client submitting transaction data
    WHEN the services layer raises an unexpected Exception
    THEN the response status should be 200
    and the generic error flash message should be displayed.
    """
    with patch(
        "src.entrypoints.flaskapp.blueprints.accounting.routes.services.record_new_transaction",
        side_effect=Exception("Database crash"),
    ):
        response = client_logged_in.post(
            "/accounting/new_transaction",
            data={
                "type_debit": str(model.AccountType.ASSET.id),
                "account_debit": "2",
                "type_credit": str(model.AccountType.REVENUE.id),
                "account_credit": "4",
                "amount": "100.00",
                "description": "Test failure",
                "date": "2024-01-01",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert (
        b"An unexpected error occurred while recording the transaction."
        in response.data
    )


def test_new_account_post_handles_value_error(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client submitting account data
    WHEN the services layer raises a ValueError (business validation failure)
    THEN the response status should be 200
    and the warning flash message should be displayed.
    """
    with patch(
        "src.entrypoints.flaskapp.blueprints.accounting.routes.services.record_new_account",
        side_effect=ValueError("Invalid hierarchy error"),
    ):
        response = client_logged_in.post(
            "/accounting/new_account",
            data={
                "name": "Invalid Account",
                "account_type": str(model.AccountType.ASSET.id),
                "is_physical": "True",
                "is_archived": "False",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Error creating account: Invalid hierarchy error" in response.data


def test_new_account_post_handles_unexpected_exception(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client submitting account data
    WHEN the services layer raises an unexpected Exception
    THEN the response status should be 200
    and the generic error flash message should be displayed.
    """
    with patch(
        "src.entrypoints.flaskapp.blueprints.accounting.routes.services.record_new_account",
        side_effect=Exception("Database crash"),
    ):
        response = client_logged_in.post(
            "/accounting/new_account",
            data={
                "name": "Crash Account",
                "account_type": str(model.AccountType.ASSET.id),
                "is_physical": "True",
                "is_archived": "False",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"An unexpected error occurred while creating the account." in response.data
