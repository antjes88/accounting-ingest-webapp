import os
import pytest
import datetime as dt
from typing import Generator
from unittest.mock import MagicMock

from src.utils.postgresql_client import PostgresGCPClient, PostgresSQLClient


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


def test_failed_query_rolls_back_and_does_not_poison_pool(db_conn: PostgresGCPClient):
    """
    GIVEN an active PostgresGCPClient
    WHEN an invalid query causes an error in a pooled connection
    THEN the transaction is rolled back and the next query on the pool succeeds.
    """
    with pytest.raises(Exception):
        db_conn.execute("INVALID SQL STATEMENT;")

    # Next query should succeed without "current transaction is aborted"
    result = db_conn.query("SELECT 42;")
    assert result == [(42,)]


def test_client_close_cleans_up_pool():
    """
    GIVEN a PostgresGCPClient with an initialized connection pool
    WHEN close is called on the client
    THEN the pool is cleanly closed and removed from the active pools registry.
    """
    client = PostgresGCPClient(
        host=os.getenv("HOST") or "",
        database_name=os.getenv("DATABASE_NAME") or "",
        user_name=os.getenv("USER_NAME") or "",
        user_password=os.getenv("USER_PASSWORD") or "",
    )
    # Trigger pool creation
    client.query("SELECT 1;")
    assert client._pool_key in PostgresGCPClient._pools

    # Close pool
    client.close()
    assert client._pool_key not in PostgresGCPClient._pools


def test_execute_with_params(execute_create_table: PostgresGCPClient):
    """
    GIVEN a PostgreSQL client connected to a database with a test table
    WHEN execute is called with a parameterized UPDATE statement
    THEN the table records are updated accordingly.
    """
    statement = "UPDATE test.simple SET Activated = %s WHERE Id = %s;"
    execute_create_table.execute(statement, params=(False, 1))

    rows = execute_create_table.query("SELECT Activated FROM test.simple WHERE Id = 1;")
    assert rows == [(False,)]


def test_close_connection_when_conn_is_already_closed(db_conn: PostgresGCPClient):
    """
    GIVEN an active PostgresGCPClient and an already-closed connection
    WHEN close_connection is called with that connection
    THEN it should safely return it to the pool with close=True without errors.
    """
    cursor, conn = db_conn.create_connection()
    conn.close()
    assert conn.closed
    db_conn.close_connection(cursor, conn)


def test_close_connection_when_cursor_close_raises_exception(
    db_conn: PostgresGCPClient,
):
    """
    GIVEN a mock cursor whose close method raises an exception
    WHEN close_connection is called
    THEN it should catch and suppress the cursor exception and proceed to return the connection.
    """
    mock_cursor = MagicMock()
    mock_cursor.closed = False
    mock_cursor.close.side_effect = RuntimeError("Cursor close failed")

    cursor, conn = db_conn.create_connection()
    db_conn.close_connection(cursor, None)
    db_conn.close_connection(mock_cursor, conn)


def test_close_connection_when_rollback_raises_exception(db_conn: PostgresGCPClient):
    """
    GIVEN a connection whose rollback method raises an exception
    WHEN close_connection is called
    THEN it should discard the connection from the pool without raising an unhandled error.
    """
    cursor, conn = db_conn.create_connection()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.rollback.side_effect = RuntimeError("Rollback failed")

    pool = db_conn._get_pool()
    pool._rused[id(mock_conn)] = None  # type: ignore

    db_conn.close_connection(cursor, mock_conn)
    db_conn.close_connection(None, conn)


def test_close_connection_without_active_pool():
    """
    GIVEN a PostgresGCPClient whose connection pool is not initialized
    WHEN close_connection is called with a standalone open connection
    THEN it should close the connection directly.
    """
    client = PostgresGCPClient(
        host="127.0.0.1",
        database_name="uninitialized_db",
        user_name="user",
        user_password="password",
    )
    mock_conn = MagicMock()
    mock_conn.closed = False

    client.close_connection(None, mock_conn)
    mock_conn.close.assert_called_once()


def test_close_all_pools_with_active_pools(db_conn: PostgresGCPClient):
    """
    GIVEN active connection pools in PostgresSQLClient._pools
    WHEN close_all_pools is called
    THEN all pools should be closed and the registry cleared.
    """
    db_conn.query("SELECT 1;")
    assert len(PostgresSQLClient._pools) > 0

    PostgresSQLClient.close_all_pools()
    assert len(PostgresSQLClient._pools) == 0
