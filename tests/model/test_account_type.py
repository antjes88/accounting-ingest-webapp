import pytest
from src.model import AccountType


def test_account_type_from_id_valid_id():
    """
    GIVEN a valid AccountType ID
    WHEN AccountType.from_id is called with that ID
    THEN the correct AccountType enum member should be returned.
    """
    assert AccountType.from_id(1) == AccountType.ASSET
    assert AccountType.from_id(4) == AccountType.REVENUE


def test_account_type_from_id_invalid_id():
    """
    GIVEN an invalid AccountType ID
    WHEN AccountType.from_id is called with that ID
    THEN a ValueError should be raised.
    """
    with pytest.raises(ValueError, match="No AccountType with id 99"):
        AccountType.from_id(99)

    with pytest.raises(ValueError, match="No AccountType with id 0"):
        AccountType.from_id(0)
