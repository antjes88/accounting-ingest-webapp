import dataclasses
from src import repository, model


def record_new_transaction(
    repo: repository.AbstractRepository,
    transaction: model.Transaction,
    debit_account: model.Account,
    credit_account: model.Account,
):
    max_id = repo.get_max_transaction_id()
    transaction = dataclasses.replace(transaction, id=max_id + 1)
    repo.record_new_transaction(transaction, debit_account, credit_account)
