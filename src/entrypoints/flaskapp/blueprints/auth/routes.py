from flask import render_template, request, redirect, url_for, session, flash
import os

from . import login_page


@login_page.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # TODO: password should be hashed protected
        if username == os.environ["USERNAME"] and password == os.environ["PASSWORD"]:
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
