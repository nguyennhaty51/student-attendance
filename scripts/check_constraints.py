"""Kiểm tra nhanh các ràng buộc UNIQUE (tiêu chí hoàn thành). Chạy sau khi seed:

    python scripts/check_constraints.py

Mỗi phép chèn trùng phải bị CSDL từ chối (IntegrityError); script rollback nên không để lại dữ liệu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.exc import IntegrityError  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Attendance, AttendanceStatus, CheckInMethod, Course, Enrollment, Student,
)


def expect_rejected(label, make):
    try:
        db.session.add(make())
        db.session.flush()
    except IntegrityError:
        print(f"OK    bị từ chối: {label}")
        return True
    finally:
        db.session.rollback()
    print(f"LỖI   không bị từ chối: {label}")
    return False


def main():
    app = create_app()
    with app.app_context():
        att = Attendance.query.first()
        enr = Enrollment.query.first()
        stu = Student.query.first()
        course = Course.query.first()
        if not (att and enr and stu and course):
            sys.exit("Chưa có dữ liệu. Chạy: python scripts/seed.py")
        results = [
            expect_rejected("attendances (session_id, student_id) trùng", lambda: Attendance(
                session_id=att.session_id, student_id=att.student_id,
                status=AttendanceStatus.PRESENT, method=CheckInMethod.MANUAL)),
            expect_rejected("enrollments (section_id, student_id) trùng",
                            lambda: Enrollment(section_id=enr.section_id, student_id=enr.student_id)),
            expect_rejected("courses.code trùng", lambda: Course(code=course.code, name="Trùng mã", credits=3)),
            expect_rejected("students.student_code trùng", lambda: Student(
                username="khac", password="x", full_name="Khác", email="khac@school.edu.vn",
                student_code=stu.student_code)),
            expect_rejected("users.username trùng", lambda: Student(
                username=stu.username, password="x", full_name="Khác", email="khac2@school.edu.vn",
                student_code="SV9999999")),
            expect_rejected("users.email trùng", lambda: Student(
                username="khac3", password="x", full_name="Khác", email=stu.email, student_code="SV9999998")),
            expect_rejected("khóa ngoại sai (attendances.session_id không tồn tại)", lambda: Attendance(
                session_id=-1, student_id=stu.id, status=AttendanceStatus.PRESENT, method=CheckInMethod.MANUAL)),
        ]
        sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
