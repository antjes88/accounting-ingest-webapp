import pytest
from datetime import date
from decimal import Decimal
from src.model import Account, AccountType, EntryType, Transaction, TransactionLine

# Common test data
asset_type = AccountType.ASSET
revenue_type = AccountType.REVENUE
cash_account = Account(id=1, account_type=asset_type, name="Cash")

income_account = Account(id=3, account_type=revenue_type, name="Work Income")
debit_entry = EntryType.DEBIT
credit_entry = EntryType.CREDIT


def test_account_str_representation():
    """
    GIVEN an Account object
    WHEN its string representation is requested
    THEN it should return a formatted string containing the account name.
    """
    acc_type = AccountType.ASSET
    account = Account(id=1, account_type=acc_type, name="Cash")

    assert str(account) == "Account name: Cash"


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
    "lines",
    [
        ([]),
        (
            [
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=debit_entry,
                )
            ]
        ),
        (
            [
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=debit_entry,
                )
            ]
            * 3
        ),
    ],
)
def test_transaction_raises_value_error_for_incorrect_number_of_lines(lines):
    """
    GIVEN a list of transaction lines that does not contain exactly two lines
    WHEN a Transaction object is instantiated with these lines
    THEN a ValueError should be raised, indicating the incorrect number of lines.
    """

    with pytest.raises(
        ValueError, match="A transaction must contain exactly two lines."
    ):
        Transaction(
            id=None,
            date=date.today(),
            description="Invalid transaction",
            amount=Decimal("100.00"),
            lines=lines,
        )


def test_transaction_raises_value_error_for_unbalanced_entries():
    """
    GIVEN a list of two transaction lines where the total debit amount does not equal the total credit amount
    WHEN a Transaction object is instantiated with these unbalanced lines
    THEN a ValueError should be raised, indicating an unbalanced entry.
    """

    with pytest.raises(ValueError, match="Unbalanced entry. Total Debits"):
        Transaction(
            id=None,
            date=date.today(),
            description="Unbalanced transaction",
            amount=Decimal("100.00"),
            lines=[
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=debit_entry,
                ),
                TransactionLine(
                    account=income_account,
                    amount=Decimal("50.00"),
                    entry_type=credit_entry,
                ),
            ],
        )


def test_transaction_get_debit_id():
    """
    GIVEN a valid Transaction object
    WHEN get_debit_account_id is called
    THEN it should return the correct account ID for the debit line.
    """

    transaction = Transaction(
        id=None,
        date=date.today(),
        description="Valid transaction for ID retrieval",
        amount=Decimal("250.00"),
        lines=[
            TransactionLine(
                account=cash_account, amount=Decimal("250.00"), entry_type=debit_entry
            ),
            TransactionLine(
                account=income_account,
                amount=Decimal("250.00"),
                entry_type=credit_entry,
            ),
        ],
    )

    assert transaction.get_debit_account_id() == cash_account.id


def test_transaction_get_credit_account_ids():
    """
    GIVEN a valid Transaction object
    WHEN get_credit_account_id method is called
    THEN it should return the correct account ID for the credit line.
    """

    transaction = Transaction(
        id=None,
        date=date.today(),
        description="Valid transaction for ID retrieval",
        amount=Decimal("250.00"),
        lines=[
            TransactionLine(
                account=cash_account, amount=Decimal("250.00"), entry_type=debit_entry
            ),
            TransactionLine(
                account=income_account,
                amount=Decimal("250.00"),
                entry_type=credit_entry,
            ),
        ],
    )

    assert transaction.get_credit_account_id() == income_account.id
