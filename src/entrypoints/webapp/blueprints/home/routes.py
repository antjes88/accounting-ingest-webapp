from flask import render_template

# own files
from . import home_page


@home_page.route("/")
def home():
    return render_template("menu.html")
