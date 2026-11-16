"""Nạp dữ liệu mẫu. Chạy lại nhiều lần không lỗi và không tạo trùng (mỗi bản ghi tra theo khóa duy nhất).

    flask --app wsgi db upgrade      # tạo bảng (lần đầu)
    python scripts/seed.py

Chỉ dùng khi phát triển: mật khẩu mẫu rất đơn giản.
"""
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # gốc dự án (để import app)
sys.path.insert(0, HERE)                   # để import seed_data

from sqlalchemy import inspect  # noqa: E402

import seed_data as D  # noqa: E402
from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Admin, Attendance, AttendanceLog, AttendanceStatus, CheckInMethod, ClassSection, ClassSession, Course,
    Enrollment, LeaveRequest, LeaveStatus, Lecturer, Notification, Student,
)

counts = {}


def get_or_create(model, lookup, defaults=None):
    """Tra theo `lookup` (khóa duy nhất); chưa có thì tạo với lookup + defaults."""
    obj = model.query.filter_by(**lookup).first()
    if obj is not None:
        return obj
    obj = model(**lookup, **(defaults or {}))
    db.session.add(obj)
    db.session.flush()
    counts[model.__name__] = counts.get(model.__name__, 0) + 1
    return obj


def seed_users():
    a = D.ADMIN
    admin = get_or_create(Admin, {"username": a["username"]},
                          {k: a[k] for k in ("password", "full_name", "email")})
    lecturers = {}
    for l in D.LECTURERS:
        lecturers[l["username"]] = get_or_create(
            Lecturer, {"username": l["username"]},
            {k: l[k] for k in ("password", "full_name", "email", "lecturer_code", "department")})
    students = {}
    for i, s in enumerate(D.STUDENTS, start=1):
        students[i] = get_or_create(
            Student, {"username": s["username"]},
            {k: s[k] for k in ("password", "full_name", "email", "student_code", "class_name")})
    return admin, lecturers, students


def seed_academic(lecturers, students):
    courses = {c["code"]: get_or_create(Course, {"code": c["code"]}, {"name": c["name"], "credits": c["credits"]})
               for c in D.COURSES}
    sections, sessions = {}, {}
    for sec in D.SECTIONS:
        section = get_or_create(
            ClassSection,
            {"course_id": courses[sec["course"]].id, "lecturer_id": lecturers[sec["lecturer"]].id,
             "semester": D.SEMESTER, "room": sec["room"]})
        sections[sec["key"]] = section
        for k in sec["students"]:
            get_or_create(Enrollment, {"section_id": section.id, "student_id": students[k].id})
        for n in range(1, D.SESSIONS_PER_SECTION + 1):
            sessions[(sec["key"], n)] = get_or_create(
                ClassSession, {"section_id": section.id, "session_date": D.session_date(sec, n)},
                {"start_time": sec["start"], "end_time": sec["end"]})
    # Buổi 7 của S1 đang mở mã điểm danh để thử check-in; mỗi lần seed gia hạn thêm 1 ngày.
    open_session = sessions[("S1", D.OPEN_CODE_SESSION)]
    open_session.check_in_code = D.OPEN_CODE
    open_session.code_expiry = datetime.utcnow() + timedelta(days=1)
    return sections, sessions


def seed_attendance(students, sessions):
    for sec in D.SECTIONS:
        for n in range(1, D.HELD_SESSIONS + 1):
            session = sessions[(sec["key"], n)]
            for k in sec["students"]:
                status = D.planned_status(sec["key"], k, n)
                present_like = status in ("PRESENT", "LATE")
                qr = present_like and sec["key"] in ("S1", "S3")  # S2, S4: giảng viên điểm danh tay
                check_in_time = None
                if qr:
                    delay = 20 if status == "LATE" else 2
                    check_in_time = datetime.combine(session.session_date, sec["start"]) + timedelta(minutes=delay)
                get_or_create(
                    Attendance, {"session_id": session.id, "student_id": students[k].id},
                    {"status": AttendanceStatus[status],
                     "method": CheckInMethod.QR_PIN if qr else CheckInMethod.MANUAL,
                     "check_in_time": check_in_time})


def seed_log_leave_notification(lecturers, students, sessions):
    e = D.EDIT_LOG
    att = Attendance.query.filter_by(
        session_id=sessions[(e["section"], e["session_no"])].id, student_id=students[e["student"]].id).one()
    get_or_create(AttendanceLog, {"attendance_id": att.id, "reason": e["reason"]},
                  {"changed_by": lecturers[e["editor"]].id,
                   "old_status": AttendanceStatus[e["old"]], "new_status": AttendanceStatus[e["new"]]})

    a = D.APPROVED_LEAVE
    get_or_create(
        LeaveRequest,
        {"student_id": students[a["student"]].id, "session_id": sessions[(a["section"], a["session_no"])].id},
        {"reason": a["reason"], "status": LeaveStatus.APPROVED, "reviewed_by": lecturers[a["reviewer"]].id,
         "reviewed_at": datetime.utcnow()})
    p = D.PENDING_LEAVE
    get_or_create(
        LeaveRequest,
        {"student_id": students[p["student"]].id, "session_id": sessions[(p["section"], p["session_no"])].id},
        {"reason": p["reason"], "status": LeaveStatus.PENDING})

    get_or_create(
        Notification,
        {"user_id": students[5].id,
         "message": "Cảnh báo: bạn đã vắng 3/6 buổi môn Lập trình Python (50%), vượt ngưỡng 20%."},
        {"is_read": False})


def main():
    app = create_app()
    with app.app_context():
        if not inspect(db.engine).has_table("users"):
            sys.exit("Chưa có bảng. Chạy trước: flask --app wsgi db upgrade")
        admin, lecturers, students = seed_users()
        _, sessions = seed_academic(lecturers, students)
        seed_attendance(students, sessions)
        seed_log_leave_notification(lecturers, students, sessions)
        db.session.commit()

        print("Seed xong. Bản ghi mới tạo lần này:", counts or "không (dữ liệu đã đủ)")
        print(f"Tổng: {Admin.query.count()} admin, {Lecturer.query.count()} giảng viên, "
              f"{Student.query.count()} sinh viên, {Course.query.count()} môn, {ClassSection.query.count()} lớp, "
              f"{ClassSession.query.count()} buổi, {Attendance.query.count()} điểm danh")
        print(f"Phiên mã đang mở: lớp S1 buổi {D.OPEN_CODE_SESSION}, mã {D.OPEN_CODE} (hạn 1 ngày kể từ lần seed)")


if __name__ == "__main__":
    main()
