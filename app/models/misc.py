"""LeaveRequest, Notification, Report – Hình 5.1; bảng leave_requests, notifications – Hình 6.1.

Report chỉ có trong sơ đồ lớp (không có bảng): tính từ dữ liệu khi cần, nên CSDL đúng 11 bảng.
"""
from datetime import datetime

from app.extensions import db
from .enums import LeaveStatus, enum_col


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    __table_args__ = (
        db.UniqueConstraint("student_id", "session_id", name="uq_leave_requests_student_session"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("lecturers.user_id"))
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(enum_col(LeaveStatus, "ck_leave_requests_status"), nullable=False, default=LeaveStatus.PENDING)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    student = db.relationship("Student", back_populates="leave_requests")
    session = db.relationship("ClassSession", back_populates="leave_requests")
    reviewer = db.relationship("Lecturer", back_populates="reviewed_requests")

    def approve(self, lecturer_id: int):
        """UC8 – duyệt: buổi đó thành EXCUSED (BR8). Đã duyệt/từ chối thì không đổi được."""
        raise NotImplementedError("TODO TV3: LeaveService.approve")

    def reject(self, lecturer_id: int):
        """UC8."""
        raise NotImplementedError("TODO TV3: LeaveService.reject")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="notifications")

    def mark_as_read(self) -> None:
        """UC15 (M07 – Mark as read). Chưa commit."""
        self.is_read = True


class Report:
    """Báo cáo điểm danh (UC9, UC10). Phụ thuộc vào Attendance, không có bảng riêng."""

    def generate_by_section(self, section_id: int, date_from=None, date_to=None) -> dict:
        raise NotImplementedError("TODO TV3: ReportService.generate_by_section")

    def generate_by_student(self, student_id: int, section_id: int | None = None) -> dict:
        raise NotImplementedError("TODO TV3: ReportService.generate_by_student")

    def export_excel(self, report: dict, path: str) -> str:
        """Ghi file .xlsx (openpyxl), trả về đường dẫn."""
        raise NotImplementedError("TODO TV3: ReportService.export_excel")

    def export_pdf(self, report: dict, path: str) -> str:
        """Ghi file .pdf, trả về đường dẫn."""
        raise NotImplementedError("TODO TV3: ReportService.export_pdf")
