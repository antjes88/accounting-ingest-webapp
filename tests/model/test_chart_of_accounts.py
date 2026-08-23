import pytest

from src.model import Account, AccountType, ChartOfAccounts


def test_chart_of_accounts_init_empty():
    """
    GIVEN no accounts provided
    WHEN a ChartOfAccounts is initialized
    THEN it should have an empty accounts list.
    """
    chart = ChartOfAccounts()
    assert chart.accounts == []


def test_chart_of_accounts_init_with_accounts():
    """
    GIVEN a list of valid unique accounts
    WHEN a ChartOfAccounts is initialized with this list
    THEN it should contain all accounts and allow lookup by id and name.
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Cash")
    acc2 = Account(id=2, account_type=AccountType.LIABILITY, name="Accounts Payable")

    chart = ChartOfAccounts([acc1, acc2])

    assert len(chart.accounts) == 2
    assert chart.get_account_by_id(1) == acc1
    assert chart.get_account_by_name("Cash") == acc1
    assert chart.get_account_by_name("cash") == acc1
    assert chart.get_account_by_name("NonExistent") is None


def test_chart_of_accounts_init_raises_on_duplicate_names():
    """
    GIVEN accounts with duplicate names (case-insensitive)
    WHEN a ChartOfAccounts is initialized
    THEN a ValueError should be raised.
    """
    acc1 = Account(id=1, account_type=AccountType.ASSET, name="Cash")
    acc2 = Account(id=2, account_type=AccountType.ASSET, name="cash")

    with pytest.raises(ValueError, match="Account with name 'cash' already exists."):
        ChartOfAccounts([acc1, acc2])


def test_chart_of_accounts_create_account_success():
    """
    GIVEN a valid ChartOfAccounts
    WHEN create_account is called with valid data
    THEN the new account should be added to the chart and returned.
    """
    parent = Account(id=10, account_type=AccountType.ASSET, name="Current Assets")
    chart = ChartOfAccounts([parent])

    new_acc = chart.create_account(
        name="Bank Savings",
        account_type=AccountType.ASSET,
        father_account_id=10,
        is_physical=True,
        is_archived=False,
    )

    assert new_acc.name == "Bank Savings"
    assert new_acc.account_type == AccountType.ASSET
    assert new_acc.father_account == parent
    assert new_acc in chart.accounts
    assert len(chart.accounts) == 2


def test_chart_of_accounts_create_account_raises_on_duplicate_name():
    """
    GIVEN an existing account with name 'Cash' in the chart
    WHEN attempting to create another account with name ' cash '
    THEN a ValueError should be raised.
    """
    existing_acc = Account(id=1, account_type=AccountType.ASSET, name="Cash")
    chart = ChartOfAccounts([existing_acc])

    with pytest.raises(ValueError, match="Account with name ' cash ' already exists."):
        chart.create_account(
            name=" cash ",
            account_type=AccountType.ASSET,
        )


def test_chart_of_accounts_create_account_raises_when_father_not_found():
    """
    GIVEN a non-existent father_account_id
    WHEN create_account is called
    THEN a ValueError should be raised.
    """
    chart = ChartOfAccounts()

    with pytest.raises(ValueError, match="Father account with ID 999 not found."):
        chart.create_account(
            name="Child Account",
            account_type=AccountType.ASSET,
            father_account_id=999,
        )


def test_chart_of_accounts_create_account_raises_when_father_is_child():
    """
    GIVEN a father account that is already a child of another account
    WHEN create_account is called using that account as father
    THEN a ValueError should be raised indicating invalid hierarchy.
    """
    grandparent = Account(id=1, account_type=AccountType.ASSET, name="Assets")
    parent_is_child = Account(
        id=2,
        account_type=AccountType.ASSET,
        name="Current Assets",
        father_account=grandparent,
    )
    chart = ChartOfAccounts([grandparent, parent_is_child])

    with pytest.raises(
        ValueError,
        match="Invalid hierarchy: Account 'Current Assets' is already a child account",
    ):
        chart.create_account(
            name="Sub Child",
            account_type=AccountType.ASSET,
            father_account_id=2,
        )


def test_chart_of_accounts_get_account_by_id_raises_when_not_found():
    """
    GIVEN a ChartOfAccounts
    WHEN get_account_by_id is called with an unknown ID
    THEN a ValueError should be raised.
    """
    chart = ChartOfAccounts()
    with pytest.raises(ValueError, match="Account with ID 404 not found."):
        chart.get_account_by_id(404)


def test_chart_of_accounts_postable_and_parent_accounts_filtering():
    """
    GIVEN a ChartOfAccounts with father, child, and archived accounts
    WHEN accessing postable_accounts and parent_accounts
    THEN postable_accounts should contain only non-father, non-archived accounts,
    and parent_accounts should contain only father, non-archived accounts.
    """
    parent = Account(id=1, account_type=AccountType.ASSET, name="Cash")
    child = Account(
        id=2,
        account_type=AccountType.ASSET,
        name="Petty Cash",
        father_account=parent,
    )
    archived_parent = Account(
        id=3,
        account_type=AccountType.EXPENSE,
        name="Old Parent",
        is_archived=True,
    )
    archived_child = Account(
        id=4,
        account_type=AccountType.EXPENSE,
        name="Old Child",
        father_account=parent,
        is_archived=True,
    )

    chart = ChartOfAccounts([parent, child, archived_parent, archived_child])

    assert chart.postable_accounts == [child]
    assert chart.parent_accounts == [parent]
