from typing import Optional
from decimal import Decimal

from src import repository, model
from src.utils.helpers import (
    filter_entries_by_date,
    to_account_options,
    resolve_active_accounts,
    aggregate_monthly_account_changes,
    build_monthly_valuation_entries,
    build_empty_non_physical_valuation_view,
)
from src.dto import (
    CreateTransactionDTO,
    CreateAccountDTO,
    PostableAccountOptionDTO,
    ParentAccountOptionDTO,
    AccountTypeOptionDTO,
    TransactionViewDTO,
    TransactionFilterDTO,
    DeleteTransactionDTO,
    NonPhysicalAccountOptionDTO,
    NonPhysicalValuationFilterDTO,
    NonPhysicalValuationViewDTO,
)


def record_new_transaction(
    repo: repository.AbstractRepository,
    transaction_dto: CreateTransactionDTO,
) -> int:
    chart = repo.get_chart_of_accounts()

    try:
        debit_account = chart.get_account_by_id(transaction_dto.debit_account_id)
    except ValueError:
        raise ValueError(
            f"Debit account with ID {transaction_dto.debit_account_id} not found."
        )

    try:
        credit_account = chart.get_account_by_id(transaction_dto.credit_account_id)
    except ValueError:
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

    return repo.post_new_transaction(transaction)


def record_new_account(
    repo: repository.AbstractRepository,
    account_dto: CreateAccountDTO,
) -> None:
    chart = repo.get_chart_of_accounts()
    account_type = model.AccountType.from_id(account_dto.account_type_id)

    new_account = chart.create_account(
        name=account_dto.name,
        account_type=account_type,
        father_account_id=account_dto.father_account_id,
        is_physical=account_dto.is_physical,
        is_archived=account_dto.is_archived,
    )

    repo.post_new_account(new_account)


def get_postable_account_options(
    repo: repository.AbstractRepository,
) -> list[PostableAccountOptionDTO]:
    chart = repo.get_chart_of_accounts()
    return [
        PostableAccountOptionDTO(
            id=acc.id,  # type: ignore
            name=acc.name,
            account_type_id=acc.account_type.id,
            account_type_name=acc.account_type.display_name,
        )
        for acc in chart.postable_accounts
    ]


def get_parent_account_options(
    repo: repository.AbstractRepository,
) -> list[ParentAccountOptionDTO]:
    chart = repo.get_chart_of_accounts()
    return [
        ParentAccountOptionDTO(
            id=acc.id,  # type: ignore
            name=acc.name,
            account_type_id=acc.account_type.id,
        )
        for acc in chart.parent_accounts
    ]


def get_account_type_options() -> list[AccountTypeOptionDTO]:
    return [
        AccountTypeOptionDTO(
            id=account_type.id,
            display_name=account_type.display_name,
        )
        for account_type in model.AccountType
    ]


def get_all_transactions(
    repo: repository.AbstractRepository,
    filter_dto: Optional[TransactionFilterDTO] = None,
) -> list[TransactionViewDTO]:
    start_date = filter_dto.start_date if filter_dto else None
    end_date = filter_dto.end_date if filter_dto else None
    transactions = repo.get_transactions(start_date=start_date, end_date=end_date)

    result: list[TransactionViewDTO] = []
    for t in transactions:
        debit_line = next(
            line for line in t._lines if line.entry_type == model.EntryType.DEBIT
        )
        credit_line = next(
            line for line in t._lines if line.entry_type == model.EntryType.CREDIT
        )
        result.append(
            TransactionViewDTO(
                id=t.id,  # type: ignore
                date=t.date,
                description=t.description,
                amount=t.amount,
                debit_account_name=debit_line.account.name,
                credit_account_name=credit_line.account.name,
            )
        )

    return result


def delete_transaction(
    repo: repository.AbstractRepository,
    transaction_dto: DeleteTransactionDTO,
) -> None:

    if transaction_dto.transaction_id <= 0:
        raise ValueError(f"Invalid transaction ID: {transaction_dto.transaction_id}")

    repo.delete_transaction(transaction_id=transaction_dto.transaction_id)


def get_non_physical_account_options(
    repo: repository.AbstractRepository,
) -> list[NonPhysicalAccountOptionDTO]:
    chart = repo.get_chart_of_accounts()
    target_accounts = [
        acc for acc in chart.non_physical_accounts if not acc.is_father_account
    ]

    return list(to_account_options(target_accounts))


def get_non_physical_accounts_valuation(
    repo: repository.AbstractRepository,
    filter_dto: Optional[NonPhysicalValuationFilterDTO] = None,
) -> NonPhysicalValuationViewDTO:
    chart = repo.get_chart_of_accounts()
    all_transactions = repo.get_transactions()

    target_accounts = [
        acc for acc in chart.non_physical_accounts if not acc.is_father_account
    ]
    account_options = to_account_options(target_accounts)

    active_accounts, selected_account_ids = resolve_active_accounts(
        target_accounts, filter_dto
    )
    single_selected_id = (
        selected_account_ids[0] if len(selected_account_ids) == 1 else None
    )
    active_account_ids = {acc.id for acc in active_accounts}

    monthly_changes, has_activity = aggregate_monthly_account_changes(
        all_transactions, active_account_ids  # type: ignore
    )

    if not active_accounts or not has_activity:
        return build_empty_non_physical_valuation_view(
            account_options, single_selected_id, selected_account_ids
        )

    generated_entries = build_monthly_valuation_entries(
        active_accounts, monthly_changes
    )
    filtered_entries = filter_entries_by_date(generated_entries, filter_dto)

    total_current_value = (
        generated_entries[-1].total_balance if generated_entries else Decimal("0.00")
    )
    latest_monthly_change = (
        generated_entries[-1].total_net_change if generated_entries else Decimal("0.00")
    )

    return NonPhysicalValuationViewDTO(
        accounts=account_options,
        selected_account_id=single_selected_id,
        monthly_entries=tuple(reversed(filtered_entries)),
        total_current_value=total_current_value,
        latest_monthly_change=latest_monthly_change,
        selected_account_ids=selected_account_ids,
    )
