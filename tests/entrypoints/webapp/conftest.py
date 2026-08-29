from typing import Generator
import pytest
from flask.testing import FlaskClient
from tests.helpers.sample_data import web_credentials

from src.entrypoints.webapp.app import server


@pytest.fixture(scope="function")
def webapp_client() -> Generator[FlaskClient, None, None]:
    server.config["TESTING"] = True
    server.config["WTF_CSRF_ENABLED"] = False
    with server.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def client_logged_in(webapp_client: FlaskClient) -> Generator[FlaskClient, None, None]:
    webapp_client.post(
        "/login",
        data=web_credentials,
        follow_redirects=True,
    )

    yield webapp_client

    webapp_client.get("/logout", follow_redirects=True)
