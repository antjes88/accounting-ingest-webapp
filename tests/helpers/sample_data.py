import os

from src import model

web_credentials = {
    "username": os.environ["USERNAME"],
    "password": os.environ["PASSWORD"],
}

cash_account = model.Account(
    id=1,
    account_type=model.AccountType(id=1, name="Asset"),
    name="Cash",
    is_physical=True,
    is_archived=False,
)
petty_cash_account = model.Account(
    id=2,
    account_type=model.AccountType(id=1, name="Asset"),
    name="Petty Cash",
    is_physical=True,
    is_archived=True,
    father_account=cash_account,
)
work_income_account = model.Account(
    id=3,
    account_type=model.AccountType(id=4, name="Revenue"),
    name="Work Income",
    is_physical=True,
    is_archived=False,
)
base_salary_account = model.Account(
    id=4,
    account_type=model.AccountType(id=4, name="Revenue"),
    name="Base Salary",
    is_physical=True,
    is_archived=False,
    father_account=model.Account(
        id=3,
        account_type=model.AccountType(id=4, name="Revenue"),
        name="Work Income",
        is_physical=True,
        is_archived=False,
    ),
)
