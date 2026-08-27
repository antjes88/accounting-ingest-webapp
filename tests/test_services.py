import pytest
from datetime import date
from decimal import Decimal
from typing import Optional

from src.repository import PostgresRepository
from src.services import (
    record_new_transaction,
    record_new_account,
    get_postable_account_options,
    get_parent_account_options,
    get_account_type_options,
    get_all_transactions,
)
from src.dto import (
    CreateTransactionDTO,
    CreateAccountDTO,
    PostableAccountOptionDTO,
    ParentAccountOptionDTO,
    AccountTypeOptionDTO,
    TransactionViewDTO,
)
from src import model
from tests.helpers.sample_data import (
    cash_account,
    petty_cash_account,
    base_salary_account,
)


def test_record_new_transaction(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository with existing data and a valid CreateTransactionDTO object
    WHEN the record_new_transaction service is called with the repository and the DTO
    THEN the transaction should be successfully recorded in the database,
    and the transaction details and ledger entries should match the provided data.
    """
    transaction_date = date(2001, 6, 1)
    description = "Test services new trans"
    amount = Decimal("123.98")

    record_new_transaction(
        repo_with_data,
        transaction_dto=CreateTransactionDTO(
            date=transaction_date,
            description=description,
            amount=amount,
            debit_account_id=petty_cash_account.id,  # type: ignore
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )
    transaction_id = repo_with_data.get_max_transaction_id()

    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, transaction_date, transaction_description FROM {repo_with_data.transactions_table} WHERE transaction_id = {transaction_id}"
    ) == [(transaction_id, transaction_date, description)]
    assert repo_with_data.postgres_client.query(
        f"SELECT transaction_id, account_id, entry_type_id, amount "
        f"FROM {repo_with_data.ledger_entries_table} "
        f"WHERE transaction_id = {transaction_id} ORDER BY entry_type_id"
    ) == [
        (transaction_id, base_salary_account.id, 1, amount),
        (transaction_id, petty_cash_account.id, 2, amount),
    ]


@pytest.mark.parametrize(
    "new_account_name, new_account_type_id, is_physical, is_archived, father_account_id",
    [
        ("New Savings Account", model.AccountType.ASSET.id, True, False, None),
        (
            "New Checking Account",
            model.AccountType.ASSET.id,
            True,
            False,
            cash_account.id,
        ),
    ],
)
def test_record_new_account(
    new_account_name: str,
    new_account_type_id: int,
    is_physical: bool,
    is_archived: bool,
    father_account_id: Optional[int],
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository and a CreateAccountDTO
    WHEN the record_new_account service is called with the DTO
    THEN the account should be successfully recorded in the database,
    and its details should match the provided data.
    """
    account_dto = CreateAccountDTO(
        account_type_id=new_account_type_id,
        name=new_account_name,
        is_physical=is_physical,
        is_archived=is_archived,
        father_account_id=father_account_id,
    )

    record_new_account(repo_with_data, account_dto)

    max_account_id = repo_with_data.get_max_account_id()
    retrieved_account_data = repo_with_data.postgres_client.query(
        f"SELECT account_id, account_type_id, account_name, is_physical, is_archived, father_account_id "
        f"FROM {repo_with_data.accounts_table} WHERE account_id = {max_account_id}"
    )

    assert len(retrieved_account_data) == 1
    assert retrieved_account_data[0] == (
        max_account_id,
        new_account_type_id,
        new_account_name,
        is_physical,
        is_archived,
        father_account_id,
    )


def test_record_new_account_raises_value_error_when_father_account_not_found(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository and a CreateAccountDTO with a non-existent father account ID
    WHEN record_new_account service is called
    THEN a ValueError should be raised indicating that the father account was not found.
    """
    non_existent_id = 9999
    dto = CreateAccountDTO(
        account_type_id=model.AccountType.ASSET.id,
        name="Invalid Father Account",
        father_account_id=non_existent_id,
    )

    with pytest.raises(
        ValueError, match=f"Father account with ID {non_existent_id} not found."
    ):
        record_new_account(repo_with_data, dto)


def test_get_postable_account_options(repo_with_data: PostgresRepository) -> None:
    """
    GIVEN a PostgresRepository with sample accounts
    WHEN get_postable_account_options service is called
    THEN it should return only non-father, non-archived accounts as PostableAccountOptionDTOs.
    """
    options = get_postable_account_options(repo_with_data)
    petty_opt = next((opt for opt in options if opt.id == 2), None)
    base_salary_opt = next((opt for opt in options if opt.id == 4), None)

    # In sample data: Petty Cash (id=2) and Base Salary (id=4) are non-father & non-archived
    assert len(options) == 2
    assert all(isinstance(opt, PostableAccountOptionDTO) for opt in options)
    assert petty_opt is not None
    assert petty_opt.name == "Petty Cash"
    assert petty_opt.account_type_id == model.AccountType.ASSET.id
    assert petty_opt.account_type_name == "Asset"
    assert base_salary_opt is not None
    assert base_salary_opt.name == "Base Salary"


def test_get_parent_account_options(repo_with_data: PostgresRepository) -> None:
    """
    GIVEN a PostgresRepository with sample accounts
    WHEN get_parent_account_options service is called
    THEN it should return only father, non-archived accounts as ParentAccountOptionDTOs.
    """
    options = get_parent_account_options(repo_with_data)
    cash_opt = next((opt for opt in options if opt.id == 1), None)
    work_income_opt = next((opt for opt in options if opt.id == 3), None)

    # In sample data: Cash (id=1) and Work Income (id=3) are father & non-archived
    assert len(options) == 2
    assert all(isinstance(opt, ParentAccountOptionDTO) for opt in options)
    assert cash_opt is not None
    assert cash_opt.name == "Cash"
    assert cash_opt.account_type_id == model.AccountType.ASSET.id
    assert work_income_opt is not None
    assert work_income_opt.name == "Work Income"


def test_get_account_type_options():
    """
    GIVEN the model AccountType enum
    WHEN get_account_type_options service is called
    THEN it should return AccountTypeOptionDTOs matching all AccountType enum entries.
    """
    type_options = get_account_type_options()

    assert len(type_options) == len(model.AccountType)
    assert all(isinstance(opt, AccountTypeOptionDTO) for opt in type_options)
    assert [opt.id for opt in type_options] == [t.id for t in model.AccountType]
    assert [opt.display_name for opt in type_options] == [
        t.display_name for t in model.AccountType
    ]


def test_record_new_transaction_raises_value_error_when_debit_account_not_found(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository with existing accounts and a CreateTransactionDTO
    with a non-existent debit account ID
    WHEN record_new_transaction service is called
    THEN a ValueError should be raised indicating that the debit account was not found.
    """
    non_existent_id = 9999
    dto = CreateTransactionDTO(
        date=date(2024, 1, 1),
        description="Invalid debit account transaction",
        amount=Decimal("100.00"),
        debit_account_id=non_existent_id,
        credit_account_id=base_salary_account.id,  # type: ignore
    )

    with pytest.raises(
        ValueError, match=f"Debit account with ID {non_existent_id} not found."
    ):
        record_new_transaction(repo_with_data, dto)


def test_record_new_transaction_raises_value_error_when_credit_account_not_found(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a PostgresRepository with existing accounts and
    a CreateTransactionDTO with a non-existent credit account ID
    WHEN record_new_transaction service is called
    THEN a ValueError should be raised indicating that the credit account was not found.
    """
    non_existent_id = 9999
    dto = CreateTransactionDTO(
        date=date(2024, 1, 1),
        description="Invalid credit account transaction",
        amount=Decimal("100.00"),
        debit_account_id=petty_cash_account.id,  # type: ignore
        credit_account_id=non_existent_id,
    )

    with pytest.raises(
        ValueError, match=f"Credit account with ID {non_existent_id} not found."
    ):
        record_new_transaction(repo_with_data, dto)


def test_get_all_transactions(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository with sample transactions
    WHEN get_all_transactions service is called
    THEN it should return TransactionViewDTO objects correctly mapped from the repository.
    """
    transactions = get_all_transactions(repo_with_data)
    t = transactions[0]

    assert len(transactions) == 1
    assert isinstance(t, TransactionViewDTO)
    assert t.id == 1
    assert t.date == date(2024, 1, 1)
    assert t.description == "Test"
    assert t.amount == Decimal("100.00")
    assert t.debit_account_name == "Petty Cash"
    assert t.credit_account_name == "Base Salary"
