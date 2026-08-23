from src import repository, model
from src.dto import (
    CreateTransactionDTO,
    CreateAccountDTO,
    PostableAccountOptionDTO,
    ParentAccountOptionDTO,
    AccountTypeOptionDTO,
)


def record_new_transaction(
    repo: repository.AbstractRepository,
    transaction_dto: CreateTransactionDTO,
) -> None:
    accounts = repo.get_accounts()
    accounts_by_id = {account.id: account for account in accounts}

    debit_account = accounts_by_id.get(transaction_dto.debit_account_id)
    credit_account = accounts_by_id.get(transaction_dto.credit_account_id)

    if not debit_account:
        raise ValueError(
            f"Debit account with ID {transaction_dto.debit_account_id} not found."
        )
    if not credit_account:
        raise ValueError(
            f"Credit account with ID {transaction_dto.credit_account_id} not found."
        )

    transaction = model.Transaction(
        id=None,
        date=transaction_dto.date,
        description=transaction_dto.description,
        lines=[
            model.TransactionLine(
                account=debit_account,
                amount=transaction_dto.amount,
                entry_type=model.EntryType.DEBIT,
            ),
            model.TransactionLine(
                account=credit_account,
                amount=transaction_dto.amount,
                entry_type=model.EntryType.CREDIT,
            ),
        ],
    )

    repo.post_new_transaction(transaction)


def record_new_account(
    repo: repository.AbstractRepository,
    account_dto: CreateAccountDTO,
) -> None:
    account_type = model.AccountType.from_id(account_dto.account_type_id)

    father_account = None
    if account_dto.father_account_id is not None:
        accounts = repo.get_accounts()
        accounts_by_id = {acc.id: acc for acc in accounts}
        father_account = accounts_by_id.get(account_dto.father_account_id)
        if not father_account:
            raise ValueError(
                f"Father account with ID {account_dto.father_account_id} not found."
            )

    account = model.Account(
        id=None,
        account_type=account_type,
        name=account_dto.name,
        father_account=father_account,
        is_physical=account_dto.is_physical,
        is_archived=account_dto.is_archived,
    )

    repo.post_new_account(account)


def get_postable_account_options(
    repo: repository.AbstractRepository,
) -> list[PostableAccountOptionDTO]:
    accounts = repo.get_accounts()
    return [
        PostableAccountOptionDTO(
            id=acc.id,  # type: ignore
            name=acc.name,
            account_type_id=acc.account_type.id,
            account_type_name=acc.account_type.display_name,
        )
        for acc in accounts
        if not acc.is_father_account and not acc.is_archived
    ]


def get_parent_account_options(
    repo: repository.AbstractRepository,
) -> list[ParentAccountOptionDTO]:
    accounts = repo.get_accounts()
    return [
        ParentAccountOptionDTO(
            id=acc.id,  # type: ignore
            name=acc.name,
            account_type_id=acc.account_type.id,
        )
        for acc in accounts
        if acc.is_father_account and not acc.is_archived
    ]


def get_account_type_options() -> list[AccountTypeOptionDTO]:
    return [
        AccountTypeOptionDTO(
            id=account_type.id,
            display_name=account_type.display_name,
        )
        for account_type in model.AccountType
    ]
