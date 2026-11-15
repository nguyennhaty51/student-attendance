from functools import wraps

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash,
    abort, current_app
)

from app.models import User
from app.services.user_service import UserService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return redirect(url_for("auth.login"))

        user = User.query.get(user_id)

        if not user or not user.is_active or user.role != "ADMIN":
            session.clear()
            abort(403)

        return function(*args, **kwargs)

    return wrapper


@admin_bp.route("/users")
@admin_required
def users():

    keyword = request.args.get("search", "").strip()
    role = request.args.get("role", "").upper()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    pagination = UserService.list_users(
        keyword=keyword,
        role=role,
        page=page
    )

    return render_template(
        "users.html",
        users=pagination.items,
        pagination=pagination,
        search=keyword,
        selected_role=role
    )


@admin_bp.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():

    if request.method == "POST":
        try:
            user, temporary_password = UserService.create_user(
                request.form
            )

            session["temporary_password"] = temporary_password

            flash("User account created successfully.", "success")

            return redirect(url_for("admin.show_temporary_password"))

        except ValueError as error:
            flash(str(error), "danger")

    return render_template("user_form.html", user=None)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.role not in ("STUDENT", "LECTURER"):
        abort(403)

    if request.method == "POST":
        try:
            UserService.update_user(user_id, request.form)

            flash("User updated successfully.", "success")
            return redirect(url_for("admin.users"))

        except ValueError as error:
            flash(str(error), "danger")

    return render_template("user_form.html", user=user)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):

    try:
        user = UserService.toggle_active(user_id)

        status = "unlocked" if user.is_active else "locked"
        flash(f"Account successfully {status}.", "success")

    except ValueError as error:
        flash(str(error), "danger")

    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):

    try:
        temporary_password = UserService.reset_password(user_id)

        session["temporary_password"] = temporary_password

        return redirect(url_for("admin.show_temporary_password"))

    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("admin.users"))


@admin_bp.route("/temporary-password")
@admin_required
def show_temporary_password():

    temporary_password = session.pop("temporary_password", None)

    if not temporary_password:
        return redirect(url_for("admin.users"))

    return render_template(
        "temporary_password.html",
        temporary_password=temporary_password
    )