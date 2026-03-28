from flask import render_template, request

# own files
from . import home_page


@home_page.route("/")
def home():
    return render_template("menu.html")


@home_page.route("/successful")
def successful():
    return render_template(
        "home_page/successful.html",
        go_back_to=request.args.get("go_back_to"),
        blueprint=request.args.get("blueprint"),
    )


@home_page.route("/error")
def error_page():
    return render_template(
        "home_page/error_page.html", message=request.args.get("message")
    )
