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
    delete_transaction,
    get_non_physical_account_options,
    get_non_physical_accounts_valuation,
)
from src.dto import (
    CreateTransactionDTO,
    CreateAccountDTO,
    PostableAccountOptionDTO,
    ParentAccountOptionDTO,
    AccountTypeOptionDTO,
    TransactionViewDTO,
    DeleteTransactionDTO,
    NonPhysicalValuationFilterDTO,
    NonPhysicalValuationViewDTO,
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
    THEN the transaction should be successfully recorded in the database and its ID returned,
    and the transaction details and ledger entries should match the provided data.
    """
    transaction_date = date(2001, 6, 1)
    description = "Test services new trans"
    amount = Decimal("123.98")

    transaction_id = record_new_transaction(
        repo_with_data,
        transaction_dto=CreateTransactionDTO(
            date=transaction_date,
            description=description,
            amount=amount,
            debit_account_id=petty_cash_account.id,  # type: ignore
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )

    assert transaction_id == repo_with_data.get_max_transaction_id()
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


def test_delete_transaction(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository with sample transactions and a DeleteTransactionDTO
    WHEN delete_transaction service is called
    THEN the transaction should be deleted from the repository.
    """
    assert len(get_all_transactions(repo_with_data)) == 1

    dto = DeleteTransactionDTO(transaction_id=1)
    delete_transaction(repo_with_data, dto)

    assert len(get_all_transactions(repo_with_data)) == 0


@pytest.mark.parametrize("invalid_id", [0, -1, -100])
def test_delete_transaction_raises_value_error_for_invalid_id(
    invalid_id: int,
):
    """
    GIVEN a DeleteTransactionDTO with an invalid transaction ID (<= 0)
    WHEN delete_transaction service is called
    THEN a ValueError should be raised.
    """
    dto = DeleteTransactionDTO(transaction_id=invalid_id)

    with pytest.raises(ValueError, match=f"Invalid transaction ID: {invalid_id}"):
        delete_transaction(None, dto)  # type: ignore


def test_get_non_physical_account_options(repo_with_data: PostgresRepository):
    """
    GIVEN a PostgresRepository with existing physical accounts
    WHEN a new non-physical account is added and get_non_physical_account_options is called
    THEN the non-physical account should be listed in the returned options.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Crypto Assets",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )

    options = get_non_physical_account_options(repo_with_data)
    assert any(opt.name == "Crypto Assets" for opt in options)


def test_get_non_physical_accounts_valuation_empty(repo_with_data: PostgresRepository):
    """
    GIVEN a repository with only physical accounts
    WHEN get_non_physical_accounts_valuation is called
    THEN an empty valuation view DTO should be returned with 0 current value.
    """
    valuation = get_non_physical_accounts_valuation(repo_with_data)
    assert isinstance(valuation, NonPhysicalValuationViewDTO)
    assert len(valuation.accounts) == 0
    assert len(valuation.monthly_entries) == 0
    assert valuation.total_current_value == Decimal("0.00")


def test_get_non_physical_accounts_valuation_with_accounts_but_no_activity(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with a non-physical account and transactions only affecting physical accounts
    WHEN get_non_physical_accounts_valuation is called
    THEN an empty valuation view DTO should be returned with accounts populated and 0 current value.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Inactive Crypto Wallet",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 15),
            amount=Decimal("100.00"),
            description="Physical transfer",
            debit_account_id=petty_cash_account.id,  # type: ignore
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )

    valuation = get_non_physical_accounts_valuation(repo_with_data)
    assert isinstance(valuation, NonPhysicalValuationViewDTO)
    assert len(valuation.accounts) == 1
    assert valuation.accounts[0].name == "Inactive Crypto Wallet"
    assert len(valuation.monthly_entries) == 0
    assert valuation.total_current_value == Decimal("0.00")
    assert valuation.latest_monthly_change == Decimal("0.00")


def test_get_non_physical_accounts_valuation_with_transactions(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with a non-physical account and transactions in Jan and Mar 2024
    WHEN get_non_physical_accounts_valuation is called
    THEN monthly entries should include Jan, Feb (gap maintained), and Mar with correct running balances.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Crypto Wallet",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    chart = repo_with_data.get_chart_of_accounts()
    crypto_acc = chart.get_account_by_name("Crypto Wallet")
    assert crypto_acc is not None
    assert crypto_acc.id is not None

    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 15),
            amount=Decimal("100.00"),
            debit_account_id=crypto_acc.id,
            credit_account_id=base_salary_account.id,  # type: ignore
            description="Buy crypto Jan",
        ),
    )
    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 3, 10),
            amount=Decimal("50.00"),
            debit_account_id=crypto_acc.id,
            credit_account_id=base_salary_account.id,  # type: ignore
            description="Buy crypto Mar",
        ),
    )

    valuation = get_non_physical_accounts_valuation(repo_with_data)

    assert len(valuation.monthly_entries) == 3
    # Newest first
    mar_entry, feb_entry, jan_entry = valuation.monthly_entries

    assert jan_entry.year_month == "2024-01"
    assert jan_entry.total_net_change == Decimal("100.00")
    assert jan_entry.total_balance == Decimal("100.00")

    assert feb_entry.year_month == "2024-02"
    assert feb_entry.total_net_change == Decimal("0.00")
    assert feb_entry.total_balance == Decimal("100.00")

    assert mar_entry.year_month == "2024-03"
    assert mar_entry.total_net_change == Decimal("50.00")
    assert mar_entry.total_balance == Decimal("150.00")

    assert valuation.total_current_value == Decimal("150.00")
    assert valuation.latest_monthly_change == Decimal("50.00")


def test_get_non_physical_accounts_valuation_filter_by_account_and_date(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with multiple non-physical accounts and transactions
    WHEN filtering by account ID and date range
    THEN only the filtered account and months within the date range should be returned.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Crypto Wallet 1",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Crypto Wallet 2",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    chart = repo_with_data.get_chart_of_accounts()
    w1 = chart.get_account_by_name("Crypto Wallet 1")
    w2 = chart.get_account_by_name("Crypto Wallet 2")
    assert w1 and w2 and w1.id and w2.id

    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 15),
            amount=Decimal("100.00"),
            debit_account_id=w1.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )
    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 2, 10),
            amount=Decimal("200.00"),
            debit_account_id=w2.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )

    filter_dto = NonPhysicalValuationFilterDTO(
        account_id=w1.id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )
    valuation = get_non_physical_accounts_valuation(repo_with_data, filter_dto)

    assert len(valuation.monthly_entries) == 1
    assert valuation.monthly_entries[0].year_month == "2024-01"
    assert valuation.monthly_entries[0].total_balance == Decimal("100.00")
    assert valuation.selected_account_id == w1.id


def test_get_non_physical_accounts_valuation_raises_for_invalid_account_id(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with non-physical accounts
    WHEN filtering by an account ID that is not a non-physical account
    THEN a ValueError should be raised.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="NFT Fund",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    with pytest.raises(
        ValueError, match="Account with ID 9999 is not a valid non-physical account."
    ):
        get_non_physical_accounts_valuation(
            repo_with_data,
            NonPhysicalValuationFilterDTO(account_id=9999),
        )


def test_get_non_physical_accounts_valuation_filter_by_multiple_account_ids(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with multiple non-physical accounts and transactions
    WHEN filtering by a tuple of multiple account IDs
    THEN only the filtered accounts and their combined valuation should be returned.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Multi Token A",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Multi Token B",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Multi Token C",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    chart = repo_with_data.get_chart_of_accounts()
    ta = chart.get_account_by_name("Multi Token A")
    tb = chart.get_account_by_name("Multi Token B")
    tc = chart.get_account_by_name("Multi Token C")
    assert ta and tb and tc and ta.id and tb.id and tc.id

    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 10),
            amount=Decimal("150.00"),
            debit_account_id=ta.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )
    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 15),
            amount=Decimal("250.00"),
            debit_account_id=tb.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )
    record_new_transaction(
        repo_with_data,
        CreateTransactionDTO(
            date=date(2024, 1, 20),
            amount=Decimal("500.00"),
            debit_account_id=tc.id,
            credit_account_id=base_salary_account.id,  # type: ignore
        ),
    )

    filter_dto = NonPhysicalValuationFilterDTO(
        account_ids=(ta.id, tb.id),
    )
    valuation = get_non_physical_accounts_valuation(repo_with_data, filter_dto)

    assert len(valuation.monthly_entries) == 1
    assert valuation.monthly_entries[0].total_balance == Decimal("400.00")
    assert valuation.selected_account_ids == (ta.id, tb.id)
    assert valuation.selected_account_id is None


def test_get_non_physical_accounts_valuation_raises_for_invalid_account_ids(
    repo_with_data: PostgresRepository,
):
    """
    GIVEN a repository with non-physical accounts
    WHEN filtering by account_ids containing non-existent or invalid accounts
    THEN a ValueError should be raised detailing the invalid IDs.
    """
    record_new_account(
        repo_with_data,
        CreateAccountDTO(
            account_type_id=model.AccountType.ASSET.id,
            name="Valid Virtual Account",
            is_physical=False,
            is_archived=False,
            father_account_id=cash_account.id,
        ),
    )
    with pytest.raises(
        ValueError,
        match=r"Account ID\(s\) \[8888, 9999\] are not valid non-physical accounts.",
    ):
        get_non_physical_accounts_valuation(
            repo_with_data,
            NonPhysicalValuationFilterDTO(account_ids=(8888, 9999)),
        )
