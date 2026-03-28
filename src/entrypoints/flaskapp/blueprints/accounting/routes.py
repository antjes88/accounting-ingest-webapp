from flask import render_template, request, flash
import os

from src.utils.postgresql_client import PostgresGCPClient
from src.repository import PostgresRepository
from src import services

from . import accounting_pages
from .forms import NewTransactionForm


@accounting_pages.route("/new_transaction", methods=["GET", "POST"])
def new_transaction():
    try:
        client = PostgresGCPClient(
            host=os.getenv("HOST"),
            database_name=os.getenv("DATABASE_NAME"),
            user_name=os.getenv("USER_NAME"),
            user_password=os.getenv("USER_PASSWORD"),
        )
        repo = PostgresRepository(client)
        accounts = repo.get_accounts()

        form = NewTransactionForm(accounts)

        if (form.validate_on_submit()) & (request.method == "POST"):
            services.record_new_transaction(
                repo=repo,
                transaction=form.to_transaction(),
                debit_account=form.get_debit_account(accounts),
                credit_account=form.get_credit_account(accounts),
            )
            # TODO: add check for creation of transaction
            flash("Transaction recorded successfully!", "success")
    except Exception as message:
        flash(f"Error recording transaction: {message}", "error")

    return render_template("new_transaction.html", form=form)
