import dataclasses
from src import repository, model


def record_new_transaction(
    repo: repository.AbstractRepository,
    transaction: model.Transaction,
) -> None:
    repo.post_new_transaction(transaction)
