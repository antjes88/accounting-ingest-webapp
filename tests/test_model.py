from src.model import Account, AccountType


def test_account_str_representation():
    acc_type = AccountType(id=1, name="Asset")
    account = Account(id=1, account_type=acc_type, name="Cash")

    assert str(account) == "Account name: Cash"
