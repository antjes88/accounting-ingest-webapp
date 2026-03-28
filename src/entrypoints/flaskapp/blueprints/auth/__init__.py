from flask import Blueprint

login_page = Blueprint(
    "login_page", __name__, template_folder="templates", static_folder="static"
)
from . import routes
