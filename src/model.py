from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, List
from decimal import Decimal
from enum import Enum


class AccountType(Enum):
    ASSET = (1, "Asset")
    LIABILITY = (2, "Liability")
    EQUITY = (3, "Equity")
    REVENUE = (4, "Revenue")
    EXPENSE = (5, "Expense")

    def __init__(self, id: int, display_name: str):
        self._id = id
        self._display_name = display_name

    @property
    def id(self) -> int:
        return self._id

    @property
    def display_name(self) -> str:
        return self._display_name

    @classmethod
    def from_id(cls, id_value: int) -> "AccountType":
        for member in cls:
            if member.id == id_value:
                return member
        raise ValueError(f"No AccountType with id {id_value}")


class EntryType(Enum):
    CREDIT = (1, "Credit")
    DEBIT = (2, "Debit")

    def __init__(self, id: int, display_name: str):
        self._id = id
        self._display_name = display_name

    @property
    def id(self) -> int:
        return self._id

    @property
    def display_name(self) -> str:
        return self._display_name


@dataclass
class Account:
    id: Optional[int]
    account_type: AccountType
    name: str
    father_account: Optional[Account] = None
    is_physical: bool = True
    is_archived: bool = False

    def __str__(self):
        return f"Account name: {self.name}"

    def __post_init__(self):
        if self.father_account is not None:
            if self.father_account.father_account is not None:
                raise ValueError(
                    f"Invalid hierarchy: Account '{self.father_account.name}' is already "
                    "a child account and cannot be assigned as a father account."
                )

    @property
    def is_father_account(self):
        if self.father_account:
            return False
        else:
            return True


@dataclass(frozen=True)
class TransactionLine:
    account: Account
    amount: Decimal
    entry_type: EntryType

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Transaction line amount must be greater than zero.")

        if self.account.is_archived:
            raise ValueError(
                f"Cannot create a transaction line for archived account: {self.account.name}."
            )

        if self.account.is_father_account:
            raise ValueError(
                f"Cannot create a transaction line for father account: {self.account.name}."
            )


class Transaction:
    def __init__(
        self,
        id: Optional[int],
        date: date,
        description: Optional[str],
        lines: List[TransactionLine],
    ):
        self._id = id
        self._date = date
        self._description = description
        self._lines = lines

        self._validate_integrity()

    def _validate_integrity(self):
        if len(self._lines) != 2:
            raise ValueError("A transaction must contain exactly two lines.")

        debits = sum(
            line.amount for line in self._lines if line.entry_type == EntryType.DEBIT
        )
        credits = sum(
            line.amount for line in self._lines if line.entry_type == EntryType.CREDIT
        )

        if debits != credits:
            raise ValueError("The transaction is not balanced.")

    def __eq__(self, other):
        if not isinstance(other, Transaction) or self._id is None or other._id is None:
            return self is other
        return self._id == other._id

    def __hash__(self):
        return hash(self._id) if self._id else id(self)

    def get_debit_account_id(self) -> int:
        return next(
            line.account.id
            for line in self._lines
            if line.entry_type == EntryType.DEBIT
        )  # type: ignore

    def get_credit_account_id(self) -> int:
        return next(
            line.account.id
            for line in self._lines
            if line.entry_type == EntryType.CREDIT
        )  # type: ignore

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def date(self) -> date:
        return self._date

    @property
    def amount(self) -> Decimal:
        return sum(
            (line.amount for line in self._lines if line.entry_type == EntryType.DEBIT),
            Decimal("0"),
        )

    @property
    def description(self) -> Optional[str]:
        return self._description
