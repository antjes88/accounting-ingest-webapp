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
    debit_account_id = 2  # Petty Cash
    credit_account_id = 4  # Base Salary
    payload = {
        "date": transaction_date.strftime("%Y-%m-%d"),
        "amount": str(amount),
        "debit_account_id": debit_account_id,
        "credit_account_id": credit_account_id,
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
        (transaction_id, credit_account_id, EntryType.CREDIT.id, amount),
        (transaction_id, debit_account_id, EntryType.DEBIT.id, amount),
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
        "debit_account_id": 2,
        "credit_account_id": 4,
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
    WHEN the client posts transaction data referencing an account ID that does not exist
    THEN the response status code should be 400 Bad Request with an error description.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account_id": 9999,  # Nonexistent account
        "credit_account_id": 4,
        "description": "Invalid debit account test",
    }

    response = api_client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json=payload,
    )
    json_data = response.get_json()

    assert response.status_code == 400
    assert "Debit account with ID 9999 not found." in json_data["message"]


@pytest.mark.parametrize(
    "invalid_payload",
    [
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "0.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            id="zero_amount",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "-50.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            id="negative_amount",
        ),
        pytest.param(
            {
                "date": "invalid-date",
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            id="invalid_date_format",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 0,
                "credit_account_id": 4,
            },
            id="invalid_debit_account_id_zero",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": -1,
            },
            id="invalid_credit_account_id_negative",
        ),
        pytest.param(
            {
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            id="missing_date",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            id="missing_amount",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "credit_account_id": 4,
            },
            id="missing_debit_account_id",
        ),
        pytest.param(
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 2,
            },
            id="missing_credit_account_id",
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
        "debit_account_id": 2,
        "credit_account_id": 4,
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
        "debit_account_id": 2,
        "credit_account_id": 4,
        "description": "Direct to_dto conversion test",
    }
    dto = schema.to_dto(data)

    assert isinstance(dto, CreateTransactionDTO)
    assert dto.date == dt.date(2024, 5, 20)
    assert dto.amount == Decimal("150.75")
    assert dto.debit_account_id == 2
    assert dto.credit_account_id == 4
    assert dto.description == "Direct to_dto conversion test"
