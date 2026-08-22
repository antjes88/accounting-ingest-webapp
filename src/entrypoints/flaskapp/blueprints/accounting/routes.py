from flask import render_template, flash, redirect, url_for
import os

from src.utils.postgresql_client import PostgresGCPClient
from src.utils.logs import default_module_logger
from src.repository import PostgresRepository
from src import services

from . import accounting_pages
from .forms import NewTransactionForm, NewAccountForm

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
    account_options = services.get_account_options(repo)
    type_options = services.get_account_type_options()

    form = NewTransactionForm(account_options, type_options)

    if form.validate_on_submit():

        try:
            services.record_new_transaction(
                repo=repo,
                transaction_dto=form.to_dto(),
            )

            flash("Transaction recorded successfully!", "success")
            return redirect(url_for("accounting_pages.new_transaction"))

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
    account_options = services.get_account_options(repo)
    type_options = services.get_account_type_options()

    form = NewAccountForm(account_options, type_options)

    if form.validate_on_submit():

        try:
            services.record_new_account(
                repo=repo,
                account_dto=form.to_dto(),
            )

            flash("Account created successfully!", "success")
            return redirect(url_for("accounting_pages.new_account"))

        except ValueError as err:
            logger.warning(f"Validation error creating account: {err}")
            flash(f"Error creating account: {err}", "warning")

        except Exception:
            logger.exception("Unexpected error creating account")
            flash("An unexpected error occurred while creating the account.", "error")

    return render_template("new_account.html", form=form)
