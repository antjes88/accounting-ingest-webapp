import os
from flask import url_for
import pytest
import datetime as dt
from decimal import Decimal

from src.entrypoints.flaskapp.app import server


def test_new_transaction_page_is_reached(client_logged_in):
    response = client_logged_in.get(
        "/accounting/new_transaction",
        follow_redirects=True,
    )

    print(f"Response status code: {response.data}")
    assert 200 == response.status_code
    assert (
        b"<!--new_transaction_form this comment is to check that it is reached on test-->"
        in response.data
    )


def test_new_transaction_post(client_logged_in, repo_with_data):
    transaction_date = dt.date(2024, 1, 1)
    description = "Test Post new transaction"
    amount = Decimal("999.87")

    response = client_logged_in.post(
        "/accounting/new_transaction",
        data={
            "type_debit": "Asset",
            "account_debit": "Petty Cash",
            "type_credit": "Revenue",
            "account_credit": "Base Salary",
            "amount": amount,
            "description": description,
            "date": transaction_date.strftime("%Y-%m-%d"),
        },
        follow_redirects=True,
    )
    transaction_id = repo_with_data.get_max_transaction_id()

    assert response.status_code == 200
    assert b"Transaction recorded successfully!" in response.data
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
