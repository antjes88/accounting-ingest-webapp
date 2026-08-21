from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, optional

from src import model


class NewTransactionForm(FlaskForm):
    type_debit = SelectField(
        "debit",
        default="-- Select Account Type --",
        choices=[],
        validators=[DataRequired()],
        id="debit",
    )

    type_credit = SelectField(
        "credit",
        default="-- Select Account Type --",
        choices=[],
        validators=[DataRequired()],
        id="credit",
    )

    account_debit = SelectField(
        "Account Debit",
        default="-- Select an Account --",
        choices=[],
        validators=[DataRequired()],
        id="account_debit",
    )
    account_credit = SelectField(
        "Account Credit",
        default="-- Select an Account --",
        choices=[],
        validators=[DataRequired()],
        id="account_credit",
    )

    amount = FloatField("Amount", validators=[DataRequired()])
    description = StringField("Description", validators=[optional()])
    date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    submit = SubmitField("Submit")

    def __init__(self, accounts: list[model.Account], *args, **kwargs):
        super().__init__(*args, **kwargs)

        acc_choices = sorted(
            [
                ("", "-- Select an Account --"),
                *(
                    (
                        str(account.id),
                        account.name,
                        {"data-type": str(account.account_type.id)},
                    )
                    for account in accounts
                    if not account.is_father_account
                ),
            ],
            key=lambda x: x[1],
        )
        type_choices = sorted(
            [
                ("", "-- Select Account Type --"),
                *(
                    (str(account_type.id), account_type.display_name)
                    for account_type in model.AccountType
                ),
            ],
            key=lambda x: x[-1],
        )

        self.account_debit.choices = acc_choices
        self.account_credit.choices = acc_choices
        self.type_debit.choices = type_choices
        self.type_credit.choices = type_choices

    def to_transaction(self, accounts: list[model.Account]) -> model.Transaction:

        if self.amount.data and self.date.data:
            return model.Transaction(
                id=None,
                date=self.date.data,
                description=self.description.data,
                amount=Decimal(self.amount.data),
                lines=[
                    model.TransactionLine(
                        account=self.get_debit_account(accounts),
                        amount=Decimal(self.amount.data),
                        entry_type=model.EntryType.DEBIT,
                    ),
                    model.TransactionLine(
                        account=self.get_credit_account(accounts),
                        amount=Decimal(self.amount.data),
                        entry_type=model.EntryType.CREDIT,
                    ),
                ],
            )
        raise ValueError("Amount and Date are required fields")

    def get_debit_account(self, accounts: list[model.Account]) -> model.Account:
        for account in accounts:
            if account.id == int(self.account_debit.data):
                return account
        raise ValueError("No matching debit account found")

    def get_credit_account(self, accounts: list[model.Account]) -> model.Account:
        for account in accounts:
            if account.id == int(self.account_credit.data):
                return account
        raise ValueError("No matching credit account found")


class NewAccountForm(FlaskForm):
    account_type = SelectField(
        "Account Type",
        choices=[],
        validators=[DataRequired()],
        id="account_type",
    )
    name = StringField("Account Name", validators=[DataRequired()])
    father_account = SelectField(
        "Father Account (Optional)",
        choices=[],
        validators=[optional()],
        id="father_account",
    )
    is_physical = SelectField(
        "Is Physical Account?",
        choices=[("True", "Yes"), ("False", "No")],
        validators=[DataRequired()],
        id="is_physical",
    )
    is_archived = SelectField(
        "Is Archived?",
        choices=[("False", "No"), ("True", "Yes")],
        validators=[DataRequired()],
        id="is_archived",
    )
    submit = SubmitField("Create Account")

    def __init__(self, accounts: list[model.Account], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.account_type.choices = sorted(
            [
                ("", "-- Select Account Type --"),
                *(
                    (str(account_type.id), account_type.display_name)
                    for account_type in model.AccountType
                ),
            ],
            key=lambda x: x[-1],
        )
        self.father_account.choices = sorted(
            [
                ("", "-- Select Father Account (Optional) --"),
                *(
                    (
                        str(account.id),
                        account.name,
                        {"data-type": str(account.account_type.id)},
                    )
                    for account in accounts
                    if account.is_father_account
                ),
            ],
            key=lambda x: x[1],
        )

    def to_account(self, accounts: list[model.Account]) -> model.Account:
        father_acc = None
        if self.father_account.data:
            father_acc = next(
                (
                    account
                    for account in accounts
                    if account.id == int(self.father_account.data)
                ),
                None,
            )

        return model.Account(
            id=None,
            account_type=model.AccountType.from_id(int(self.account_type.data)),
            name=self.name.data,  # type: ignore
            father_account=father_acc,
            is_physical=self.is_physical.data == "True",
            is_archived=self.is_archived.data == "True",
        )
