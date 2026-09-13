import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch
import pytest
from click.testing import CliRunner

from src.entrypoints.cli.__main__ import cli
from src.entrypoints.cli.create_transaction import (
    load_transaction_dto_from_json,
    load_batch_transaction_dto_from_json,
    validate_transaction_dict,
)
from src.dto import CreateTransactionDTO, BatchCreateTransactionDTO
from src.repository import PostgresRepository
from src.model import EntryType


def test_create_transaction_success(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN a valid JSON transaction file and a repository with existing accounts
    WHEN the create-transaction CLI command is executed with the -fp option
    THEN the exit code should be 0, a success message with the transaction ID displayed,
    and the transaction should be persisted in the database.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "250.50",
        "debit_account_id": 2,
        "credit_account_id": 4,
        "description": "CLI Test transaction",
    }
    json_file = tmp_path / "transaction.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ):
        result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])
    transaction_id = repo_with_data.get_max_transaction_id()

    assert result.exit_code == 0
    assert "Transaction recorded successfully! Transaction ID:" in result.output
    assert str(transaction_id) in result.output
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_date, transaction_description "
        f"FROM {repo_with_data.transactions_table} WHERE transaction_id = {transaction_id}"
    ) == [(transaction_id, date(2024, 6, 15), "CLI Test transaction")]
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, account_id, entry_type_id, amount "
        f"FROM {repo_with_data.ledger_entries_table} "
        f"WHERE transaction_id = {transaction_id} ORDER BY entry_type_id"
    ) == [
        (transaction_id, 4, EntryType.CREDIT.id, Decimal("250.50")),
        (transaction_id, 2, EntryType.DEBIT.id, Decimal("250.50")),
    ]


def test_create_transaction_missing_option() -> None:
    """
    GIVEN the create-transaction CLI command invoked without the required -fp option
    WHEN the CLI command is executed
    THEN the exit code should be non-zero indicating a missing required option.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ["create-transaction"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "-fp" in result.output


def test_create_transaction_file_not_found() -> None:
    """
    GIVEN a non-existent file path passed to -fp
    WHEN the create-transaction CLI command is executed
    THEN the exit code should be non-zero indicating a parameter error.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create-transaction", "-fp", "/nonexistent/path/trans.json"]
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output and "Error" in result.output


