import os

from src import model

web_credentials: dict[str, str] = {
    "username": os.environ["USERNAME"],
    "password": os.environ["PASSWORD"],
}

cash_account = model.Account(
    id=1,
    account_type=model.AccountType.ASSET,
    name="Cash",
    is_physical=True,
    is_archived=False,
)
petty_cash_account = model.Account(
    id=2,
    account_type=model.AccountType.ASSET,
    name="Petty Cash",
    is_physical=True,
    is_archived=False,
    father_account=cash_account,
)
work_income_account = model.Account(
    id=3,
    account_type=model.AccountType.REVENUE,
    name="Work Income",
    is_physical=True,
    is_archived=False,
)
base_salary_account = model.Account(
    id=4,
    account_type=model.AccountType.REVENUE,
    name="Base Salary",
    is_physical=True,
    is_archived=False,
    father_account=work_income_account,
)
archived_account = model.Account(
    id=5,
    account_type=model.AccountType.REVENUE,
    name="Archived",
    is_physical=True,
    is_archived=True,
    father_account=work_income_account,
)
