import pytest

from src.model import Account, AccountType

father_account = Account(id=111, account_type=AccountType.ASSET, name="Parent Account")
child_account = Account(
    id=1,
    father_account=father_account,
    account_type=AccountType.ASSET,
    name="Child Account",
)
acc1 = Account(id=1, account_type=AccountType.ASSET, name="Cash")
acc1_duplicate = Account(
    id=1, account_type=AccountType.EXPENSE, name="Different Name", is_archived=True
)
acc2 = Account(id=2, account_type=AccountType.ASSET, name="Bank")
acc_none1 = Account(id=None, account_type=AccountType.ASSET, name="Cash None 1")
acc_none2 = Account(id=None, account_type=AccountType.ASSET, name="Cash None 2")


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


# Common Account fixtures for equality and hash tests


@pytest.mark.parametrize(
    "acc_a,acc_b,expected_equal",
    [
        (acc1, acc1_duplicate, True),
        (acc1, acc2, False),
        (acc_none1, acc_none1, True),
        (acc_none1, acc_none2, False),
        (acc1, acc_none1, False),
        (acc1, "not_an_account", False),
        (acc1, 1, False),
        (acc1, None, False),
    ],
    ids=[
        "same_id",
        "different_ids",
        "same_instance_none_id",
        "different_instances_none_id",
        "defined_id_vs_none_id",
        "vs_string",
        "vs_integer",
        "vs_none",
    ],
)
def test_account_equality(acc_a, acc_b, expected_equal: bool):
    """
    GIVEN two objects (at least one Account)
    WHEN evaluated for equality (__eq__)
    THEN the result should match the expected equality.
    """
    assert (acc_a == acc_b) == expected_equal


@pytest.mark.parametrize(
    "acc_a,acc_b,should_hash_equal,expected_set_len",
    [
        (acc1, acc1_duplicate, True, 1),
        (acc1, acc2, False, 2),
        (acc_none1, acc_none1, True, 1),
        (acc_none1, acc_none2, False, 2),
        (acc1, acc_none1, False, 2),
    ],
    ids=[
        "same_id_same_hash",
        "different_ids_different_hash",
        "same_none_id_instance_same_hash",
        "different_none_id_instances_different_hash",
        "defined_id_vs_none_id_different_hash",
    ],
)
def test_account_hash(acc_a, acc_b, should_hash_equal: bool, expected_set_len: int):
    """
    GIVEN two Account objects
    WHEN hash() is called and objects are added to a set
    THEN:
      - Hashes should be equal if and only if should_hash_equal is True.
      - Hash falls back to id(self) when id is None, or hash(id) when id is present.
      - Set length should match expected_set_len.
    """
    assert (hash(acc_a) == hash(acc_b)) == should_hash_equal
    assert len({acc_a, acc_b}) == expected_set_len
    if acc_a.id is None:
        assert hash(acc_a) == id(acc_a)
    else:
        assert hash(acc_a) == hash(acc_a.id)
