import pytest

from src.model import Account, AccountType

father_account = Account(id=111, account_type=AccountType.ASSET, name="Parent Account")
child_account = Account(
    id=1,
    father_account=father_account,
    account_type=AccountType.ASSET,
    name="Child Account",
)


def test_account_str_representation():
    """
    GIVEN an Account object
    WHEN its string representation is requested
    THEN it should return a formatted string containing the account name.
    """
    acc_type = AccountType.ASSET
    account = Account(id=1, account_type=acc_type, name="Cash")

    assert str(account) == "Account name: Cash"


def test_account_is_father_account_property():
    """
    GIVEN an Account object
    WHEN the is_father_account property is accessed
    THEN it should return True if the account has child accounts, otherwise False.
    """
    assert father_account.is_father_account is True
    assert child_account.is_father_account is False


def test_account_raises_value_error_for_incorrect_hierarchy():
    """
    GIVEN an account with a father account that is already a child account
    WHEN a new account is created with this father account
    THEN a ValueError should be raised, indicating the invalid hierarchy.
    """
    with pytest.raises(
        ValueError,
        match=f"Invalid hierarchy: Account '{child_account.name}' is already "
        "a child account and cannot be assigned as a father account.",
    ):
        Account(
            id=None,
            account_type=AccountType.ASSET,
            name="Cash",
            father_account=child_account,
        )
