import secrets
import os
from flask import Flask
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

from src.entrypoints.webapi.blueprints.accounting import accounting
from src.entrypoints.webapi.blueprints.authentication import login

if os.environ.get("ISDEVCONTAINER") and not os.environ.get("ISTESTING"):
    load_dotenv(dotenv_path=".env", override=True)  # pragma: no cover

server = Flask(__name__)


class APIConfig:
    API_TITLE = "Accounting Ingest API"
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_bytes(32))
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    API_SPEC_OPTIONS = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
        "security": [{"bearerAuth": []}],
    }


server.config.from_object(APIConfig)
api = Api(server)
jwt = JWTManager(server)

api.register_blueprint(login)
api.register_blueprint(accounting)
