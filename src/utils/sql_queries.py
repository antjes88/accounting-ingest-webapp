SELECT_FATHER_ACCOUNTS = """
SELECT
  acct.account_id,
  acty.account_type_id,
  acty.account_type_name,
  acct.account_name,
  acct.is_physical,
  acct.is_archived
FROM
  {accounts_table} acct
INNER JOIN
  {account_types_table} acty
ON acct.account_type_id = acty.account_type_id
WHERE acct.father_account_id IS NULL;
"""

SELECT_CHILDREN_ACCOUNTS = """
SELECT
  acct.account_id,
  acty.account_type_id,
  acty.account_type_name,
  acct.account_name,
  acct.is_physical,
  acct.is_archived,
  acct.father_account_id
FROM
  {accounts_table} acct
INNER JOIN
  {account_types_table} acty
ON acct.account_type_id = acty.account_type_id
WHERE acct.father_account_id IS NOT NULL;
"""

SELECT_MAX_ID_TRANSACTIONS = """
SELECT 
    CASE 
      WHEN max(transaction_id) IS NULL 
        THEN 0 
      ELSE max(transaction_id) 
    END AS max_id 
FROM {transactions_table};
"""

SELECT_ENTRY_TYPES = """
SELECT 
  entry_type_name,
  entry_type_id
FROM {entry_types_table}
ORDER BY entry_type_id;
"""


INSERT_NEW_TRANSACTION = """
INSERT INTO {transaction_table}
(transaction_id, transaction_date, transaction_description)
VALUES
(%s, %s, %s);

INSERT INTO {ledger_entries_table}
(transaction_id, account_id, entry_type_id, amount)
VALUES
(%s, %s, %s, %s),
(%s, %s, %s, %s)
"""

SELECT_MAX_ID_ACCOUNTS = """
SELECT
    CASE
      WHEN max(account_id) IS NULL
        THEN 0
      ELSE max(account_id)
    END AS max_id
FROM {accounts_table};
"""

INSERT_NEW_ACCOUNT = """
INSERT INTO {accounts_table}
(account_id, father_account_id, account_type_id, account_name, is_physical, is_archived)
VALUES
(%s, %s, %s, %s, %s, %s);
"""

SELECT_ALL_TRANSACTIONS = """
SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_description,
    le.account_id,
    le.entry_type_id,
    le.amount
FROM {transactions_table} t
INNER JOIN {ledger_entries_table} le ON t.transaction_id = le.transaction_id
{where_clause}
ORDER BY t.transaction_date DESC, t.transaction_id DESC;
"""
