from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.errors import ServiceError
from app.models.enums import AttendanceStatus, Role
from app.services.attendance_service import AttendanceService
from app.services.uc5_manual_attendance import parse_attendance_form
from app.utils.decorators import role_required

attendance_bp = Blueprint("attendance", __name__)

# Template M09 do TV5 làm (TV5-1). Biến truyền vào: session, students, has_saved, error_code, error_message.
M09_TEMPLATE = "lecturer/attendance.html"


def _abort_if_denied(exc: ServiceError) -> None:
    """Không tìm thấy / sai lớp → trang 404 / 403 thay vì hiện lại form."""
    if exc.http_status in (403, 404):
        abort(exc.http_status)


def _overlay_submitted(rows: list[dict], form) -> None:
    """Giữ lại những gì giảng viên vừa nhập khi lưu bị lỗi, để không phải chọn lại cả lớp."""
    for row in rows:
        student_id = row["student_id"]
        raw_status = (form.get(f"status[{student_id}]") or "").strip().upper()
        if raw_status in AttendanceStatus.__members__:
            row["status"] = AttendanceStatus[raw_status]
        if f"note[{student_id}]" in form:
            row["note"] = form[f"note[{student_id}]"]
        row["reason"] = form.get(f"reason[{student_id}]", "")


@attendance_bp.route("/lecturer/sessions/<int:session_id>/attendance", methods=["GET", "POST"])
@role_required(Role.LECTURER)
def session_attendance(session_id):
    """M09 – xem/lưu điểm danh một buổi học (đúng lớp mình phụ trách – QT4)."""
    error = None
    if request.method == "POST":
        try:
            records = parse_attendance_form(request.form)
            AttendanceService.take_attendance(current_user.id, session_id, records)
        except ServiceError as exc:
            _abort_if_denied(exc)
            error = exc
        else:
            flash("Đã lưu điểm danh.", "success")
            return redirect(url_for("attendance.session_attendance", session_id=session_id))  # PRG

    try:
        sheet = AttendanceService.get_attendance_sheet(current_user.id, session_id)
    except ServiceError as exc:
        _abort_if_denied(exc)
        raise
    if error is not None:
        _overlay_submitted(sheet["students"], request.form)

    return render_template(
        M09_TEMPLATE,
        error_code=error.code if error else None,
        error_message=error.message if error else None,
        **sheet,
    ), (error.http_status if error else 200)
