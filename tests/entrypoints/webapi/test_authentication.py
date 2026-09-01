from flask.testing import FlaskClient
import pytest

from tests.helpers.sample_data import web_credentials


def test_api_login_success(api_client: FlaskClient) -> None:
    """
    GIVEN a valid set of user credentials in environment variables
    WHEN the client sends a POST request to '/api/v1/auth/login' with matching credentials
    THEN the response status code should be 200 and contain a JWT access_token.
    """
    response = api_client.post(
        "/api/v1/auth/login",
        json=web_credentials,
    )
    json_data = response.get_json()

    assert response.status_code == 200
    assert "access_token" in json_data
    assert isinstance(json_data["access_token"], str)
    assert len(json_data["access_token"]) > 0


def test_api_login_invalid_credentials(api_client: FlaskClient) -> None:
    """
    GIVEN invalid login credentials
    WHEN the client sends a POST request to '/api/v1/auth/login'
    THEN the response status code should be 401 Unauthorized with an error message.
    """
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "wrong_user", "password": "wrong_password"},
    )
    json_data = response.get_json()

    assert response.status_code == 401
    assert json_data["message"] == "Invalid credentials"


@pytest.mark.parametrize(
    "invalid_payload",
    [
        pytest.param({}, id="empty_payload"),
        pytest.param({"username": "admin"}, id="missing_password"),
        pytest.param({"password": "secret"}, id="missing_username"),
    ],
)
def test_api_login_missing_fields(
    api_client: FlaskClient, invalid_payload: dict[str, str]
) -> None:
    """
    GIVEN incomplete credential payloads
    WHEN the client sends a POST request to '/api/v1/auth/login'
    THEN the response status code should be 422 Unprocessable Entity.
    """
    response = api_client.post(
        "/api/v1/auth/login",
        json=invalid_payload,
    )

    assert response.status_code == 422
