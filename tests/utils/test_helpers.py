import re
from datetime import date
from decimal import Decimal
from typing import Optional
import pytest

from src.model import Account, AccountType, EntryType, Transaction, TransactionLine
from src.dto import (
    NonPhysicalValuationFilterDTO,
    MonthlyValuationEntryDTO,
)
from src.utils.helpers import (
    _generate_month_range,
    to_account_options,
    resolve_active_accounts,
    aggregate_monthly_account_changes,
    build_monthly_valuation_entries,
    filter_entries_by_date,
)


@pytest.mark.parametrize(
    "start_ym,end_ym,expected_months",
    [
        (
            "2024-05",
            "2024-05",
            ["2024-05"],
        ),
        (
            "2024-01",
            "2024-04",
            ["2024-01", "2024-02", "2024-03", "2024-04"],
        ),
        (
            "2023-11",
            "2024-02",
            ["2023-11", "2023-12", "2024-01", "2024-02"],
        ),
        (
            "2022-11",
            "2024-01",
            [
                "2022-11",
                "2022-12",
                "2023-01",
                "2023-02",
                "2023-03",
                "2023-04",
                "2023-05",
                "2023-06",
                "2023-07",
                "2023-08",
                "2023-09",
                "2023-10",
                "2023-11",
                "2023-12",
                "2024-01",
            ],
        ),
        (
            "2024-05",
            "2024-01",
            [],
        ),
        (
            "2025-01",
            "2024-12",
            [],
        ),
    ],
)
def test_generate_month_range(
    start_ym: str, end_ym: str, expected_months: list[str]
) -> None:
    """
    GIVEN a start month and an end month in 'YYYY-MM' format
    WHEN _generate_month_range is called
    THEN it should return the expected continuous list of 'YYYY-MM' strings
    """
    result = _generate_month_range(start_ym, end_ym)

    assert result == expected_months


def test_to_account_options_empty() -> None:
    """
    GIVEN an empty list of accounts
    WHEN to_account_options is called
    THEN it should return an empty tuple
    """
    assert to_account_options([]) == ()


def test_to_account_options_sorted_alphabetically() -> None:
    """
    GIVEN a list of accounts in non-alphabetical order
    WHEN to_account_options is called
    THEN it should return a tuple of NonPhysicalAccountOptionDTO sorted by name in case-insensitive order
    """
    acc_zebra = Account(id=1, account_type=AccountType.EQUITY, name="Zebra Account")
    acc_apple = Account(id=2, account_type=AccountType.ASSET, name="apple Account")
    acc_mango = Account(id=3, account_type=AccountType.LIABILITY, name="Mango Account")

    options = to_account_options([acc_zebra, acc_apple, acc_mango])

    assert len(options) == 3
    assert [opt.name for opt in options] == [
        "apple Account",
        "Mango Account",
        "Zebra Account",
    ]
    assert [opt.id for opt in options] == [2, 3, 1]
    assert [opt.account_type_id for opt in options] == [
        AccountType.ASSET.id,
        AccountType.LIABILITY.id,
        AccountType.EQUITY.id,
    ]


def test_resolve_active_accounts_no_target_accounts() -> None:
    """
    GIVEN an empty list of target accounts
    WHEN resolve_active_accounts is called with no filter
    THEN it should return empty lists for active accounts and selected IDs
    """
    active, selected_ids = resolve_active_accounts([], None)

    assert active == []
    assert selected_ids == ()


@pytest.mark.parametrize(
    "filter_dto,expected_error_msg",
    [
        (
            NonPhysicalValuationFilterDTO(account_ids=(99,)),
            "Account ID(s) [99] are not valid non-physical accounts.",
        ),
        (
            NonPhysicalValuationFilterDTO(account_id=99),
            "Account with ID 99 is not a valid non-physical account.",
        ),
    ],
)
def test_resolve_active_accounts_no_targets_raises_on_filter(
    filter_dto: NonPhysicalValuationFilterDTO, expected_error_msg: str
) -> None:
    """
    GIVEN an empty list of target accounts
    WHEN resolve_active_accounts is called with account filter criteria
    THEN it should raise ValueError with an informative message
    """
    with pytest.raises(ValueError, match=re.escape(expected_error_msg)):
        resolve_active_accounts([], filter_dto)


def test_resolve_active_accounts_filter_by_account_ids_valid() -> None:
    """
    GIVEN target accounts and a filter with valid account_ids
    WHEN resolve_active_accounts is called
    THEN it should return the matching accounts in the requested order and selected IDs
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="B Account")
    acc2 = Account(id=2, account_type=AccountType.ASSET, name="A Account")
    target_accounts = [acc1, acc2]

    filter_dto = NonPhysicalValuationFilterDTO(account_ids=(2, 1))
    active, selected_ids = resolve_active_accounts(target_accounts, filter_dto)

    assert active == [acc2, acc1]
    assert selected_ids == (2, 1)


def test_resolve_active_accounts_filter_by_account_ids_invalid() -> None:
    """
    GIVEN target accounts and a filter with invalid account_ids
    WHEN resolve_active_accounts is called
    THEN it should raise ValueError identifying the invalid IDs
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Account 1")
    filter_dto = NonPhysicalValuationFilterDTO(account_ids=(1, 99, 100))

    with pytest.raises(
        ValueError,
        match=re.escape("Account ID(s) [99, 100] are not valid non-physical accounts."),
    ):
        resolve_active_accounts([acc1], filter_dto)


