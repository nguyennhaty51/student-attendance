from flask import Blueprint, redirect, url_for
from flask_login import current_user
from app.routes.auth import _home_by_role

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(_home_by_role(current_user.role))
    return redirect(url_for("auth.login"))