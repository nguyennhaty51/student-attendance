from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.errors import LEAVE_DUPLICATE, LEAVE_NOT_IN_CLASS, NOT_FOUND, VALIDATION_ERROR, ServiceError
from app.extensions import db
from app.models import ClassSection, ClassSession, Enrollment, LeaveRequest, LeaveStatus, Student

REASON_MAX_LENGTH = 255  # khớp cột leave_requests.reason và hợp đồng M06


def session_label(session: ClassSession) -> str:
    """Nhãn một buổi học, ví dụ: 'INT1001 - Lập trình Python · 23/11/2026 07:00-09:30'."""
    course = session.section.course
    return (f"{course.code} - {course.name} · {session.session_date:%d/%m/%Y} "
            f"{session.start_time:%H:%M}-{session.end_time:%H:%M}")


def _duplicate_message(status: LeaveStatus) -> str:
    if status == LeaveStatus.PENDING:
        return "Bạn đã có đơn xin nghỉ đang chờ duyệt cho buổi này."
    if status == LeaveStatus.APPROVED:
        return "Đơn xin nghỉ cho buổi này đã được duyệt."
    return "Đơn xin nghỉ cho buổi này đã bị từ chối; không thể gửi lại cho cùng một buổi."


class LeaveService:
    @staticmethod
    def submit(student_id: int, session_id: int, reason: str) -> LeaveRequest:
        """UC4 – sinh viên gửi đơn xin nghỉ cho một buổi học. Lưu PENDING cùng thời điểm gửi.

        Kiểm tra: lý do không rỗng (≤ 255 ký tự); buổi học thuộc lớp sinh viên đang học (QT3);
        chưa có đơn cho buổi này (QT8).

        Bảng leave_requests có UNIQUE (student_id, session_id) theo ERD, nên một sinh viên chỉ có tối đa
        một đơn cho mỗi buổi, kể cả đơn đã duyệt hoặc bị từ chối: các trường hợp này cũng báo LEAVE_DUPLICATE
        (đơn đã xử lý không được đổi – BR8).
        """
        reason = (reason or "").strip()
        if not reason:
            raise ServiceError(VALIDATION_ERROR, "Vui lòng nhập lý do xin nghỉ.", 400)
        if len(reason) > REASON_MAX_LENGTH:
            raise ServiceError(VALIDATION_ERROR, f"Lý do không được dài quá {REASON_MAX_LENGTH} ký tự.", 400)

        if db.session.get(Student, student_id) is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy sinh viên.", 404)

        session = db.session.get(ClassSession, session_id)
        enrolled = session is not None and db.session.scalar(
            select(Enrollment.id).where(
                Enrollment.section_id == session.section_id, Enrollment.student_id == student_id,
            )
        ) is not None
        if not enrolled:
            raise ServiceError(LEAVE_NOT_IN_CLASS, "Buổi học không thuộc lớp học phần bạn đang theo học.", 400)

        existing = db.session.scalar(
            select(LeaveRequest).where(
                LeaveRequest.student_id == student_id, LeaveRequest.session_id == session_id,
            )
        )
        if existing is not None:
            raise ServiceError(LEAVE_DUPLICATE, _duplicate_message(existing.status), 409)

        leave = LeaveRequest(
            student_id=student_id,
            session_id=session_id,
            reason=reason,
            status=LeaveStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db.session.add(leave)
        try:
            db.session.commit()
        except IntegrityError as exc:  # hai lần gửi đồng thời: UNIQUE của CSDL chặn lần thứ hai
            db.session.rollback()
            raise ServiceError(LEAVE_DUPLICATE, "Bạn đã có đơn xin nghỉ cho buổi này.", 409) from exc
        return leave

    @staticmethod
    def list_upcoming_sessions(student_id: int, today: date | None = None) -> list[dict]:
        """Các buổi học sắp tới (từ hôm nay) của mọi lớp sinh viên đang học, gần nhất trước (M06)."""
        today = today or date.today()
        sessions = db.session.scalars(
            select(ClassSession)
            .join(ClassSection, ClassSection.id == ClassSession.section_id)
            .join(Enrollment, Enrollment.section_id == ClassSection.id)
            .where(Enrollment.student_id == student_id, ClassSession.session_date >= today)
            .order_by(ClassSession.session_date, ClassSession.start_time, ClassSession.id)
        ).all()
        return [{"session_id": s.id, "label": session_label(s)} for s in sessions]

    @staticmethod
    def requests_for_student(student_id: int) -> list[dict]:
        """Các đơn xin nghỉ sinh viên đã gửi kèm trạng thái, mới nhất trước (bảng "Đơn của tôi" ở M06)."""
        leaves = db.session.scalars(
            select(LeaveRequest)
            .where(LeaveRequest.student_id == student_id)
            .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
        ).all()
        return [
            {
                "id": leave.id,
                "session_label": session_label(leave.session),
                "reason": leave.reason,
                "created_at": leave.created_at,
                "status": leave.status.value,  # 'PENDING' | 'APPROVED' | 'REJECTED'
            }
            for leave in leaves
        ]
