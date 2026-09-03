import os
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
import click

from src.dto import CreateTransactionDTO
from src.repository import PostgresRepository, AbstractRepository
from src.utils.postgresql_client import PostgresGCPClient
from src.utils.logs import default_module_logger
from src import services

logger = default_module_logger(__file__)


def _get_repository() -> AbstractRepository:
    return PostgresRepository(
        PostgresGCPClient(
            host=os.getenv("HOST") or "",
            database_name=os.getenv("DATABASE_NAME") or "",
            user_name=os.getenv("USER_NAME") or "",
            user_password=os.getenv("USER_PASSWORD") or "",
            port=5432,
        )
    )


def load_transaction_dto_from_json(file_path: str) -> CreateTransactionDTO:
    with open(file_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Invalid JSON format: root element must be an object.")

    required_fields = ["date", "amount", "debit_account_id", "credit_account_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValueError(f"Missing required field: '{field}'.")

    try:
        transaction_date = date.fromisoformat(str(data["date"]))
    except (ValueError, TypeError) as err:
        raise ValueError(
            f"Invalid date format '{data.get('date')}': expected YYYY-MM-DD."
        ) from err

    try:
        amount = Decimal(str(data["amount"]))
    except (InvalidOperation, TypeError) as err:
        raise ValueError(
            f"Invalid amount '{data.get('amount')}': must be a valid numeric decimal."
        ) from err

    if amount <= Decimal("0"):
        raise ValueError(f"Invalid amount '{amount}': amount must be greater than 0.")

    try:
        debit_account_id = int(data["debit_account_id"])
        credit_account_id = int(data["credit_account_id"])
    except (ValueError, TypeError) as err:
        raise ValueError("Account IDs must be integers.") from err

    if debit_account_id <= 0:
        raise ValueError(f"Invalid debit_account_id: {debit_account_id}")

    if credit_account_id <= 0:
        raise ValueError(f"Invalid credit_account_id: {credit_account_id}")

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("Description must be a string.")

    return CreateTransactionDTO(
        date=transaction_date,
        amount=amount,
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        description=description,
    )


@click.command(name="create-transaction")
@click.option(
    "file_path",
    "-fp",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="Path of the file in the bucket",
)
def create_transaction(file_path: str) -> None:
    """Create and record a new transaction from a JSON file."""
    repo = _get_repository()

    try:
        dto = load_transaction_dto_from_json(file_path)
        transaction_id = services.record_new_transaction(
            repo=repo,
            transaction_dto=dto,
        )
        msg = f"Transaction recorded successfully! Transaction ID: {transaction_id}"
        logger.info(msg)
        click.echo(msg)

    except json.JSONDecodeError as err:
        error_msg = f"Error parsing JSON file: {err}"
        logger.warning(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        raise click.Abort()

    except ValueError as err:
        error_msg = f"Validation error recording transaction: {err}"
        logger.warning(error_msg)
        click.echo(f"Error: {err}", err=True)
        raise click.Abort()

    except Exception:
        logger.exception("Unexpected error recording transaction via CLI")
        click.echo(
            "An unexpected error occurred while recording the transaction.", err=True
        )
        raise click.Abort()