def test_create_transaction_invalid_json(tmp_path: Path) -> None:
    """
    GIVEN a file containing malformed JSON
    WHEN the create-transaction CLI command is executed with -fp
    THEN the exit code should be non-zero and an error message displayed.
    """
    json_file = tmp_path / "malformed.json"
    json_file.write_text("{invalid_json: true,", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert "Error parsing JSON file" in result.output


@pytest.mark.parametrize(
    "missing_field",
    ["date", "amount", "debit_account_id", "credit_account_id"],
)
def test_create_transaction_missing_required_fields(
    missing_field: str, tmp_path: Path
) -> None:
    """
    GIVEN a JSON file missing a required field
    WHEN the create-transaction CLI command is executed and load_transaction_dto_from_json is called
    THEN the CLI should fail and load_transaction_dto_from_json should raise a ValueError.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account_id": 2,
        "credit_account_id": 4,
    }
    del payload[missing_field]

    json_file = tmp_path / "missing.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert f"Missing required field: '{missing_field}'" in result.output


@pytest.mark.parametrize(
    "invalid_payload, expected_error",
    [
        (
            {
                "date": "invalid-date",
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            "Invalid date format",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "-50.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            "amount must be greater than 0",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "not-a-number",
                "debit_account_id": 2,
                "credit_account_id": 4,
            },
            "must be a valid numeric decimal",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 0,
                "credit_account_id": 4,
            },
            "Invalid debit_account_id",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": -1,
            },
            "Invalid credit_account_id",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": "abc",
                "credit_account_id": 4,
            },
            "Account IDs must be integers",
        ),
        (
            {
                "date": "2024-06-15",
                "amount": "100.00",
                "debit_account_id": 2,
                "credit_account_id": 4,
                "description": 12345,
            },
            "Description must be a string",
        ),
    ],
)
def test_create_transaction_invalid_field_values(
    invalid_payload: dict[str, Any], expected_error: str, tmp_path: Path
) -> None:
    """
    GIVEN a JSON file containing invalid field values
    WHEN the create-transaction CLI command is executed and load_transaction_dto_from_json is called
    THEN the CLI should fail and load_transaction_dto_from_json should raise a ValueError with expected message.
    """
    json_file = tmp_path / "invalid.json"
    json_file.write_text(json.dumps(invalid_payload), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert expected_error in result.output


def test_create_transaction_nonexistent_account(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN a JSON file referencing a non-existent account ID
    WHEN the create-transaction CLI command is executed
    THEN the exit code should be non-zero and domain validation error displayed.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account_id": 9999,
        "credit_account_id": 4,
    }
    json_file = tmp_path / "nonexistent_account.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ):
        result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert "Debit account with ID 9999 not found" in result.output


def test_create_transaction_unexpected_exception(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN an unexpected error during transaction creation
    WHEN the create-transaction CLI command is executed
    THEN the exit code should be non-zero and a generic error message displayed.
    """
    payload = {
        "date": "2024-06-15",
        "amount": "100.00",
        "debit_account_id": 2,
        "credit_account_id": 4,
    }
    json_file = tmp_path / "trans.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ), patch(
        "src.entrypoints.cli.create_transaction.services.record_new_transaction",
        side_effect=Exception("Database crash"),
    ):
        result = runner.invoke(cli, ["create-transaction", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert (
        "An unexpected error occurred while recording the transaction." in result.output
    )


def test_load_transaction_dto_from_json_direct(tmp_path: Path) -> None:
    """
    GIVEN a valid JSON transaction file
    WHEN load_transaction_dto_from_json is called directly
    THEN it should return an immutable CreateTransactionDTO instance with correctly typed values.
    """
    payload = {
        "date": "2024-05-20",
        "amount": "150.75",
        "debit_account_id": 2,
        "credit_account_id": 4,
        "description": "Direct DTO loader test",
    }
    json_file = tmp_path / "valid.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    dto = load_transaction_dto_from_json(str(json_file))

    assert isinstance(dto, CreateTransactionDTO)
    assert dto.date == date(2024, 5, 20)
    assert dto.amount == Decimal("150.75")
    assert dto.debit_account_id == 2
    assert dto.credit_account_id == 4
    assert dto.description == "Direct DTO loader test"


def test_load_transaction_dto_from_json_non_dict(tmp_path: Path) -> None:
    """
    GIVEN a JSON file containing a list instead of an object
    WHEN load_transaction_dto_from_json is called
    THEN it should raise a ValueError.
    """
    json_file = tmp_path / "list.json"
    json_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with pytest.raises(ValueError, match="root element must be an object"):
        load_transaction_dto_from_json(str(json_file))


def test_create_transactions_success(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN a valid JSON file containing a list of transactions and a repository with existing accounts
    WHEN the create-transactions CLI command is executed with the -fp option
    THEN the exit code should be 0, a success message with all transaction IDs displayed,
    and all transactions should be persisted in the database.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "CLI Batch Tx 1",
        },
        {
            "date": "2024-06-17",
            "amount": "200.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "CLI Batch Tx 2",
        },
    ]
    json_file = tmp_path / "transactions.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ):
        result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])

    rows = repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_description "
        f"FROM {repo_with_data.transactions_table} "
        f"WHERE transaction_description IN ('CLI Batch Tx 1', 'CLI Batch Tx 2') "
        f"ORDER BY transaction_id ASC;"
    )
    id1, id2 = rows[0][0], rows[1][0]

    assert result.exit_code == 0
    assert "Transactions recorded successfully! Transaction IDs:" in result.output
    assert len(rows) == 2
    assert f"{id1}, {id2}" in result.output


def test_create_transactions_missing_option() -> None:
    """
    GIVEN the create-transactions CLI command invoked without the required -fp option
    WHEN the CLI command is executed
    THEN the exit code should be non-zero indicating a missing required option.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ["create-transactions"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "-fp" in result.output


def test_create_transactions_file_not_found() -> None:
    """
    GIVEN a non-existent file path passed to -fp
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero indicating a parameter error.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli, ["create-transactions", "-fp", "/nonexistent/path/batch.json"]
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output and "Error" in result.output


