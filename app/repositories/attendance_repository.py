from sqlalchemy import func, select

from app.extensions import db
from app.models import (
    Attendance,
    AttendanceStatus,
    CheckInMethod,
    ClassSection,
    ClassSession,
    Enrollment,
)

# "Đã điểm danh" tính cả có mặt và đi muộn
_ATTENDED = (AttendanceStatus.PRESENT, AttendanceStatus.LATE)


class AttendanceRepository:
    # ---------- UC6 ----------
    def get_session(self, session_id):
        return db.session.get(ClassSession, session_id)

    def get_section_lecturer_id(self, class_section_id):
        return db.session.scalar(
            select(ClassSection.lecturer_id).where(ClassSection.id == class_section_id)
        )

    def code_in_use(self, code: str, exclude_session_id=None) -> bool:
        """Mã đã được buổi học khác dùng chưa (để các phiên đang mở không trùng PIN)."""
        stmt = select(ClassSession.id).where(ClassSession.check_in_code == code)
        if exclude_session_id is not None:
            stmt = stmt.where(ClassSession.id != exclude_session_id)
        return db.session.scalar(stmt.limit(1)) is not None

    def count_present(self, session_id) -> int:
        stmt = select(func.count(Attendance.id)).where(
            Attendance.class_session_id == session_id,
            Attendance.status.in_(_ATTENDED),
        )
        return db.session.scalar(stmt) or 0

    def count_students(self, class_section_id) -> int:
        stmt = select(func.count(Enrollment.id)).where(
            Enrollment.class_section_id == class_section_id
        )
        return db.session.scalar(stmt) or 0

    # ---------- UC3 ----------
    def find_session_by_code(self, code: str):
        stmt = select(ClassSession).where(ClassSession.check_in_code == code).limit(1)
        return db.session.scalar(stmt)

    def is_student_in_section(self, student_id, class_section_id) -> bool:
        stmt = select(Enrollment.id).where(
            Enrollment.student_id == student_id,
            Enrollment.class_section_id == class_section_id,
        ).limit(1)
        return db.session.scalar(stmt) is not None

    def has_attendance(self, student_id, session_id) -> bool:
        stmt = select(Attendance.id).where(
            Attendance.student_id == student_id,
            Attendance.class_session_id == session_id,
        ).limit(1)
        return db.session.scalar(stmt) is not None

    def add_present(self, student_id, session_id, check_in_time):
        """Ghi PRESENT + QR_PIN. flush để vi phạm unique nổ ngay tại đây."""
        record = Attendance(
            student_id=student_id,
            class_session_id=session_id,
            status=AttendanceStatus.PRESENT,
            method=CheckInMethod.QR_PIN,
            check_in_time=check_in_time,
        )
        db.session.add(record)
        db.session.flush()
        return record

    # ---------- giao dịch ----------
    def commit(self):
        db.session.commit()

    def rollback(self):
        db.session.rollback()
