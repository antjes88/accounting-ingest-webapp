from flask import Flask, session, request, redirect, url_for
import os
from datetime import timedelta

from src.entrypoints.flaskapp.blueprints.home import home_page
from src.entrypoints.flaskapp.blueprints.auth import login_page
from src.entrypoints.flaskapp.blueprints.accounting import accounting_pages
from src.utils.env_var_loader import env_var_loader

if os.environ.get("ISDEVCONTAINER"):
    env_var_loader(".env")


class Config:
    API_TITLE = "Accounting Ingest Web App"
    API_VERSION = "v1"
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-session-change-me")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)
    SESSION_REFRESH_EACH_REQUEST = True


server = Flask(__name__)
server.config.from_object(Config)

server.register_blueprint(home_page)
server.register_blueprint(login_page)
server.register_blueprint(accounting_pages)


@server.before_request
def require_login():
    if request.endpoint == "login_page.login":
        return
    if not session.get("logged_in"):
        return redirect(url_for("login_page.login"))