def test_create_transactions_invalid_json(tmp_path: Path) -> None:
    """
    GIVEN a file containing malformed JSON
    WHEN the create-transactions CLI command is executed with -fp
    THEN the exit code should be non-zero and an error message displayed.
    """
    json_file = tmp_path / "malformed_batch.json"
    json_file.write_text("[{invalid_json: true,", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert "Error parsing JSON file" in result.output


def test_create_transactions_root_not_list(tmp_path: Path) -> None:
    """
    GIVEN a JSON file where the root element is an object instead of a list
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero and an informative error displayed.
    """
    json_file = tmp_path / "not_a_list.json"
    json_file.write_text(json.dumps({"date": "2024-06-15"}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert "root element must be a list" in result.output


def test_create_transactions_empty_list(tmp_path: Path) -> None:
    """
    GIVEN a JSON file containing an empty list
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero and an error displayed.
    """
    json_file = tmp_path / "empty_list.json"
    json_file.write_text(json.dumps([]), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert "At least one transaction must be provided" in result.output


def test_create_transactions_validation_error_in_item(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN a JSON file containing multiple transactions where one has an invalid field value
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero and no transactions should be saved in the database.
    """
    initial_tx_count = len(repo_with_data.get_transactions())
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "Valid Tx in batch",
        },
        {
            "date": "2024-06-17",
            "amount": "-50.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "Invalid amount Tx",
        },
    ]
    json_file = tmp_path / "invalid_item.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ):
        result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])
    final_tx_count = len(repo_with_data.get_transactions())

    assert result.exit_code != 0
    assert "amount must be greater than 0" in result.output
    assert final_tx_count == initial_tx_count


def test_create_transactions_nonexistent_account(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN a JSON file containing multiple transactions where one references a non-existent account
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero and no transactions should be persisted.
    """
    initial_tx_count = len(repo_with_data.get_transactions())
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "Valid Tx",
        },
        {
            "date": "2024-06-17",
            "amount": "100.00",
            "debit_account_id": 2,
            "credit_account_id": 9999,
            "description": "Invalid Account Tx",
        },
    ]
    json_file = tmp_path / "nonexistent_account_batch.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ):
        result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])
    final_tx_count = len(repo_with_data.get_transactions())

    assert result.exit_code != 0
    assert "Credit account with ID 9999 not found" in result.output
    assert final_tx_count == initial_tx_count


def test_create_transactions_unexpected_exception(
    repo_with_data: PostgresRepository, tmp_path: Path
) -> None:
    """
    GIVEN an unexpected error during batch transaction creation
    WHEN the create-transactions CLI command is executed
    THEN the exit code should be non-zero and a generic error message displayed.
    """
    payload = [
        {
            "date": "2024-06-16",
            "amount": "100.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
        }
    ]
    json_file = tmp_path / "batch.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    runner = CliRunner()
    with patch(
        "src.entrypoints.cli.create_transaction._get_repository",
        return_value=repo_with_data,
    ), patch(
        "src.entrypoints.cli.create_transaction.services.record_new_transactions",
        side_effect=Exception("Database batch crash"),
    ):
        result = runner.invoke(cli, ["create-transactions", "-fp", str(json_file)])

    assert result.exit_code != 0
    assert (
        "An unexpected error occurred while recording the transactions."
        in result.output
    )


def test_load_batch_transaction_dto_from_json_direct(tmp_path: Path) -> None:
    """
    GIVEN a valid JSON batch transactions file
    WHEN load_batch_transaction_dto_from_json is called directly
    THEN it should return an immutable BatchCreateTransactionDTO containing typed CreateTransactionDTOs.
    """
    payload = [
        {
            "date": "2024-05-20",
            "amount": "150.75",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "Batch item 1",
        },
        {
            "date": "2024-05-21",
            "amount": "250.00",
            "debit_account_id": 2,
            "credit_account_id": 4,
            "description": "Batch item 2",
        },
    ]
    json_file = tmp_path / "valid_batch.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    batch_dto = load_batch_transaction_dto_from_json(str(json_file))

    assert isinstance(batch_dto, BatchCreateTransactionDTO)
    assert len(batch_dto.transactions) == 2
    assert batch_dto.transactions[0].amount == Decimal("150.75")
    assert batch_dto.transactions[1].amount == Decimal("250.00")


def test_validate_transaction_dict_non_dict() -> None:
    """
    GIVEN a non-dict item passed to validate_transaction_dict
    WHEN validate_transaction_dict is called
    THEN it should raise a ValueError.
    """
    with pytest.raises(ValueError, match="element must be an object"):
        validate_transaction_dict("not a dict")  # type: ignore