def test_resolve_active_accounts_filter_by_single_account_id_valid() -> None:
    """
    GIVEN target accounts and a filter with a single valid account_id
    WHEN resolve_active_accounts is called
    THEN it should return the matching account and single-element tuple of IDs
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Account 1")
    acc2 = Account(id=2, account_type=AccountType.ASSET, name="Account 2")

    filter_dto = NonPhysicalValuationFilterDTO(account_id=2)
    active, selected_ids = resolve_active_accounts([acc1, acc2], filter_dto)

    assert active == [acc2]
    assert selected_ids == (2,)


def test_resolve_active_accounts_filter_by_single_account_id_invalid() -> None:
    """
    GIVEN target accounts and a filter with a single invalid account_id
    WHEN resolve_active_accounts is called
    THEN it should raise ValueError
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Account 1")
    filter_dto = NonPhysicalValuationFilterDTO(account_id=99)

    with pytest.raises(
        ValueError,
        match=re.escape("Account with ID 99 is not a valid non-physical account."),
    ):
        resolve_active_accounts([acc1], filter_dto)


def test_resolve_active_accounts_no_filter_returns_all_sorted() -> None:
    """
    GIVEN target accounts and no filter
    WHEN resolve_active_accounts is called
    THEN it should return all target accounts sorted alphabetically and empty selected IDs
    """
    acc_b = Account(id=1, account_type=AccountType.ASSET, name="Beta Account")
    acc_a = Account(id=2, account_type=AccountType.ASSET, name="Alpha Account")

    active, selected_ids = resolve_active_accounts([acc_b, acc_a], None)

    assert active == [acc_a, acc_b]
    assert selected_ids == ()


def test_aggregate_monthly_account_changes_empty() -> None:
    """
    GIVEN no transactions
    WHEN aggregate_monthly_account_changes is called
    THEN it should return empty changes and has_activity False
    """
    changes, has_activity = aggregate_monthly_account_changes([], {1, 2})

    assert len(changes) == 0
    assert has_activity is False


def test_aggregate_monthly_account_changes_no_matching_accounts() -> None:
    """
    GIVEN transactions affecting account 99 and active accounts {1, 2}
    WHEN aggregate_monthly_account_changes is called
    THEN it should return empty changes and has_activity False
    """
    parent = Account(id=100, account_type=AccountType.ASSET, name="Parent")
    acc99 = Account(
        id=99, account_type=AccountType.ASSET, name="Unrelated", father_account=parent
    )
    acc_offset = Account(
        id=98, account_type=AccountType.EQUITY, name="Offset", father_account=parent
    )
    t = Transaction(
        id=1,
        date=date(2024, 1, 10),
        description="Test",
        lines=[
            TransactionLine(
                account=acc99, amount=Decimal("100.00"), entry_type=EntryType.DEBIT
            ),
            TransactionLine(
                account=acc_offset,
                amount=Decimal("100.00"),
                entry_type=EntryType.CREDIT,
            ),
        ],
    )
    changes, has_activity = aggregate_monthly_account_changes([t], {1, 2})

    assert len(changes) == 0
    assert has_activity is False


def test_aggregate_monthly_account_changes_with_activity() -> None:
    """
    GIVEN multiple transactions across different months for active accounts
    WHEN aggregate_monthly_account_changes is called
    THEN it should compute net balance impact per year-month and account, with has_activity True
    """
    parent = Account(id=100, account_type=AccountType.ASSET, name="Parent")
    acc1 = Account(
        id=1, account_type=AccountType.ASSET, name="Asset 1", father_account=parent
    )
    acc2 = Account(
        id=2, account_type=AccountType.ASSET, name="Asset 2", father_account=parent
    )
    acc_offset = Account(
        id=98, account_type=AccountType.EQUITY, name="Offset", father_account=parent
    )

    # t1: 2024-01-15, acc1 DEBIT 100 (+100 for ASSET)
    t1 = Transaction(
        id=1,
        date=date(2024, 1, 15),
        description="Jan txn 1",
        lines=[
            TransactionLine(
                account=acc1, amount=Decimal("100.00"), entry_type=EntryType.DEBIT
            ),
            TransactionLine(
                account=acc_offset,
                amount=Decimal("100.00"),
                entry_type=EntryType.CREDIT,
            ),
        ],
    )
    # t2: 2024-01-20, acc1 CREDIT 30 (-30 for ASSET), acc2 DEBIT 30 (+30 for ASSET)
    t2 = Transaction(
        id=2,
        date=date(2024, 1, 20),
        description="Jan txn 2",
        lines=[
            TransactionLine(
                account=acc1, amount=Decimal("30.00"), entry_type=EntryType.CREDIT
            ),
            TransactionLine(
                account=acc2, amount=Decimal("30.00"), entry_type=EntryType.DEBIT
            ),
        ],
    )
    # t3: 2024-03-05, acc2 CREDIT 20 (-20 for ASSET), acc_offset DEBIT 20
    t3 = Transaction(
        id=3,
        date=date(2024, 3, 5),
        description="Mar txn",
        lines=[
            TransactionLine(
                account=acc2, amount=Decimal("20.00"), entry_type=EntryType.CREDIT
            ),
            TransactionLine(
                account=acc_offset,
                amount=Decimal("20.00"),
                entry_type=EntryType.DEBIT,
            ),
        ],
    )

    changes, has_activity = aggregate_monthly_account_changes([t3, t1, t2], {1, 2})

    assert has_activity is True
    # 2024-01: acc1 = 100 - 30 = 70.00, acc2 = 30.00
    assert changes["2024-01"][1] == Decimal("70.00")
    assert changes["2024-01"][2] == Decimal("30.00")
    # 2024-03: acc2 = -20.00
    assert changes["2024-03"][2] == Decimal("-20.00")


