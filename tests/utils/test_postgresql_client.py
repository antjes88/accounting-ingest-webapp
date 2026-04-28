import pytest
import datetime as dt

from utils.postgresql_client import PostgresGCPClient


@pytest.fixture(scope="function")
def execute_create_table(db_conn):
    statement_create_table = """
    DROP TABLE IF EXISTS test.simple; 
    DROP SCHEMA IF EXISTS test;
    
    CREATE SCHEMA test;

    CREATE TABLE test.simple (
        Id INT not null,
        Name VARCHAR(100) NOT NULL,
        Activated BOOLEAN not null,
        Date DATE NOT NULL
    );

    INSERT INTO test.simple 
    (Id, Name, Activated, Date) 
    VALUES 
    (1, 'Mercedes', true, '2020-01-01'),
    (2, 'Toyota', false, '2020-02-02');
    """
    db_conn.execute(statement_create_table)

    yield db_conn

    db_conn.execute("DROP TABLE IF EXISTS test.simple; DROP SCHEMA IF EXISTS test")


def test_execute(execute_create_table):
    statement = "SELECT * FROM test.simple ORDER BY id ASC;"
    actual_data = execute_create_table.query(statement)

    expected_data = [
        (1, "Mercedes", True, dt.date(2020, 1, 1)),
        (2, "Toyota", False, dt.date(2020, 2, 2)),
    ]

    print("Actual data:", actual_data)
    assert actual_data == expected_data


def test_execute_raises_exception_with_wrong_statement(db_conn):
    statement = "INVALID SQL STATEMENT;"
    with pytest.raises(Exception):
        db_conn.execute(statement)


def test_query_raises_exception_with_wrong_statement(db_conn):
    statement = "INVALID SQL STATEMENT;"
    with pytest.raises(Exception):
        db_conn.query(statement)


def test_create_connection_raises_exception_with_wrong_credentials(db_conn):
    db_conn_wrong_credentials = PostgresGCPClient(
        host="11.222.333.444",
        database_name="wrong_database",
        user_name="wrong_user",
        user_password="wrong_password",
    )
    with pytest.raises(Exception):
        db_conn_wrong_credentials.create_connection()
