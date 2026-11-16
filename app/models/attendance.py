"""Attendance, AttendanceLog – Hình 5.1; bảng attendances, attendance_logs – Hình 6.1."""
from datetime import datetime

from app.extensions import db
from .enums import AttendanceStatus, CheckInMethod, enum_col


class Attendance(db.Model):
    __tablename__ = "attendances"
    # BR1 / QT1 / NFR4: mỗi sinh viên đúng một bản ghi cho mỗi buổi
    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_attendances_session_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)
    status = db.Column(enum_col(AttendanceStatus, "ck_attendances_status"), nullable=False)
    check_in_time = db.Column(db.DateTime)
    method = db.Column(enum_col(CheckInMethod, "ck_attendances_method"), nullable=False)
    note = db.Column(db.String(255))

    session = db.relationship("ClassSession", back_populates="attendances")
    student = db.relationship("Student", back_populates="attendances")
    logs = db.relationship(
        "AttendanceLog", back_populates="attendance", cascade="all, delete-orphan",
        order_by="AttendanceLog.changed_at",
    )

    def update_status(self, new_status: AttendanceStatus, changed_by: int, reason: str):
        """UC7 – đổi trạng thái và tạo AttendanceLog (BR6)."""
        raise NotImplementedError("TODO TV2: AttendanceService.edit_attendance")


class AttendanceLog(db.Model):
    """Lịch sử sửa điểm danh: ai sửa, khi nào, giá trị cũ/mới, lý do (NFR11)."""

    __tablename__ = "attendance_logs"

    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("attendances.id", ondelete="CASCADE"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("lecturers.user_id"), nullable=False)
    old_status = db.Column(enum_col(AttendanceStatus, "ck_attendance_logs_old_status"), nullable=False)
    new_status = db.Column(enum_col(AttendanceStatus, "ck_attendance_logs_new_status"), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    attendance = db.relationship("Attendance", back_populates="logs")
    editor = db.relationship("Lecturer", back_populates="edited_logs")
