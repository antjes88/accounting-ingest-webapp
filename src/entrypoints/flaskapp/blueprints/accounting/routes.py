from flask import render_template, request, flash
import os

from src.utils.postgresql_client import PostgresGCPClient
from src.utils.logs import default_module_logger
from src.repository import PostgresRepository
from src import services

from . import accounting_pages
from .forms import NewTransactionForm

logger = default_module_logger(__file__)


@accounting_pages.route("/new_transaction", methods=["GET", "POST"])
def new_transaction():
    try:
        repo = PostgresRepository(
            PostgresGCPClient(
                host=os.getenv("HOST"),
                database_name=os.getenv("DATABASE_NAME"),
                user_name=os.getenv("USER_NAME"),
                user_password=os.getenv("USER_PASSWORD"),
                port=5432,
            )
        )
        accounts = repo.get_accounts()

        form = NewTransactionForm(accounts)

        if (form.validate_on_submit()) & (request.method == "POST"):
            services.record_new_transaction(
                repo=repo,
                transaction=form.to_transaction(),
                debit_account=form.get_debit_account(accounts),
                credit_account=form.get_credit_account(accounts),
            )

            flash("Transaction recorded successfully!", "success")
    except Exception as message:
        logger.error(f"Error when dealing with database: '{message}'")
        flash(f"Error recording transaction: {message}", "error")

    return render_template("new_transaction.html", form=form)
