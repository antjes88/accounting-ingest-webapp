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


@dataclass(frozen=True)
class NonPhysicalAccountOptionDTO:
    id: int
    name: str
    account_type_id: int
    account_type_name: str
    is_father_account: bool


@dataclass(frozen=True)
class MonthlyAccountValueDTO:
    account_id: int
    account_name: str
    balance: Decimal
    net_change: Decimal


@dataclass(frozen=True)
class MonthlyValuationEntryDTO:
    year_month: str
    month_label: str
    total_balance: Decimal
    total_net_change: Decimal
    account_values: tuple[MonthlyAccountValueDTO, ...]


@dataclass(frozen=True)
class NonPhysicalValuationFilterDTO:
    account_ids: tuple[int, ...] = ()
    account_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass(frozen=True)
class NonPhysicalValuationViewDTO:
    accounts: tuple[NonPhysicalAccountOptionDTO, ...]
    selected_account_id: Optional[int]
    monthly_entries: tuple[MonthlyValuationEntryDTO, ...]
    total_current_value: Decimal
    latest_monthly_change: Decimal
    selected_account_ids: tuple[int, ...] = ()
