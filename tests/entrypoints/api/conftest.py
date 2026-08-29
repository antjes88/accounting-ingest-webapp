from typing import Generator
import pytest
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token

from src.entrypoints.api.app import server


@pytest.fixture(scope="function")
def api_client() -> Generator[FlaskClient, None, None]:
    server.config["TESTING"] = True
    with server.test_client() as client:
        with server.app_context():
            yield client


@pytest.fixture(scope="function")
def auth_headers() -> dict[str, str]:
    with server.app_context():
        token = create_access_token(identity="test_user")
    return {"Authorization": f"Bearer {token}"}
