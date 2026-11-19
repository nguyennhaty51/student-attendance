from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.errors import LEAVE_DUPLICATE, VALIDATION_ERROR, ServiceError
from app.models.enums import Role
from app.services.leave_service import LeaveService

student_leave_bp = Blueprint("student_leave", __name__)


def _render_leave_page(
    error_code: str | None = None,
    error_message: str | None = None,
    form_data: dict | None = None,
    status_code: int = 200,
):
    return (
        render_template(
            "student/leave.html",
            upcoming_sessions=LeaveService.list_upcoming_sessions(current_user.id),
            my_requests=LeaveService.requests_for_student(current_user.id),
            error_code=error_code,
            error_message=error_message,
            form=form_data or {"session_id": "", "reason": ""},
        ),
        status_code,
    )


@student_leave_bp.route("/student/leave", methods=["GET", "POST"])
def leave_page():
    if not current_user.is_authenticated:
        return redirect("/login")
    if getattr(current_user, "role", None) != Role.STUDENT:
        abort(403)

    if request.method == "GET":
        return _render_leave_page()

    raw_session_id = request.form.get("session_id", "").strip()
    reason = request.form.get("reason", "")
    form_data = {"session_id": raw_session_id, "reason": reason}

    if not raw_session_id or not raw_session_id.isdigit():
        return _render_leave_page(
            error_code=VALIDATION_ERROR,
            error_message="Vui lòng chọn buổi học cần xin nghỉ.",
            form_data=form_data,
            status_code=400,
        )

    try:
        LeaveService.submit(current_user.id, int(raw_session_id), reason)
    except ServiceError as exc:
        http_status = 409 if exc.code == LEAVE_DUPLICATE else 400
        return _render_leave_page(
            error_code=exc.code,
            error_message=exc.message,
            form_data=form_data,
            status_code=http_status,
        )

    return redirect(url_for("student_leave.leave_page"))