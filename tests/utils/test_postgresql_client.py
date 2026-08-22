import pytest
import datetime as dt
from typing import Generator

from utils.postgresql_client import PostgresGCPClient


@pytest.fixture(scope="function")
def execute_create_table(
    db_conn: PostgresGCPClient,
) -> Generator[PostgresGCPClient, None, None]:
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


def test_execute(execute_create_table: PostgresGCPClient):
    """
    GIVEN a PostgreSQL client connected to a database with a populated test table
    WHEN a query selecting all records ordered by ID is executed
    THEN it should return all rows matching the expected data.
    """
    statement = "SELECT * FROM test.simple ORDER BY id ASC;"
    actual_data = execute_create_table.query(statement)

    expected_data = [
        (1, "Mercedes", True, dt.date(2020, 1, 1)),
        (2, "Toyota", False, dt.date(2020, 2, 2)),
    ]

    assert actual_data == expected_data


def test_query_with_params(execute_create_table: PostgresGCPClient):
    """
    GIVEN a PostgreSQL client connected to a database with a populated test table
    WHEN a parameterized query is executed with specific filter parameters
    THEN it should return only the rows matching the parameters.
    """
    statement = "SELECT * FROM test.simple WHERE Id = %s AND Activated = %s;"
    params = (1, True)
    actual_data = execute_create_table.query(statement, params=params)

    expected_data = [
        (1, "Mercedes", True, dt.date(2020, 1, 1)),
    ]

    assert actual_data == expected_data


def test_execute_raises_exception_with_wrong_statement(db_conn: PostgresGCPClient):
    """
    GIVEN a PostgreSQL client connection
    WHEN execute is called with an invalid SQL statement
    THEN an Exception should be raised indicating an execution error.
    """
    statement = "INVALID SQL STATEMENT;"
    with pytest.raises(Exception):
        db_conn.execute(statement)


def test_query_raises_exception_with_wrong_statement(db_conn: PostgresGCPClient):
    """
    GIVEN a PostgreSQL client connection
    WHEN query is called with an invalid SQL statement
    THEN an Exception should be raised indicating a query error.
    """
    statement = "INVALID SQL STATEMENT;"
    with pytest.raises(Exception):
        db_conn.query(statement)


def test_create_connection_raises_exception_with_wrong_credentials():
    """
    GIVEN a PostgresGCPClient initialized with invalid database credentials
    WHEN create_connection is called
    THEN an Exception should be raised indicating a connection failure.
    """
    db_conn_wrong_credentials = PostgresGCPClient(
        host="11.222.333.444",
        database_name="wrong_database",
        user_name="wrong_user",
        user_password="wrong_password",
    )
    with pytest.raises(Exception):
        db_conn_wrong_credentials.create_connection()
