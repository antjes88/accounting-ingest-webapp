from flask.testing import FlaskClient


def test_home_page_is_reached(client_logged_in: FlaskClient):
    """
    GIVEN a logged-in client
    WHEN the client requests the home page ("/")
    THEN the response status code should be 200 and the menu HTML should be present.
    """
    response = client_logged_in.get(
        "/",
        follow_redirects=True,
    )

    assert 200 == response.status_code
    assert (
        b"<!--menu this comment is to check that it is reached on test-->"
        in response.data
    )
