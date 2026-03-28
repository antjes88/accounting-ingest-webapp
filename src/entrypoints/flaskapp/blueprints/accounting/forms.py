from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, optional, InputRequired
from typing import List

from src import model


class NewTransactionForm(FlaskForm):
    type_debit = SelectField(
        "debit",
        default="-- Choose Account Type --",
        choices=[],
        validators=[DataRequired()],
        id="debit",
    )

    type_credit = SelectField(
        "credit",
        default="-- Choose Account Type --",
        choices=[],
        validators=[DataRequired()],
        id="credit",
    )

    account_debit = SelectField(
        "Account Debit",
        default="-- Choose an Account --",
        choices=[],
        validators=[DataRequired()],
        id="account_debit",
    )
    account_credit = SelectField(
        "Account Credit",
        default="-- Choose an Account --",
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

        acc_choices: List = [("", "-- Choose an Account --")]
        type_choices: List = [("", "-- Choose Account Type --")]
        for acc in accounts:
            if acc.father_account is not None:
                acc_choices.append(
                    (
                        acc.name,
                        acc.name,
                        {"data-type": acc.account_type.name},
                    )
                )
                if acc.account_type.name not in [choice[1] for choice in type_choices]:
                    type_choices.append(
                        (
                            acc.account_type.name,
                            acc.account_type.name,
                        )
                    )

        self.account_debit.choices = acc_choices
        self.account_credit.choices = acc_choices
        self.type_debit.choices = type_choices
        self.type_credit.choices = type_choices

    def to_transaction(self) -> model.Transaction:

        if self.amount.data and self.date.data:
            return model.Transaction(
                amount=Decimal(self.amount.data),
                description=self.description.data,
                date=self.date.data,
                id=None,
            )
        raise ValueError("Amount and Date are required fields")

    def get_debit_account(self, accounts: list[model.Account]) -> model.Account:
        for account in accounts:
            if account.name == self.account_debit.data:
                return account
        raise ValueError("No matching debit account found")

    def get_credit_account(self, accounts: list[model.Account]) -> model.Account:
        for account in accounts:
            if account.name == self.account_credit.data:
                return account
        raise ValueError("No matching credit account found")
