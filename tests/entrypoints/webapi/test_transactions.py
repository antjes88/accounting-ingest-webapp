from decimal import Decimal
from typing import Any
from unittest.mock import patch
import datetime as dt
import pytest
from flask.testing import FlaskClient

from src.dto import CreateTransactionDTO
from src.entrypoints.webapi.blueprints.accounting import CreateTransactionSchema
from src.repository import PostgresRepository
from src.model import EntryType
from tests.conftest import repo_with_data


def test_create_transaction_success(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client and a repository with existing accounts
    WHEN the client sends a valid POST request to '/api/v1/transactions'
    THEN the response status code should be 201 Created, returning a success message,
    and the transaction should be persisted in the database.
    """
    transaction_date = dt.date(2024, 6, 15)
    amount = Decimal("250.50")
    description = "API Test transaction"
    debit_account = "Petty Cash"
    credit_account = "Base Salary"
    payload = {
        "date": transaction_date.strftime("%Y-%m-%d"),
        "amount": str(amount),
        "debit_account": debit_account,
        "credit_account": credit_account,
        "description": description,
    }

    response = api_client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json=payload,
    )
    json_data = response.get_json()
    transaction_id = repo_with_data.get_max_transaction_id()

    assert response.status_code == 201
    assert json_data["message"] == "Transaction recorded successfully"
    assert json_data["transaction_id"] == transaction_id
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_date, transaction_description "
        f"FROM {repo_with_data.transactions_table} WHERE transaction_id = {transaction_id}"
    ) == [(transaction_id, transaction_date, description)]
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, account_id, entry_type_id, amount "
        f"FROM {repo_with_data.ledger_entries_table} "
        f"WHERE transaction_id = {transaction_id} ORDER BY entry_type_id"
    ) == [
        (transaction_id, 4, EntryType.CREDIT.id, amount),
        (transaction_id, 2, EntryType.DEBIT.id, amount),
    ]


def test_create_transaction_unauthorized(api_client: FlaskClient) -> None:
    """
    GIVEN an unauthenticated request without a JWT bearer token
    WHEN the client sends a POST request to '/api/v1/transactions'
    THEN the response status code should be 401 Unauthorized.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account": "Petty Cash",
        "credit_account": "Base Salary",
    }

    response = api_client.post(
        "/api/v1/transactions",
        json=payload,
    )

    assert response.status_code == 401


def test_create_transaction_nonexistent_account(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the client posts transaction data referencing an account name that does not exist
    THEN the response status code should be 400 Bad Request with an error description.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account": "Nonexistent Account",
        "credit_account": "Base Salary",
        "description": "Invalid debit account test",
    }

    response = api_client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json=payload,
    )
    json_data = response.get_json()

    assert response.status_code == 400
    assert "Debit account 'Nonexistent Account' not found." in json_data["message"]


