import os
import pytest
from typing import Generator

from src.utils.postgresql_client import PostgresGCPClient
from src.repository import PostgresRepository
from src.entrypoints.flaskapp.app import server
from tests.helpers.sample_data import web_credentials


@pytest.fixture(scope="session")
def db_conn() -> PostgresGCPClient:
    return PostgresGCPClient(
        host=os.getenv("HOST"),
        database_name=os.getenv("DATABASE_NAME"),
        user_name=os.getenv("USER_NAME"),
        user_password=os.getenv("USER_PASSWORD"),
    )


@pytest.fixture(scope="session")
def postgres_repo(db_conn: PostgresGCPClient) -> PostgresRepository:
    return PostgresRepository(postgres_client=db_conn)


@pytest.fixture(scope="module")
def repo_with_data(
    postgres_repo: PostgresRepository,
) -> Generator[PostgresRepository, None, None]:
    postgres_repo.postgres_client.execute(
        """
        TRUNCATE TABLE 
            accounting.ledger_entries, 
            accounting.transactions,
            accounting.accounts
        RESTART IDENTITY CASCADE;

        INSERT INTO accounting.accounts 
        (account_id, account_type_id, account_name, is_physical, is_archived, father_account_id)
        VALUES (1, 1, 'Cash', true, false, null),
               (2, 1, 'Petty Cash', true, true, 1),
               (3, 4, 'Work Income', true, false, null),
               (4, 4, 'Base Salary', true, false, 3);
        
        INSERT INTO accounting.transactions
        (transaction_id, transaction_date, transaction_description)
        VALUES (1, '2024-01-01', 'Test');

        INSERT INTO accounting.ledger_entries
        (transaction_id, account_id, entry_type_id, amount)
        VALUES 
        (1, 2, 2, 100.00),
        (1, 4, 1, 100.00);
        """
    )

    yield postgres_repo

    postgres_repo.postgres_client.execute(
        """
        TRUNCATE TABLE
            accounting.ledger_entries,
            accounting.transactions,
            accounting.accounts
        RESTART IDENTITY CASCADE;
        """
    )


@pytest.fixture(scope="function")
def client():
    server.config["TESTING"] = True
    server.config["WTF_CSRF_ENABLED"] = False
    with server.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def client_logged_in(client):
    client.post(
        "/login",
        data=web_credentials,
        follow_redirects=True,
    )

    yield client

    client.get("/logout", follow_redirects=True)
