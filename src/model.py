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


@dataclass(frozen=True)
class TransactionLine:
    account: Account
    amount: Decimal
    entry_type: EntryType


@dataclass
class Transaction:
    id: Optional[int]
    date: date
    description: Optional[str]
    amount: Decimal
    lines: List[TransactionLine]

    def __post_init__(self):
        # By design, only one debit and one credit line
        if len(self.lines) != 2:
            raise ValueError("A transaction must contain exactly two lines.")

        total_debits = sum(
            line.amount
            for line in self.lines
            if line.entry_type.display_name == "Debit"
        )
        total_credits = sum(
            line.amount
            for line in self.lines
            if line.entry_type.display_name == "Credit"
        )

        if total_debits != total_credits:
            raise ValueError(
                f"Unbalanced entry. Total Debits ({total_debits}) must equal Total Credits ({total_credits})."
            )

    def get_debit_account_id(self) -> int:
        # By design, only one debit and one credit
        return next(
            line.account.id
            for line in self.lines
            if line.entry_type.display_name == "Debit"
        )  # type: ignore

    def get_credit_account_id(self) -> int:
        # By design, only one debit and one credit
        return next(
            line.account.id
            for line in self.lines
            if line.entry_type.display_name == "Credit"
        )  # type: ignore
