import os
import datetime as dt
from typing import Any
from flask import views
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

login = Blueprint(
    "authentication",
    __name__,
    url_prefix="/api/v1/auth",
    description="Authenticate user and issue JWT access tokens",
)


class CredentialsSchema(Schema):
    username = fields.String(
        required=True,
        metadata={"description": "User username for authentication"},
    )
    password = fields.String(
        required=True,
        metadata={"description": "User password for authentication"},
    )


Credentials = CredentialsSchema


class TokenResponseSchema(Schema):
    access_token = fields.String(
        required=True,
        metadata={"description": "JWT Bearer access token"},
    )


@login.route("/login")
class LoginResource(views.MethodView):

    @login.arguments(CredentialsSchema)
    @login.response(200, TokenResponseSchema)
    def post(self, credentials: dict[str, Any]) -> dict[str, str]:
        """Authenticate with username and password and receive a JWT access token"""
        expected_username = os.environ.get("USERNAME", "")
        hashed_password = os.environ.get("HASHED_PASSWORD", "")

        if credentials.get("username") == expected_username and check_password_hash(
            hashed_password, credentials.get("password", "")
        ):
            token = create_access_token(
                identity=credentials["username"],
                expires_delta=dt.timedelta(minutes=5),
            )
            return {"access_token": token}

        abort(401, message="Invalid credentials")
