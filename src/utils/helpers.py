from decimal import Decimal
from typing import Optional
from collections import defaultdict
from datetime import date

from src import model
from src.dto import (
    MonthlyAccountValueDTO,
    NonPhysicalAccountOptionDTO,
    NonPhysicalValuationFilterDTO,
    MonthlyValuationEntryDTO,
    NonPhysicalValuationViewDTO,
)


def _generate_month_range(start_ym: str, end_ym: str) -> list[str]:
    start_y, start_m = map(int, start_ym.split("-"))
    end_y, end_m = map(int, end_ym.split("-"))
    months: list[str] = []
    curr_y, curr_m = start_y, start_m
    while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
        months.append(f"{curr_y:04d}-{curr_m:02d}")
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1

    return months


def to_account_options(
    accounts: list[model.Account],
) -> tuple[NonPhysicalAccountOptionDTO, ...]:
    return tuple(
        NonPhysicalAccountOptionDTO(
            id=acc.id,  # type: ignore
            name=acc.name,
            account_type_id=acc.account_type.id,
            account_type_name=acc.account_type.display_name,
            is_father_account=acc.is_father_account,
        )
        for acc in sorted(accounts, key=lambda a: a.name.lower())
    )


def resolve_active_accounts(
    target_accounts: list[model.Account],
    filter_dto: Optional[NonPhysicalValuationFilterDTO],
) -> tuple[list[model.Account], tuple[int, ...]]:
    if not target_accounts:
        if filter_dto and filter_dto.account_ids:
            raise ValueError(
                f"Account ID(s) {list(filter_dto.account_ids)} are not valid non-physical accounts."
            )
        if filter_dto and filter_dto.account_id is not None:
            raise ValueError(
                f"Account with ID {filter_dto.account_id} is not a valid non-physical account."
            )
        return [], ()

    target_account_map = {acc.id: acc for acc in target_accounts}

    if filter_dto and filter_dto.account_ids:
        invalid_ids = [
            aid for aid in filter_dto.account_ids if aid not in target_account_map
        ]
        if invalid_ids:
            raise ValueError(
                f"Account ID(s) {invalid_ids} are not valid non-physical accounts."
            )
        selected_account_ids = tuple(filter_dto.account_ids)
        active_accounts = [target_account_map[aid] for aid in selected_account_ids]

        return active_accounts, selected_account_ids

    if filter_dto and filter_dto.account_id is not None:
        if filter_dto.account_id not in target_account_map:
            raise ValueError(
                f"Account with ID {filter_dto.account_id} is not a valid non-physical account."
            )
        selected_account_ids = (filter_dto.account_id,)
        active_accounts = [target_account_map[filter_dto.account_id]]

        return active_accounts, selected_account_ids

    active_accounts = sorted(target_accounts, key=lambda a: a.name.lower())

    return active_accounts, ()


def aggregate_monthly_account_changes(
    transactions: list[model.Transaction],
    active_account_ids: set[int],
) -> tuple[dict[str, dict[int, Decimal]], bool]:
    sorted_transactions = sorted(transactions, key=lambda t: (t.date, t.id or 0))
    monthly_changes: dict[str, dict[int, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0.00"))
    )
    has_activity = False

    for t in sorted_transactions:
        ym = t.date.strftime("%Y-%m")
        for line in t._lines:
            acc_id = line.account.id
            if acc_id in active_account_ids:
                has_activity = True
                impact = line.account.get_balance_impact(line.entry_type, line.amount)
                monthly_changes[ym][acc_id] += impact  # type: ignore

    return monthly_changes, has_activity


def build_monthly_valuation_entries(
    active_accounts: list[model.Account],
    monthly_changes: dict[str, dict[int, Decimal]],
) -> list[MonthlyValuationEntryDTO]:
    if not monthly_changes:
        return []

    all_yms = sorted(monthly_changes.keys())
    start_ym = all_yms[0]
    end_ym = all_yms[-1]
    continuous_months = _generate_month_range(start_ym, end_ym)

    running_balances: dict[int, Decimal] = {
        acc.id: Decimal("0.00") for acc in active_accounts  # type: ignore
    }
    generated_entries: list[MonthlyValuationEntryDTO] = []

    for ym in continuous_months:
        y, m = map(int, ym.split("-"))
        month_label = date(y, m, 1).strftime("%b %Y")

        month_acc_values: list[MonthlyAccountValueDTO] = []
        month_total_net = Decimal("0.00")
        month_total_balance = Decimal("0.00")
        month_changes = monthly_changes.get(ym, {})

        for acc in active_accounts:
            net_change = month_changes.get(acc.id, Decimal("0.00"))  # type: ignore
            running_balances[acc.id] += net_change  # type: ignore
            bal = running_balances[acc.id]  # type: ignore

            month_acc_values.append(
                MonthlyAccountValueDTO(
                    account_id=acc.id,  # type: ignore
                    account_name=acc.name,
                    balance=bal,
                    net_change=net_change,
                )
            )
            month_total_net += net_change
            month_total_balance += bal

        generated_entries.append(
            MonthlyValuationEntryDTO(
                year_month=ym,
                month_label=month_label,
                total_balance=month_total_balance,
                total_net_change=month_total_net,
                account_values=tuple(month_acc_values),
            )
        )

    return generated_entries


def filter_entries_by_date(
    entries: list[MonthlyValuationEntryDTO],
    filter_dto: Optional[NonPhysicalValuationFilterDTO],
) -> list[MonthlyValuationEntryDTO]:
    filter_start_ym = (
        filter_dto.start_date.strftime("%Y-%m")
        if filter_dto and filter_dto.start_date
        else None
    )
    filter_end_ym = (
        filter_dto.end_date.strftime("%Y-%m")
        if filter_dto and filter_dto.end_date
        else None
    )

    return [
        entry
        for entry in entries
        if (not filter_start_ym or entry.year_month >= filter_start_ym)
        and (not filter_end_ym or entry.year_month <= filter_end_ym)
    ]


def build_empty_non_physical_valuation_view(
    account_options: tuple[NonPhysicalAccountOptionDTO, ...],
    single_selected_id: Optional[int],
    selected_account_ids: tuple[int, ...],
) -> NonPhysicalValuationViewDTO:

    return NonPhysicalValuationViewDTO(
        accounts=account_options,
        selected_account_id=single_selected_id,
        monthly_entries=(),
        total_current_value=Decimal("0.00"),
        latest_monthly_change=Decimal("0.00"),
        selected_account_ids=selected_account_ids,
    )
