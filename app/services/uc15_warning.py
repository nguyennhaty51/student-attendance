from __future__ import annotations

from datetime import date

from flask import current_app
from sqlalchemy import select

from app.errors import NOT_ENROLLED, NOT_FOUND, ServiceError
from app.extensions import db
from app.models import Attendance, AttendanceStatus, ClassSection, ClassSession, Enrollment, Notification, Student


def get_threshold() -> float:
    return float(current_app.config.get("ABSENCE_THRESHOLD", 0.20))


class WarningAttendanceMixin:
    @staticmethod
    def attendance_summary(student_id: int, section_id: int) -> dict:
        today = date.today()
        rows = db.session.scalars(
            select(Attendance)
            .join(ClassSession, Attendance.session_id == ClassSession.id)
            .where(
                Attendance.student_id == student_id,
                ClassSession.section_id == section_id,
                ClassSession.session_date <= today,
            )
        ).all()

        present = sum(1 for r in rows if r.status == AttendanceStatus.PRESENT)
        absent = sum(1 for r in rows if r.status == AttendanceStatus.ABSENT)
        late = sum(1 for r in rows if r.status == AttendanceStatus.LATE)
        excused = sum(1 for r in rows if r.status == AttendanceStatus.EXCUSED)
        held = len(rows)

        if held == 0:
            attendance_rate = 0.0
            absence_rate = 0.0
        else:
            attendance_rate = (present + late + excused) / held
            absence_rate = absent / held

        return {
            "held": held,
            "present": present,
            "absent": absent,
            "late": late,
            "excused": excused,
            "attendance_rate": attendance_rate,
            "absence_rate": absence_rate,
        }

    @classmethod
    def check_absence_threshold(cls, student_id: int, section_id: int, commit: bool = True) -> dict:
        student = db.session.get(Student, student_id)
        if student is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy sinh viên.", 404)

        section = db.session.get(ClassSection, section_id)
        if section is None:
            raise ServiceError(NOT_FOUND, "Không tìm thấy lớp học phần.", 404)

        enrolled = db.session.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.section_id == section_id,
            )
        )
        if enrolled is None:
            raise ServiceError(NOT_ENROLLED, "Sinh viên không thuộc lớp học phần này.", 400)

        summary = cls.attendance_summary(student_id, section_id)
        held = summary["held"]
        absent = summary["absent"]
        absence_rate = summary["absence_rate"]
        threshold = get_threshold()

        exceeded = held > 0 and absence_rate > threshold
        notification_id = None

        if exceeded:
            course_name = section.course.name
            level_marker = f"vắng {absent}/{held} buổi môn {course_name}"
            already_warned = db.session.scalar(
                select(Notification.id).where(
                    Notification.user_id == student_id,
                    Notification.message.contains(level_marker),
                )
            )
            if already_warned is None:
                pct_str = f"{absence_rate * 100:.1f}".rstrip("0").rstrip(".")
                thresh_str = f"{threshold * 100:.1f}".rstrip("0").rstrip(".")
                msg = (
                    f"Cảnh báo: bạn đã vắng {absent}/{held} buổi môn {course_name} "
                    f"({pct_str}%), vượt ngưỡng {thresh_str}%."
                )
                notif = Notification(user_id=student_id, message=msg)
                db.session.add(notif)
                if commit:
                    db.session.commit()
                else:
                    db.session.flush()
                notification_id = notif.id

        return {
            **summary,
            "exceeded": exceeded,
            "notification_id": notification_id,
        }

    @classmethod
    def student_course_summaries(cls, student_id: int) -> list[dict]:
        enrollments = db.session.scalars(
            select(Enrollment).where(Enrollment.student_id == student_id)
        ).all()
        threshold = get_threshold()
        result = []
        for enr in enrollments:
            section = enr.section
            summary = cls.attendance_summary(student_id, section.id)
            over_threshold = summary["held"] > 0 and summary["absence_rate"] > threshold
            result.append({
                "section_id": section.id,
                "course_code": section.course.code,
                "course_name": section.course.name,
                "lecturer_name": section.lecturer.full_name,
                "section_label": f"{section.semester} - {section.room}",
                **summary,
                "over_threshold": over_threshold,
            })
        return result