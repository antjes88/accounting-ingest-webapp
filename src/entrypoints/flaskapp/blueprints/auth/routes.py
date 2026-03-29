from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash  # generate_password_hash
import os

from . import login_page


@login_page.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == os.environ["USERNAME"] and check_password_hash(
            os.environ["HASHED_PASSWORD"], password
        ):
            session["permanent"] = True
            session["logged_in"] = True
            session["user"] = username
            return redirect(url_for("home_page.home"))
        else:
            flash("Wrong Credentials", "danger")

    return render_template("login.html")


@login_page.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page.login"))
