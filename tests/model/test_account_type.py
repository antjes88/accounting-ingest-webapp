import pytest
from decimal import Decimal
from src.model import AccountType, EntryType


def test_account_type_from_id_valid_id():
    """
    GIVEN a valid AccountType ID
    WHEN AccountType.from_id is called with that ID
    THEN the correct AccountType enum member should be returned.
    """
    assert AccountType.from_id(1) == AccountType.ASSET
    assert AccountType.from_id(4) == AccountType.REVENUE


def test_account_type_from_id_invalid_id():
    """
    GIVEN an invalid AccountType ID
    WHEN AccountType.from_id is called with that ID
    THEN a ValueError should be raised.
    """
    with pytest.raises(ValueError, match="No AccountType with id 99"):
        AccountType.from_id(99)

    with pytest.raises(ValueError, match="No AccountType with id 0"):
        AccountType.from_id(0)


@pytest.mark.parametrize(
    "account_type, entry_type, amount, expected_impact",
    [
        (AccountType.ASSET, EntryType.DEBIT, Decimal("100.00"), Decimal("100.00")),
        (AccountType.ASSET, EntryType.CREDIT, Decimal("100.00"), Decimal("-100.00")),
        (AccountType.EXPENSE, EntryType.DEBIT, Decimal("50.00"), Decimal("50.00")),
        (AccountType.EXPENSE, EntryType.CREDIT, Decimal("50.00"), Decimal("-50.00")),
        (AccountType.LIABILITY, EntryType.CREDIT, Decimal("200.00"), Decimal("200.00")),
        (AccountType.LIABILITY, EntryType.DEBIT, Decimal("200.00"), Decimal("-200.00")),
        (AccountType.EQUITY, EntryType.CREDIT, Decimal("300.00"), Decimal("300.00")),
        (AccountType.EQUITY, EntryType.DEBIT, Decimal("300.00"), Decimal("-300.00")),
        (AccountType.REVENUE, EntryType.CREDIT, Decimal("400.00"), Decimal("400.00")),
        (AccountType.REVENUE, EntryType.DEBIT, Decimal("400.00"), Decimal("-400.00")),
    ],
)
def test_calculate_balance_impact(
    account_type: AccountType,
    entry_type: EntryType,
    amount: Decimal,
    expected_impact: Decimal,
):
    """
    GIVEN an AccountType, an EntryType, and an amount
    WHEN calculate_balance_impact is called
    THEN the signed impact on normal balance should match double-entry rules.
    """
    assert account_type.calculate_balance_impact(entry_type, amount) == expected_impact
