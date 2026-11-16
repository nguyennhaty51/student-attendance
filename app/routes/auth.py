from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.enums import Role
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


def _home_by_role(role) -> str:
    if role == Role.ADMIN:
        return "/admin/users"        # M13 Manage Users
    elif role == Role.LECTURER:
        return "/lecturer/classes"   # M08 My Classes
    return "/student/home"           # M03 Student Home


def _safe_next(target) -> bool:
    """Chỉ chấp nhận đường dẫn nội bộ (tránh chuyển hướng ra trang ngoài)."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and "\\" not in target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home_by_role(current_user.role))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user, error = AuthService.login(username, password)
        if error:
            flash(error, "danger")
            return render_template("auth/login.html")
        next_url = request.args.get("next")
        return redirect(next_url if _safe_next(next_url) else _home_by_role(user.role))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    AuthService.logout()
    flash("Bạn đã đăng xuất khỏi hệ thống.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            flash("Mật khẩu mới và nhập lại mật khẩu không khớp.", "danger")
            return render_template("auth/change_password.html")

        ok, message = AuthService.change_password(current_user, old_password, new_password)
        if not ok:
            flash(message, "danger")
            return render_template("auth/change_password.html")

        flash(message, "success")
        return redirect(_home_by_role(current_user.role))

    return render_template("auth/change_password.html")