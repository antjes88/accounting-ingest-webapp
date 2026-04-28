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
