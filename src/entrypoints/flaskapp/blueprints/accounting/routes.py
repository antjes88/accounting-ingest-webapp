from flask import render_template, flash, redirect, url_for, request
import os

from src.utils.postgresql_client import PostgresGCPClient
from src.utils.logs import default_module_logger
from src.repository import PostgresRepository
from src import services

from . import accounting_pages
from .forms import NewTransactionForm, NewAccountForm, TransactionFilterForm

logger = default_module_logger(__file__)


def _get_repository() -> PostgresRepository:
    return PostgresRepository(
        PostgresGCPClient(
            host=os.getenv("HOST") or "",
            database_name=os.getenv("DATABASE_NAME") or "",
            user_name=os.getenv("USER_NAME") or "",
            user_password=os.getenv("USER_PASSWORD") or "",
            port=5432,
        )
    )


@accounting_pages.route("/new_transaction", methods=["GET", "POST"])
def new_transaction():
    repo = _get_repository()
    postable_accounts = services.get_postable_account_options(repo)
    type_options = services.get_account_type_options()

    form = NewTransactionForm(postable_accounts, type_options)

    if form.validate_on_submit():

        try:
            services.record_new_transaction(
                repo=repo,
                transaction_dto=form.to_dto(),
            )

            flash("Transaction recorded successfully!", "success")
            form.account_debit.data = "-- Select an Account --"
            form.amount.data = 0.0

        except ValueError as err:
            logger.warning(f"Validation error recording transaction: {err}")
            flash(f"Error recording transaction: {err}", "warning")

        except Exception:
            logger.exception("Unexpected error recording transaction")
            flash(
                "An unexpected error occurred while recording the transaction.", "error"
            )

    return render_template("new_transaction.html", form=form)


@accounting_pages.route("/new_account", methods=["GET", "POST"])
def new_account():
    repo = _get_repository()
    parent_accounts = services.get_parent_account_options(repo)
    type_options = services.get_account_type_options()

    form = NewAccountForm(parent_accounts, type_options)

    if form.validate_on_submit():

        try:
            services.record_new_account(
                repo=repo,
                account_dto=form.to_dto(),
            )

            flash("Account created successfully!", "success")
            form.name.data = ""

        except ValueError as err:
            logger.warning(f"Validation error creating account: {err}")
            flash(f"Error creating account: {err}", "warning")

        except Exception:
            logger.exception("Unexpected error creating account")
            flash("An unexpected error occurred while creating the account.", "error")

    return render_template("new_account.html", form=form)


@accounting_pages.route("/transactions", methods=["GET"])
def list_transactions():
    repo = _get_repository()

    form = TransactionFilterForm(formdata=request.args, meta={"csrf": False})
    filter_dto = form.to_dto()
    if request.args:
        if form.validate():
            filter_dto = form.to_dto()

    try:
        transactions = services.get_all_transactions(repo, filter_dto=filter_dto)

    except Exception:
        logger.exception("Unexpected error listing transactions")
        flash("An unexpected error occurred while loading transactions.", "error")
        transactions = []

    return render_template("transactions.html", transactions=transactions, form=form)
