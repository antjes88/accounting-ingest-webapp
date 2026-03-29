import os
from flask import url_for
import pytest

from src.entrypoints.flaskapp.app import server
from tests.helpers.flask_helpers import get_protected_routes
from tests.helpers.sample_data import web_credentials


def test_login_page_is_reached(client):
    """
    GIVEN a user surfing the web page
    WHEN tries to access login_page.login
    THEN makes sure that the right html is returned
    """
    response = client.get("/login", follow_redirects=False)

    assert 200 == response.status_code
    assert (
        b"<!--Login_form this comment is to check that it is reached on test-->"
        in response.data
    )


@pytest.mark.parametrize("rule", get_protected_routes(server))
def test_all_routes_redirect_to_login_if_not_logged_in(client, rule):

    response = client.get(rule, follow_redirects=False)

    print(f"Testing route: {rule} - Status Code: {response.status_code}")

    assert response.status_code == 302, f"Error in {rule}: should redirect."


def test_logout_works_correctly(client_logged_in):
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


def test_login_success(client):
    response = client.post(
        "/login",
        data=web_credentials,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        b"<!--menu this comment is to check that it is reached on test-->"
        in response.data
    )


def test_login_fails_with_wrong_credentials(client):
    """
    GIVEN a user with an existing account
    WHEN tries to login with a wrong password
    THEN a flash message "Wrong Credentials" is raised with category "danger"
    """
    data = {"username": "not", "password": "not"}
    response = client.post("/login", data=data, follow_redirects=True)
    html_content = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Wrong Credentials" in html_content
    assert "danger" in html_content
