from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal, List
from decimal import Decimal


@dataclass(frozen=True)
class AccountType:
    id: Optional[int]
    name: Literal["Asset", "Liability", "Equity", "Revenue", "Expense"]


@dataclass(frozen=True)
class EntryType:
    id: Optional[int]
    name: Literal["Debit", "Credit"]


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
        # By desing, only one debit and credit line
        if len(self.lines) != 2:
            raise ValueError("A transaction must contain exactly two lines.")

        total_debits = sum(
            line.amount for line in self.lines if line.entry_type.name == "Debit"
        )
        total_credits = sum(
            line.amount for line in self.lines if line.entry_type.name == "Credit"
        )

        if total_debits != total_credits:
            raise ValueError(
                f"Unbalanced entry. Total Debits ({total_debits}) must equal Total Credits ({total_credits})."
            )

    def get_debit_account_id(self) -> int:
        # By desing, only one debit and credit
        return next(
            line.account.id for line in self.lines if line.entry_type.name == "Debit"
        )  # type: ignore

    def get_credit_account_id(self) -> int:
        # By desing, only one debit and credit
        return next(
            line.account.id for line in self.lines if line.entry_type.name == "Credit"
        )  # type: ignore
