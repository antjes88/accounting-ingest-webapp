from flask.testing import FlaskClient
import pytest
import datetime as dt
from decimal import Decimal
from typing import Optional, Any
from unittest.mock import patch

from repository import PostgresRepository
from src import model, services
from src.entrypoints.webapp.app import server
from src.entrypoints.webapp.blueprints.accounting.forms import (
    DeleteTransactionForm,
    NonPhysicalValuationFilterForm,
    NonPhysicalAccountOptionDTO,
    NonPhysicalAccountOptionDTO,
)
from src.dto import CreateAccountDTO, CreateTransactionDTO
from tests.helpers.sample_data import cash_account, base_salary_account


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
    assert (
        f"Transaction recorded successfully! Transaction ID: {transaction_id}".encode()
        in response.data
    )
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
        "src.entrypoints.webapp.blueprints.accounting.routes.services.record_new_transaction",
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
        "src.entrypoints.webapp.blueprints.accounting.routes.services.record_new_transaction",
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
        "src.entrypoints.webapp.blueprints.accounting.routes.services.record_new_account",
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
        "src.entrypoints.webapp.blueprints.accounting.routes.services.record_new_account",
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


def test_transactions_page_is_reached(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and a repository with sample transactions
    WHEN the client requests the transactions page ("/accounting/transactions")
    THEN the response status code should be 200, the table header should be rendered,
    and transaction data should be visible.
    """
    response = client_logged_in.get(
        "/accounting/transactions",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--transactions_list this comment is to check that it is reached on test-->"
        in response.data
    )


def test_transactions_page_empty_state(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and an empty transactions list
    WHEN the client requests the transactions page
    THEN the empty state message should be displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.get(
            "/accounting/transactions",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"No transactions found for the selected period." in response.data


def test_transactions_page_with_valid_date_filter(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and a repository with a transaction on 2024-01-01
    WHEN the client queries the transactions page with a matching date filter
    THEN the response status should be 200 and the transaction details should be present.
    """
    response = client_logged_in.get(
        "/accounting/transactions?start_date=2024-01-01&end_date=2024-01-31",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Petty Cash" in response.data
    assert "£100.00".encode("utf-8") in response.data


def test_transactions_page_with_non_matching_date_filter(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and a repository with a transaction on 2024-01-01
    WHEN the client queries the transactions page with a date range with no matching transactions
    THEN the response status should be 200 and the empty state message should be displayed.
    """
    response = client_logged_in.get(
        "/accounting/transactions?start_date=1900-01-01&end_date=1900-01-31",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"No transactions found for the selected period." in response.data


def test_transactions_page_handles_unexpected_exception(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client
    WHEN services.get_all_transactions raises an unexpected Exception
    THEN an error flash message should be displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        side_effect=Exception("Database connection failure"),
    ):
        response = client_logged_in.get(
            "/accounting/transactions",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"An unexpected error occurred while loading transactions." in response.data


def test_transactions_page_renders_delete_form(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in client
    WHEN the client requests the transactions page
    THEN the response status should be 200 and the delete form and button markers should be present.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.get(
            "/accounting/transactions",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert (
        b"<!--delete_transaction_form this comment is to check that it is reached on test-->"
        in response.data
    )
    assert (
        b"<!--delete_transaction_button this comment is to check that it is reached on test-->"
        in response.data
    )


def test_delete_transaction_post_success(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in client
    WHEN the client posts a valid transaction ID to the delete transaction endpoint
    THEN the response status should be 200, a success flash message displayed,
    and services.delete_transaction should be called.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.delete_transaction"
    ) as mock_delete, patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.post(
            "/accounting/delete_transaction",
            data={"transaction_id": "1"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Transaction deleted successfully!" in response.data
    mock_delete.assert_called_once()


def test_delete_transaction_post_handles_value_error(
    client_logged_in: FlaskClient,
):
    """
    GIVEN a logged-in client submitting a delete transaction request
    WHEN the services layer raises a ValueError
    THEN the response status should be 200 and a warning flash message displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.delete_transaction",
        side_effect=ValueError("Invalid transaction ID: -1"),
    ), patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.post(
            "/accounting/delete_transaction",
            data={"transaction_id": "-1"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Error deleting transaction: Invalid transaction ID: -1" in response.data


def test_delete_transaction_post_handles_unexpected_exception(
    client_logged_in: FlaskClient,
):
    """
    GIVEN a logged-in client submitting a delete transaction request
    WHEN the services layer raises an unexpected Exception
    THEN the response status should be 200 and a generic error flash message displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.delete_transaction",
        side_effect=Exception("Database failure"),
    ), patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.post(
            "/accounting/delete_transaction",
            data={"transaction_id": "1"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert (
        b"An unexpected error occurred while deleting the transaction." in response.data
    )


def test_delete_transaction_post_handles_form_validation_failure(
    client_logged_in: FlaskClient,
):
    """
    GIVEN a logged-in client submitting a delete request without required transaction_id
    WHEN the form validation fails
    THEN the response status should be 200 and a warning flash message displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_all_transactions",
        return_value=[],
    ):
        response = client_logged_in.post(
            "/accounting/delete_transaction",
            data={},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Invalid transaction selection." in response.data


@pytest.mark.parametrize(
    "invalid_data",
    [
        pytest.param("not_an_int", id="value_error_string"),
        pytest.param("12.34", id="value_error_float_string"),
        pytest.param([1, 2, 3], id="type_error_list"),
        pytest.param({"id": 1}, id="type_error_dict"),
        pytest.param(None, id="type_error_none"),
    ],
)
def test_delete_transaction_form_to_dto_raises_value_error_on_invalid_id(
    webapp_client: FlaskClient,
    invalid_data: Any,
):
    """
    GIVEN a DeleteTransactionForm with invalid non-integer data causing ValueError or TypeError
    WHEN to_dto method is called
    THEN a ValueError should be raised with the message 'Transaction ID must be a valid integer.'
    """
    with server.test_request_context():
        form = DeleteTransactionForm()
        form.transaction_id.data = invalid_data

        with pytest.raises(ValueError, match="Transaction ID must be a valid integer."):
            form.to_dto()


def test_non_physical_accounts_page_is_reached(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client
    WHEN the client requests the non-physical accounts valuation page
    THEN the response status code should be 200 and the HTML test comment should be present.
    """
    response = client_logged_in.get(
        "/accounting/non_physical_accounts",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--non_physical_accounts_valuation this comment is to check that it is reached on test-->"
        in response.data
    )


def test_non_physical_accounts_page_empty_state(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and no non-physical accounts configured
    WHEN the client requests the non-physical accounts valuation page
    THEN the empty state card should be rendered with instructions to create an account.
    """
    response = client_logged_in.get(
        "/accounting/non_physical_accounts",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert b"No Non-Physical Accounts Found" in response.data


def test_non_physical_accounts_page_with_data(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and a repository with a non-physical account and transactions
    WHEN the client requests the non-physical accounts valuation page
    THEN the valuation progression and account summary should be displayed.
    """

    services.record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Crypto Fund",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    chart = repo_with_data.get_chart_of_accounts()
    crypto = chart.get_account_by_name("Crypto Fund")
    assert crypto and crypto.id

    services.record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=dt.date(2024, 1, 15),
            amount=Decimal("250.00"),
            debit_account_id=crypto.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )

    response = client_logged_in.get(
        "/accounting/non_physical_accounts",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        b"<!--non_physical_accounts_dnd_filter this comment is to check that the drag and drop filter is reached on test-->"
        in response.data
    )
    assert (
        b"<!--non_physical_accounts_default_persistence this comment is to check that default persistence controls are reached on test-->"
        in response.data
    )
    assert b"dnd-included-zone" in response.data
    assert b"dnd-excluded-zone" in response.data
    assert b"dnd-btn-save-default" in response.data
    assert (
        b"<!--non_physical_accounts_chart this comment is to check that the chart is reached on test-->"
        in response.data
    )
    assert b"nonPhysicalValuationChart" in response.data
    assert b"valuationChartData" in response.data
    assert b"Crypto Fund" in response.data
    assert b"250.00" in response.data


def test_non_physical_accounts_page_handles_value_error(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client requesting non-physical accounts valuation
    WHEN the services layer raises a ValueError
    THEN the response status should be 200 and a warning flash message displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_non_physical_accounts_valuation",
        side_effect=ValueError("Test valuation validation error"),
    ):
        response = client_logged_in.get(
            "/accounting/non_physical_accounts",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Error loading valuation: Test valuation validation error" in response.data


def test_non_physical_accounts_page_handles_unexpected_exception(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client requesting non-physical accounts valuation
    WHEN the services layer raises an unexpected Exception
    THEN the response status should be 200 and a generic error flash message displayed.
    """
    with patch(
        "src.entrypoints.webapp.blueprints.accounting.routes.services.get_non_physical_accounts_valuation",
        side_effect=Exception("Database crash"),
    ):
        response = client_logged_in.get(
            "/accounting/non_physical_accounts",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert (
        b"An unexpected error occurred while loading non-physical accounts valuation."
        in response.data
    )


def test_non_physical_valuation_filter_form_to_dto(webapp_client: FlaskClient):
    """
    GIVEN a NonPhysicalValuationFilterForm with account ID
    WHEN to_dto is called
    THEN it should accurately map to NonPhysicalValuationFilterDTO without dates.
    """

    with server.test_request_context():
        opts = [
            NonPhysicalAccountOptionDTO(
                id=10,
                name="Digital Asset",
                account_type_id=1,
                account_type_name="Asset",
                is_father_account=False,
            )
        ]
        form = NonPhysicalValuationFilterForm(account_options=opts)
        form.account_id.data = "10"

        dto = form.to_dto()
        form.account_id.data = "invalid_id"
        dto_invalid = form.to_dto()

        assert dto.account_id == 10
        assert dto.start_date is None
        assert dto.end_date is None
        assert dto_invalid.account_id is None


def test_non_physical_valuation_filter_form_to_dto_multi_accounts(
    webapp_client: FlaskClient,
):
    """
    GIVEN a NonPhysicalValuationFilterForm with multiple account_ids
    WHEN to_dto is called
    THEN it should accurately map the tuple of account_ids into NonPhysicalValuationFilterDTO.
    """

    with server.test_request_context():
        opts = [
            NonPhysicalAccountOptionDTO(
                id=1,
                name="Crypto A",
                account_type_id=1,
                account_type_name="Asset",
                is_father_account=False,
            ),
            NonPhysicalAccountOptionDTO(
                id=2,
                name="Crypto B",
                account_type_id=1,
                account_type_name="Asset",
                is_father_account=False,
            ),
        ]
        form = NonPhysicalValuationFilterForm(account_options=opts)
        form.account_ids.data = ["1", "2", "invalid_ignored"]

        dto = form.to_dto()

        assert dto.account_ids == (1, 2)
        assert dto.start_date is None
        assert dto.end_date is None


def test_non_physical_accounts_page_filter_by_multiple_account_ids_query_params(
    client_logged_in: FlaskClient, repo_with_data: PostgresRepository
):
    """
    GIVEN a logged-in client and multiple non-physical accounts in the database
    WHEN requesting the valuation page with multiple account_ids query parameters
    THEN the response status should be 200 and only selected accounts included.
    """

    chart = repo_with_data.get_chart_of_accounts()
    cash = chart.get_account_by_name("Cash")
    salary = chart.get_account_by_name("Base Salary")
    assert cash and cash.id and salary and salary.id

    services.record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Alpha Crypto",
            is_physical=False,
            is_archived=False,
            father_account_id=cash.id,
        ),
    )
    services.record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Beta Crypto",
            is_physical=False,
            is_archived=False,
            father_account_id=cash.id,
        ),
    )
    updated_chart = repo_with_data.get_chart_of_accounts()
    alpha = updated_chart.get_account_by_name("Alpha Crypto")
    beta = updated_chart.get_account_by_name("Beta Crypto")
    assert alpha and beta and alpha.id and beta.id

    services.record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=dt.date(2024, 3, 15),
            amount=Decimal("120.00"),
            debit_account_id=alpha.id,
            credit_account_id=salary.id,
        ),
    )
    services.record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=dt.date(2024, 3, 20),
            amount=Decimal("380.00"),
            debit_account_id=beta.id,
            credit_account_id=salary.id,
        ),
    )

    response = client_logged_in.get(
        f"/accounting/non_physical_accounts?account_ids={alpha.id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Alpha Crypto" in response.data
    assert b"120.00" in response.data
