from decimal import Decimal
from typing import Any
import os
from flask import views
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate
from flask_jwt_extended import jwt_required

from src.dto import CreateTransactionDTO
from src.repository import PostgresRepository, AbstractRepository
from src.utils.postgresql_client import PostgresGCPClient
from src.utils.logs import default_module_logger
from src import services

logger = default_module_logger(__file__)

accounting = Blueprint(
    "accounting",
    __name__,
    url_prefix="/api/v1/transactions",
    description="Transactions management and operations",
)


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


class CreateTransactionSchema(Schema):
    date = fields.Date(
        required=True,
        metadata={"description": "Date of the transaction (YYYY-MM-DD)"},
    )
    amount = fields.Decimal(
        as_string=True,
        required=True,
        validate=validate.Range(min=Decimal("0.01")),
        metadata={"description": "Amount of the transaction (must be greater than 0)"},
    )
    debit_account_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        metadata={"description": "Unique identifier of debit account"},
    )
    credit_account_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        metadata={"description": "Unique identifier of credit account"},
    )
    description = fields.String(
        load_default=None,
        allow_none=True,
        metadata={"description": "Optional description of the transaction"},
    )

    def to_dto(self, data: dict[str, Any]) -> CreateTransactionDTO:
        return CreateTransactionDTO(
            date=data["date"],
            amount=data["amount"],
            debit_account_id=data["debit_account_id"],
            credit_account_id=data["credit_account_id"],
            description=data.get("description"),
        )


CreateTransaction = CreateTransactionSchema


class TransactionCreatedResponseSchema(Schema):
    transaction_id = fields.Integer(
        required=True,
        metadata={"description": "Unique identifier of the created transaction"},
    )
    message = fields.String(
        required=True,
        dump_default="Transaction recorded successfully",
        metadata={"description": "Operation confirmation message"},
    )


@accounting.route("")
class TransactionCollection(views.MethodView):

    @jwt_required()
    @accounting.arguments(CreateTransactionSchema)
    @accounting.response(201, TransactionCreatedResponseSchema)
    def post(self, transaction_data: dict[str, Any]) -> dict[str, Any]:
        """Create and record a new transaction"""
        schema = CreateTransactionSchema()
        dto = schema.to_dto(transaction_data)
        repo = _get_repository()

        try:
            transaction_id = services.record_new_transaction(
                repo=repo,
                transaction_dto=dto,
            )
            return {
                "transaction_id": transaction_id,
                "message": "Transaction recorded successfully",
            }

        except ValueError as err:
            logger.warning(f"Validation error recording transaction: {err}")
            abort(400, message=str(err))

        except Exception:
            logger.exception("Unexpected error recording transaction")
            abort(
                500,
                message="An unexpected error occurred while recording the transaction.",
            )
