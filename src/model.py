from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal
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
class Transaction:
    id: Optional[int]
    date: date
    description: Optional[str]
    amount: Decimal
