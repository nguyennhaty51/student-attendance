from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)

from app.models import User
from app.extensions import bcrypt

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if (
            user
            and user.is_active
            and bcrypt.check_password_hash(
                user.password_hash,
                password
            )
        ):
            if user.role != "ADMIN":
                flash("Administrator access is required.", "danger")
                return redirect(url_for("auth.login"))

            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role

            return redirect(url_for("admin.users"))

        flash("Invalid credentials or locked account.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))