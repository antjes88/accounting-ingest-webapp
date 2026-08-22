from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CreateTransactionDTO:
    date: date
    amount: Decimal
    debit_account_id: int
    credit_account_id: int
    description: Optional[str] = None


@dataclass(frozen=True)
class CreateAccountDTO:
    account_type_id: int
    name: str
    is_physical: bool = True
    is_archived: bool = False
    father_account_id: Optional[int] = None


@dataclass(frozen=True)
class AccountTypeOptionDTO:
    id: int
    display_name: str


@dataclass(frozen=True)
class AccountOptionDTO:
    id: int
    name: str
    account_type_id: int
    account_type_name: str
    is_selectable: bool
    is_father_account: bool
