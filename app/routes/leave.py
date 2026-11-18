from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.errors import VALIDATION_ERROR, ServiceError
from app.models.enums import Role
from app.services.leave_service import LeaveService
from app.utils.decorators import role_required

leave_bp = Blueprint("leave", __name__)


def _parse_session_id(raw: str) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ServiceError(VALIDATION_ERROR, "Vui lòng chọn buổi học muốn xin nghỉ.", 400) from None


@leave_bp.route("/student/leave", methods=["GET", "POST"])
@role_required(Role.STUDENT)
def student_leave():
    """M06: danh sách buổi sắp tới, ô lý do, bảng "Đơn của tôi"; POST gửi đơn.

    Thành công: flash + chuyển hướng về M06 (PRG). Thất bại: hiển thị lại trang kèm `error_code`,
    `error_message` (và `form` để giữ lại nội dung đã nhập), HTTP status theo bảng mã lỗi.
    """
    error = None
    form = {"session_id": "", "reason": ""}

    if request.method == "POST":
        form = {"session_id": request.form.get("session_id", "").strip(), "reason": request.form.get("reason", "")}
        try:
            LeaveService.submit(current_user.id, _parse_session_id(form["session_id"]), form["reason"])
        except ServiceError as exc:
            error = exc
        else:
            flash("Đã gửi đơn xin nghỉ, vui lòng chờ giảng viên duyệt.", "success")
            return redirect(url_for("leave.student_leave"))

    response = render_template(
        "student/leave.html",
        upcoming_sessions=LeaveService.list_upcoming_sessions(current_user.id),
        my_requests=LeaveService.requests_for_student(current_user.id),
        error_code=error.code if error else None,
        error_message=error.message if error else None,
        form=form,
    )
    return response, (error.http_status if error else 200)
