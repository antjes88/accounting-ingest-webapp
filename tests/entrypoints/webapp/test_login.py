from flask.testing import FlaskClient
import pytest

from src.entrypoints.webapp.app import server
from tests.helpers.flask_helpers import get_protected_routes
from tests.helpers.sample_data import web_credentials


def test_login_page_is_reached(webapp_client: FlaskClient):
    """
    GIVEN a Flask client
    WHEN the '/login' page is requested
    THEN the response status code should be 200 and the login form HTML should be present.
    """
    response = webapp_client.get("/login", follow_redirects=False)

    assert 200 == response.status_code
    assert (
        b"<!--Login_form this comment is to check that it is reached on test-->"
        in response.data
    )


@pytest.mark.parametrize("rule", get_protected_routes(server))
def test_all_routes_redirect_to_login_if_not_logged_in(
    webapp_client: FlaskClient, rule: str
):
    """
    GIVEN a Flask client that is not logged in
    WHEN a protected route is accessed
    THEN the response status code should be 302 (redirect) to the login page.
    """

    response = webapp_client.get(rule, follow_redirects=False)

    assert response.status_code == 302, f"Error in {rule}: should redirect."


def test_logout_works_correctly(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in Flask client
    WHEN the client accesses the home page and then the '/logout' endpoint
    THEN the home page should be accessible (status 200) and contain the menu,
    and after logout, the login form HTML should be present, indicating a successful logout.
    """
    response_login = client_logged_in.get(
        "/",
        follow_redirects=True,
    )
    response_logout = client_logged_in.get(
        "/logout",
        follow_redirects=True,
    )

    assert response_login.status_code == 200
    assert (
        b"<!--menu this comment is to check that it is reached on test-->"
        in response_login.data
    )
    assert response_logout.status_code == 200
    assert (
        b"<!--Login_form this comment is to check that it is reached on test-->"
        in response_logout.data
    )


def test_login_success(webapp_client: FlaskClient):
    """
    GIVEN a Flask client and valid web credentials
    WHEN the client posts these credentials to the '/login' endpoint
    THEN the response status code should be 200 and the menu HTML should be present, indicating a successful login.
    """
    response = webapp_client.post(
        "/login",
        data=web_credentials,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        b"<!--menu this comment is to check that it is reached on test-->"
        in response.data
    )


def test_login_fails_with_wrong_credentials(webapp_client: FlaskClient):
    """
    GIVEN a Flask client and incorrect login credentials
    WHEN the client posts these credentials to the '/login' endpoint
    THEN the response status code should be 200 and a flash message "Wrong Credentials" with category "danger" should be displayed.
    """
    data = {"username": "not", "password": "not"}
    response = webapp_client.post("/login", data=data, follow_redirects=True)
    html_content = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Wrong Credentials" in html_content
    assert "danger" in html_content
