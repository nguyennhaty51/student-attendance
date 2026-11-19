from flask import Blueprint, flash, redirect, render_template, request, url_for
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

@notification_bp.route("/student/history")
@role_required(Role.STUDENT)
def student_history():
    """M05: lịch sử điểm danh theo môn học của sinh viên."""
    from app.models.academic import Enrollment, ClassSession
    from app.models.attendance import Attendance

    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    courses = []
    for e in enrollments:
        sec = e.section
        if sec and sec.course:
            label = f"{sec.course.code} - {sec.course.name} ({sec.semester})"
            courses.append({"section_id": sec.id, "label": label})

    raw_id = request.args.get("section_id", type=int)
    valid_ids = [c["section_id"] for c in courses]
    selected_section_id = raw_id if raw_id in valid_ids else (valid_ids[0] if valid_ids else None)

    rows = []
    if selected_section_id:
        sessions = (
            ClassSession.query.filter_by(section_id=selected_section_id)
            .order_by(ClassSession.session_date.asc(), ClassSession.start_time.asc())
            .all()
        )
        records = {
            r.session_id: r
            for r in Attendance.query.filter_by(student_id=current_user.id).all()
        }
        for s in sessions:
            rec = records.get(s.id)
            if not rec:
                continue
            status_val = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
            rows.append({
                "session_id": s.id,
                "session_date": s.session_date.strftime("%d/%m/%Y") if s.session_date else "",
                "start_time": s.start_time.strftime("%H:%M") if s.start_time else "",
                "end_time": s.end_time.strftime("%H:%M") if s.end_time else "",
                "status": status_val,
                "note": rec.note or "",
            })

        summary = AttendanceService.attendance_summary(current_user.id, selected_section_id)
    else:
        summary = {"present": 0, "absent": 0, "late": 0, "excused": 0, "attendance_rate": 0.0}

    return render_template(
        "student/history.html",
        courses=courses,
        selected_section_id=selected_section_id,
        rows=rows,
        summary=summary,
    )

