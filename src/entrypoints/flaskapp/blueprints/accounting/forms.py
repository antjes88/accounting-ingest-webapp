from decimal import Decimal
from typing import Any
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, optional

from src.dto import (
    CreateTransactionDTO,
    CreateAccountDTO,
    AccountOptionDTO,
    AccountTypeOptionDTO,
)


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

    def __init__(
        self,
        account_options: list[AccountOptionDTO],
        type_options: list[AccountTypeOptionDTO],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        acc_choices = sorted(
            [
                ("", "-- Select an Account --"),
                *(
                    (
                        str(account.id),
                        account.name,
                        {"data-type": str(account.account_type_id)},
                    )
                    for account in account_options
                    if account.is_selectable
                ),
            ],
            key=lambda x: x[1],
        )
        type_choices = sorted(
            [
                ("", "-- Select Account Type --"),
                *(
                    (str(account_type.id), account_type.display_name)
                    for account_type in type_options
                ),
            ],
            key=lambda x: x[-1],
        )

        self.account_debit.choices = acc_choices
        self.account_credit.choices = acc_choices
        self.type_debit.choices = type_choices
        self.type_credit.choices = type_choices

    def to_dto(self) -> CreateTransactionDTO:

        return CreateTransactionDTO(
            date=self.date.data,  # type: ignore
            amount=Decimal(self.amount.data),  # type: ignore
            debit_account_id=int(self.account_debit.data),
            credit_account_id=int(self.account_credit.data),
            description=self.description.data,
        )


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

    def __init__(
        self,
        account_options: list[AccountOptionDTO],
        type_options: list[AccountTypeOptionDTO],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.account_type.choices = sorted(
            [
                ("", "-- Select Account Type --"),
                *(
                    (str(account_type.id), account_type.display_name)
                    for account_type in type_options
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
                        {"data-type": str(account.account_type_id)},
                    )
                    for account in account_options
                    if account.is_father_account
                ),
            ],
            key=lambda x: x[1],
        )

    def to_dto(self) -> CreateAccountDTO:

        return CreateAccountDTO(
            account_type_id=int(self.account_type.data),
            name=self.name.data,  # type: ignore
            father_account_id=(
                int(self.father_account.data) if self.father_account.data else None
            ),
            is_physical=self.is_physical.data == "True",
            is_archived=self.is_archived.data == "True",
        )
