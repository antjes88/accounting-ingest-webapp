from flask import render_template, request

# own files
from . import home_page


@home_page.route("/")
def home():
    return render_template("menu.html")
