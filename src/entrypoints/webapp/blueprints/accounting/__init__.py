from flask import Blueprint

accounting_pages = Blueprint(
    "accounting_pages",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/accounting",
)
from . import routes