def test_build_monthly_valuation_entries_empty() -> None:
    """
    GIVEN no monthly changes
    WHEN build_monthly_valuation_entries is called
    THEN it should return an empty list
    """
    assert build_monthly_valuation_entries([], {}) == []


def test_build_monthly_valuation_entries_with_gaps_and_running_balance() -> None:
    """
    GIVEN active accounts and monthly changes with gap months
    WHEN build_monthly_valuation_entries is called
    THEN it should generate continuous months carrying forward running balances
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Asset 1")
    acc2 = Account(id=2, account_type=AccountType.ASSET, name="Asset 2")

    monthly_changes = {
        "2024-01": {1: Decimal("100.00"), 2: Decimal("50.00")},
        "2024-03": {1: Decimal("25.00"), 2: Decimal("-10.00")},
    }

    entries = build_monthly_valuation_entries([acc1, acc2], monthly_changes)

    assert len(entries) == 3
    # Month 1: 2024-01
    assert entries[0].year_month == "2024-01"
    assert entries[0].month_label == "Jan 2024"
    assert entries[0].total_net_change == Decimal("150.00")
    assert entries[0].total_balance == Decimal("150.00")
    assert entries[0].account_values[0].balance == Decimal("100.00")
    assert entries[0].account_values[1].balance == Decimal("50.00")

    # Month 2: 2024-02 (gap month, net change = 0, running balance unchanged)
    assert entries[1].year_month == "2024-02"
    assert entries[1].month_label == "Feb 2024"
    assert entries[1].total_net_change == Decimal("0.00")
    assert entries[1].total_balance == Decimal("150.00")
    assert entries[1].account_values[0].balance == Decimal("100.00")
    assert entries[1].account_values[0].net_change == Decimal("0.00")
    assert entries[1].account_values[1].balance == Decimal("50.00")
    assert entries[1].account_values[1].net_change == Decimal("0.00")

    # Month 3: 2024-03 (100 + 25 = 125, 50 - 10 = 40, total 165)
    assert entries[2].year_month == "2024-03"
    assert entries[2].month_label == "Mar 2024"
    assert entries[2].total_net_change == Decimal("15.00")
    assert entries[2].total_balance == Decimal("165.00")
    assert entries[2].account_values[0].balance == Decimal("125.00")
    assert entries[2].account_values[1].balance == Decimal("40.00")


@pytest.mark.parametrize(
    "filter_dto,expected_yms",
    [
        (None, ["2024-01", "2024-02", "2024-03", "2024-04"]),
        (
            NonPhysicalValuationFilterDTO(start_date=date(2024, 2, 1)),
            ["2024-02", "2024-03", "2024-04"],
        ),
        (
            NonPhysicalValuationFilterDTO(end_date=date(2024, 3, 31)),
            ["2024-01", "2024-02", "2024-03"],
        ),
        (
            NonPhysicalValuationFilterDTO(
                start_date=date(2024, 2, 1), end_date=date(2024, 3, 31)
            ),
            ["2024-02", "2024-03"],
        ),
        (
            NonPhysicalValuationFilterDTO(start_date=date(2025, 1, 1)),
            [],
        ),
    ],
)
def test_filter_entries_by_date(
    filter_dto: Optional[NonPhysicalValuationFilterDTO], expected_yms: list[str]
) -> None:
    """
    GIVEN a list of monthly valuation entries
    WHEN filter_entries_by_date is called with various date filters
    THEN it should only return entries within the date boundaries
    """
    entries = [
        MonthlyValuationEntryDTO(
            year_month=ym,
            month_label=ym,
            total_balance=Decimal("100.00"),
            total_net_change=Decimal("10.00"),
            account_values=(),
        )
        for ym in ["2024-01", "2024-02", "2024-03", "2024-04"]
    ]

    filtered = filter_entries_by_date(entries, filter_dto)

    assert [e.year_month for e in filtered] == expected_yms
