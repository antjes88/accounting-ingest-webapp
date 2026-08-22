import pytest
from typing import List
from datetime import date
from decimal import Decimal

from src.model import Account, AccountType, EntryType, Transaction, TransactionLine

father_account = Account(
    id=111,
    account_type=AccountType.ASSET,
    name="Parent Account",
)
cash_account = Account(
    id=1,
    father_account=father_account,
    account_type=AccountType.ASSET,
    name="Cash",
)
income_account = Account(
    id=3,
    father_account=father_account,
    account_type=AccountType.REVENUE,
    name="Work Income",
)

valid_lines = [
    TransactionLine(
        account=cash_account,
        amount=Decimal("100.00"),
        entry_type=EntryType.DEBIT,
    ),
    TransactionLine(
        account=income_account,
        amount=Decimal("100.00"),
        entry_type=EntryType.CREDIT,
    ),
]

t1 = Transaction(id=1, date=date(2026, 1, 1), description="Tx 1", lines=valid_lines)
t1_duplicate = Transaction(
    id=1, date=date(2025, 1, 1), description="Different description", lines=valid_lines
)
t2 = Transaction(id=2, date=date(2026, 1, 1), description="Tx 2", lines=valid_lines)
t_none1 = Transaction(
    id=None, date=date(2026, 1, 1), description="Tx None 1", lines=valid_lines
)
t_none2 = Transaction(
    id=None, date=date(2026, 1, 1), description="Tx None 2", lines=valid_lines
)


def test_account_str_representation():
    """
    GIVEN an Account object
    WHEN its string representation is requested
    THEN it should return a formatted string containing the account name.
    """
    acc_type = AccountType.ASSET
    account = Account(id=1, account_type=acc_type, name="Cash")

    assert str(account) == "Account name: Cash"


@pytest.mark.parametrize(
    "lines",
    [
        ([]),
        (
            [
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=EntryType.DEBIT,
                )
            ]
        ),
        (
            [
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=EntryType.DEBIT,
                )
            ]
            * 3
        ),
    ],
)
def test_transaction_raises_value_error_for_incorrect_number_of_lines(
    lines: List[TransactionLine],
):
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
            date=date(2026, 1, 1),
            description="Invalid transaction",
            lines=lines,
        )


def test_transaction_raises_value_error_for_unbalanced_entries():
    """
    GIVEN a list of two transaction lines where the total debit amount does not equal the total credit amount
    WHEN a Transaction object is instantiated with these unbalanced lines
    THEN a ValueError should be raised, indicating an unbalanced entry.
    """

    with pytest.raises(ValueError, match="The transaction is not balanced."):
        Transaction(
            id=None,
            date=date(2026, 1, 1),
            description="Unbalanced transaction",
            lines=[
                TransactionLine(
                    account=cash_account,
                    amount=Decimal("100.00"),
                    entry_type=EntryType.DEBIT,
                ),
                TransactionLine(
                    account=income_account,
                    amount=Decimal("50.00"),
                    entry_type=EntryType.CREDIT,
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
        date=date(2026, 1, 1),
        description="Valid transaction for ID retrieval",
        lines=valid_lines,
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
        date=date(2026, 1, 1),
        description="Valid transaction for ID retrieval",
        lines=valid_lines,
    )

    assert transaction.get_credit_account_id() == income_account.id


@pytest.mark.parametrize(
    "tx_a,tx_b,expected_equal",
    [
        (t1, t1_duplicate, True),
        (t1, t2, False),
        (t_none1, t_none1, True),
        (t_none1, t_none2, False),
        (t1, t_none1, False),
        (t1, "not_a_transaction", False),
        (t1, 1, False),
        (t1, None, False),
    ],
    ids=[
        "same_id",
        "different_ids",
        "same_instance_none_id",
        "different_instances_none_id",
        "defined_id_vs_none_id",
        "vs_string",
        "vs_integer",
        "vs_none",
    ],
)
def test_transaction_equality(tx_a: Transaction, tx_b: object, expected_equal: bool):
    """
    GIVEN two objects (at least one Transaction)
    WHEN evaluated for equality (__eq__)
    THEN the result should match the expected equality.
    """
    assert (tx_a == tx_b) == expected_equal


@pytest.mark.parametrize(
    "tx_a,tx_b,should_hash_equal,expected_set_len",
    [
        (t1, t1_duplicate, True, 1),
        (t1, t2, False, 2),
        (t_none1, t_none1, True, 1),
        (t_none1, t_none2, False, 2),
        (t1, t_none1, False, 2),
    ],
    ids=[
        "same_id_same_hash",
        "different_ids_different_hash",
        "same_none_id_instance_same_hash",
        "different_none_id_instances_different_hash",
        "defined_id_vs_none_id_different_hash",
    ],
)
def test_transaction_hash(
    tx_a: Transaction, tx_b: Transaction, should_hash_equal: bool, expected_set_len: int
):
    """
    GIVEN two Transaction objects
    WHEN hash() is called and objects are added to a set
    THEN:
      - Hashes should be equal if and only if should_hash_equal is True.
      - Hash falls back to id(self) when id is None, or hash(id) when id is present.
      - Set length should match expected_set_len.
    """
    assert (hash(tx_a) == hash(tx_b)) == should_hash_equal
    assert len({tx_a, tx_b}) == expected_set_len
    if tx_a.id is None:
        assert hash(tx_a) == id(tx_a)
    else:
        assert hash(tx_a) == hash(tx_a.id)
