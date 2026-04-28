import os
from flask import url_for
import pytest

from src.entrypoints.flaskapp.app import server
from tests.helpers.flask_helpers import get_protected_routes


def test_home_page_is_reached(client_logged_in):
    response = client_logged_in.get(
        "/",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--menu this comment is to check that it is reached on test-->"
        in response.data
    )
