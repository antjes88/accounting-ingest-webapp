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
class PostableAccountOptionDTO:
    id: int
    name: str
    account_type_id: int
    account_type_name: str


@dataclass(frozen=True)
class ParentAccountOptionDTO:
    id: int
    name: str
    account_type_id: int


@dataclass(frozen=True)
class TransactionViewDTO:
    id: int
    date: date
    description: Optional[str]
    amount: Decimal
    debit_account_name: str
    credit_account_name: str


@dataclass(frozen=True)
class TransactionFilterDTO:
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass(frozen=True)
class DeleteTransactionDTO:
    transaction_id: int
