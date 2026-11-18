from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user

from app.errors import ServiceError
from app.models.enums import Role
from app.services.attendance_service import AttendanceService, get_threshold
from app.services.notification_service import NotificationService
from app.utils.decorators import role_required

notification_bp = Blueprint("notifications", __name__)


@notification_bp.app_context_processor
def inject_unread_notifications():
    """Biến `unread_notifications` cho mọi template (số hiện cạnh mục Thông báo trên menu của sinh viên)."""
    if current_user.is_authenticated and current_user.role == Role.STUDENT:
        return {"unread_notifications": NotificationService.count_unread(current_user.id)}
    return {"unread_notifications": 0}


@notification_bp.route("/student/home")
@role_required(Role.STUDENT)
def student_home():
    """M03: bảng môn học kèm tỷ lệ, dải cảnh báo khi vượt ngưỡng."""
    return render_template(
        "student/home.html",
        courses=AttendanceService.student_course_summaries(current_user.id),
        unread_warnings=NotificationService.count_unread(current_user.id),
        threshold=get_threshold(),
    )


@notification_bp.route("/student/notifications")
@role_required(Role.STUDENT)
def notification_list():
    """M07: danh sách thông báo, mới nhất trước."""
    notifications = [
        {"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at}
        for n in NotificationService.list_for_user(current_user.id)
    ]
    return render_template("student/notifications.html", notifications=notifications)


@notification_bp.route("/student/notifications/<int:notification_id>/read", methods=["POST"])
@role_required(Role.STUDENT)
def mark_read(notification_id: int):
    """M07 – nút Đánh dấu đã đọc, xong chuyển về M07."""
    try:
        NotificationService.mark_as_read(current_user.id, notification_id)
    except ServiceError as exc:
        flash(exc.message, "danger")
    return redirect(url_for("notifications.notification_list"))
