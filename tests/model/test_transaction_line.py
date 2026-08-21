import pytest
from decimal import Decimal

from src.model import TransactionLine, Account, AccountType, EntryType

father_account = Account(id=111, account_type=AccountType.ASSET, name="Parent Account")
child_account = Account(
    id=1,
    father_account=father_account,
    account_type=AccountType.ASSET,
    name="Child Account",
)
archived_account = Account(
    id=2,
    father_account=father_account,
    account_type=AccountType.ASSET,
    name="Archived Account",
    is_archived=True,
)


def test_transaction_line_raises_value_error_on_negative_amount():
    """
    GIVEN a transaction line with a negative amount
    WHEN the transaction line is created
    THEN a ValueError should be raised, indicating the invalid amount.
    """
    with pytest.raises(
        ValueError,
        match="Transaction line amount must be greater than zero.",
    ):
        TransactionLine(
            account=child_account,
            amount=Decimal("-100.0"),
            entry_type=EntryType.DEBIT,
        )


def test_transaction_line_raises_value_error_on_archive_account():
    """
    GIVEN a transaction line with an account that is archived
    WHEN the transaction line is created
    THEN a ValueError should be raised, indicating the invalid account.
    """
    with pytest.raises(
        ValueError,
        match=f"Cannot create a transaction line for archived account: {archived_account.name}.",
    ):
        TransactionLine(
            account=archived_account,
            amount=Decimal("100.0"),
            entry_type=EntryType.DEBIT,
        )


def test_transaction_line_raises_value_error_on_father_account():
    """
    GIVEN a transaction line with an account that is a father account
    WHEN the transaction line is created
    THEN a ValueError should be raised, indicating the invalid account.
    """
    with pytest.raises(
        ValueError,
        match=f"Cannot create a transaction line for father account: {father_account.name}.",
    ):
        TransactionLine(
            account=father_account,
            amount=Decimal("100.0"),
            entry_type=EntryType.DEBIT,
        )
