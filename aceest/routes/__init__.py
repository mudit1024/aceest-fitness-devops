"""Flask blueprints for the ACEest application."""
from flask import jsonify, redirect, url_for

CLIENT_PAGE = "clients.client_page"


def client_not_found():
    """Standard JSON 404 for API calls that reference an unknown client."""
    return jsonify({"error": "client not found"}), 404


def back_to_client(name):
    """Redirect to the client page after an HTML form submission."""
    return redirect(url_for(CLIENT_PAGE, name=name))