@pytest.mark.parametrize(
    "invalid_payload",
    [
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "0.00",
                "debit_account": "Petty Cash",
                "credit_account": "Base Salary",
            },
            id="zero_amount",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "-50.00",
                "debit_account": "Petty Cash",
                "credit_account": "Base Salary",
            },
            id="negative_amount",
        ),
        pytest.param(
            {
                "date": "invalid-date",
                "amount": "100.00",
                "debit_account": "Petty Cash",
                "credit_account": "Base Salary",
            },
            id="invalid_date_format",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account": "",
                "credit_account": "Base Salary",
            },
            id="empty_debit_account",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account": "Petty Cash",
                "credit_account": "",
            },
            id="empty_credit_account",
        ),
        pytest.param(
            {
                "amount": "100.00",
                "debit_account": "Petty Cash",
                "credit_account": "Base Salary",
            },
            id="missing_date",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "debit_account": "Petty Cash",
                "credit_account": "Base Salary",
            },
            id="missing_amount",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "credit_account": "Base Salary",
            },
            id="missing_debit_account",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account": "Petty Cash",
            },
            id="missing_credit_account",
        ),
    ],
)
def test_create_transaction_validation_errors(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    invalid_payload: dict[str, Any],
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the client sends payloads with schema violations (invalid ranges, formats, or missing fields)
    THEN the response status code should be 422 Unprocessable Entity.
    """
    response = api_client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json=invalid_payload,
    )

    assert response.status_code == 422


def test_create_transaction_handles_unexpected_exception(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the services layer throws an unexpected exception
    THEN the response status code should be 500 Internal Server Error.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account": "Petty Cash",
        "credit_account": "Base Salary",
    }

    with patch(
        "src.entrypoints.webapi.blueprints.accounting.services.record_new_transaction",
        side_effect=Exception("Unexpected database outage"),
    ):
        response = api_client.post(
            "/api/v1/transactions",
            headers=auth_headers,
            json=payload,
        )
    json_data = response.get_json()

    assert response.status_code == 500
    assert (
        json_data["message"]
        == "An unexpected error occurred while recording the transaction."
    )


def test_create_transaction_schema_to_dto() -> None:
    """
    GIVEN validated schema data dictionary
    WHEN to_dto method is called on CreateTransactionSchema
    THEN it should correctly return a frozen CreateTransactionDTO with typed values.
    """
    schema = CreateTransactionSchema()
    data = {
        "date": dt.date(2024, 5, 20),
        "amount": Decimal("150.75"),
        "debit_account": "Petty Cash",
        "credit_account": "Base Salary",
        "description": "Direct to_dto conversion test",
    }
    dto = schema.to_dto(data)

    assert isinstance(dto, CreateTransactionDTO)
    assert dto.date == dt.date(2024, 5, 20)
    assert dto.amount == Decimal("150.75")
    assert dto.debit_account == "Petty Cash"
    assert dto.credit_account == "Base Salary"
    assert dto.description == "Direct to_dto conversion test"


def test_batch_create_transactions_success(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client and a repository with existing accounts
    WHEN the client sends a valid POST request to '/api/v1/transactions/batch' with multiple transactions
    THEN the response status code should be 201 Created, returning the list of created transaction IDs,
    and all transactions should be persisted in the database.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
            "description": "Batch API Tx 1",
        },
        {
            "date": "2024-06-17",
            "amount": "200.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
            "description": "Batch API Tx 2",
        },
    ]

    response = api_client.post(
        "/api/v1/transactions/batch",
        headers=auth_headers,
        json=payload,
    )
    json_data = response.get_json()
    id1, id2 = json_data["transaction_ids"]
    res = repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_description FROM {repo_with_data.transactions_table} "
        f"WHERE transaction_id IN ({id1}, {id2}) ORDER BY transaction_id ASC"
    )

    assert response.status_code == 201
    assert json_data["message"] == "Transactions recorded successfully"
    assert len(json_data["transaction_ids"]) == 2
    assert id2 > id1
    assert res == [(id1, "Batch API Tx 1"), (id2, "Batch API Tx 2")]


def test_batch_create_transactions_unauthorized(api_client: FlaskClient) -> None:
    """
    GIVEN an unauthenticated request without a JWT bearer token
    WHEN the client sends a POST request to '/api/v1/transactions/batch'
    THEN the response status code should be 401 Unauthorized.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
        }
    ]
    response = api_client.post(
        "/api/v1/transactions/batch",
        json=payload,
    )

    assert response.status_code == 401


def test_batch_create_transactions_empty_list(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the client sends a POST request to '/api/v1/transactions/batch' with an empty list
    THEN the response status code should be 400 Bad Request with an informative error message.
    """
    response = api_client.post(
        "/api/v1/transactions/batch",
        headers=auth_headers,
        json=[],
    )
    json_data = response.get_json()

    assert response.status_code == 400
    assert json_data["message"] == "At least one transaction must be provided."


def test_batch_create_transactions_atomicity_on_nonexistent_account(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client and a payload where one transaction is valid and another has an invalid account
    WHEN the client sends a POST request to '/api/v1/transactions/batch'
    THEN the response status code should be 400 Bad Request and no transactions should be saved in the database.
    """
    initial_tx_count = len(repo_with_data.get_transactions())
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
            "description": "Batch Valid Tx",
        },
        {
            "date": "2024-06-17",
            "amount": "200.00",
            "debit_account": "Petty Cash",
            "credit_account": "Nonexistent Account",
            "description": "Batch Invalid Account Tx",
        },
    ]

    response = api_client.post(
        "/api/v1/transactions/batch",
        headers=auth_headers,
        json=payload,
    )
    json_data = response.get_json()
    final_tx_count = len(repo_with_data.get_transactions())

    assert response.status_code == 400
    assert "Credit account 'Nonexistent Account' not found." in json_data["message"]
    assert final_tx_count == initial_tx_count


def test_batch_create_transactions_validation_errors(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the client sends a batch payload where an item violates the schema
    THEN the response status code should be 422 Unprocessable Entity.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "-50.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
            "description": "Invalid Amount Tx",
        }
    ]
    response = api_client.post(
        "/api/v1/transactions/batch",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 422


def test_batch_create_transactions_handles_unexpected_exception(
    api_client: FlaskClient,
    auth_headers: dict[str, str],
    repo_with_data: PostgresRepository,
) -> None:
    """
    GIVEN an authenticated API client
    WHEN the services layer throws an unexpected exception during batch processing
    THEN the response status code should be 500 Internal Server Error.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account": "Petty Cash",
            "credit_account": "Base Salary",
            "description": "Valid Tx",
        }
    ]

    with patch(
        "src.entrypoints.webapi.blueprints.accounting.services.record_new_transactions",
        side_effect=Exception("Database batch outage"),
    ):
        response = api_client.post(
            "/api/v1/transactions/batch",
            headers=auth_headers,
            json=payload,
        )
    json_data = response.get_json()

    assert response.status_code == 500
    assert (
        json_data["message"]
        == "An unexpected error occurred while recording the transactions."
    )
