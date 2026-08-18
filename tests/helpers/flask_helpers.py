from typing import List
from flask import Flask


def get_protected_routes(app: Flask) -> List[str]:
    routes = []
    exclusions = ["static", "login_page.login"]

    for rule in app.url_map.iter_rules():
        if (
            rule.methods is not None
            and "GET" in rule.methods
            and rule.endpoint not in exclusions
        ):
            if "<" not in rule.rule:
                routes.append(rule.rule)
    return routes
