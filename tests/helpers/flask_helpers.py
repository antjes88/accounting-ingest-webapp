def get_protected_routes(app):
    routes = []
    exclusions = ["static", "login_page.login"]

    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and rule.endpoint not in exclusions:
            if "<" not in rule.rule:
                routes.append(rule.rule)
    return routes
