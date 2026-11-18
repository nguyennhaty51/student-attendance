from datetime import date, datetime, time, timedelta

import pytest
from flask import template_rendered
from jinja2 import ChoiceLoader, DictLoader

from app import create_app
from app.errors import FORBIDDEN, NOT_ENROLLED, NOT_FOUND, ServiceError
from app.extensions import db
from app.models import (
    Attendance, AttendanceStatus, CheckInMethod, ClassSection, ClassSession, Course, Enrollment, Lecturer,
    Notification, Student,
)
from app.services.attendance_service import AttendanceService
from app.services.notification_service import NotificationService
from config import TestConfig

P, A, L, E = (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LATE, AttendanceStatus.EXCUSED)
TODAY = date.today()


# ------------------------------------------------------------------ dựng dữ liệu
@pytest.fixture
def app():
    app = create_app(TestConfig)
    # Template của TV4 chưa chắc đã có: dùng bản giả để kiểm tra dữ liệu route truyền cho trang.
    app.jinja_env.loader = ChoiceLoader([
        DictLoader({"student/home.html": "M03", "student/notifications.html": "M07"}),
        app.jinja_env.loader,
    ])
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def world(app):
    """1 lớp (Lập trình Python), 1 sinh viên sv01 đã đăng ký, 6 buổi đã qua (chưa có điểm danh)."""
    lecturer = Lecturer(username="gv01", password="gv123", full_name="Nguyễn Văn An", email="gv@x.vn",
                        lecturer_code="GV001")
    course = Course(code="INT1001", name="Lập trình Python", credits=3)
    section = ClassSection(course=course, lecturer=lecturer, semester="2026-1", room="A101")
    student = Student(username="sv01", password="sv123", full_name="SV 1", email="s1@x.vn", student_code="SV001")
    other = Student(username="sv02", password="sv123", full_name="SV 2", email="s2@x.vn", student_code="SV002")
    sessions = [
        ClassSession(section=section, session_date=TODAY - timedelta(days=7 * n),
                     start_time=time(7, 0), end_time=time(9, 30))
        for n in range(6, 0, -1)
    ]
    db.session.add_all([lecturer, course, section, student, other, Enrollment(section=section, student=student),
                        *sessions])
    db.session.commit()
    return {"section": section, "student": student, "other": other, "sessions": sessions, "course": course}


def mark(session, student, status):
    db.session.add(Attendance(session=session, student=student, status=status, method=CheckInMethod.MANUAL))
    db.session.commit()


def mark_all(world, statuses):
    for session, status in zip(world["sessions"], statuses):
        mark(session, world["student"], status)


def check(world, **kwargs):
    return AttendanceService.check_absence_threshold(world["student"].id, world["section"].id, **kwargs)


def count_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id).count()


# ------------------------------------------------------------------ ClassSection.getAttendanceRate (QT7)
def test_late_counts_as_present_and_excused_is_not_absent(world):
    mark_all(world, [P, A, L, E, P, A])
    s = AttendanceService.attendance_summary(world["student"].id, world["section"].id)
    assert (s["held"], s["present"], s["absent"], s["late"], s["excused"]) == (6, 2, 2, 1, 1)
    assert s["absence_rate"] == pytest.approx(2 / 6)
    assert s["attendance_rate"] == pytest.approx(4 / 6)


def test_get_attendance_rate_on_model(world):
    mark_all(world, [P, A, L, E, P, A])
    section, student = world["section"], world["student"]
    assert section.get_attendance_rate(student.id) == pytest.approx(4 / 6)
    assert section.get_attendance_rate() == pytest.approx(4 / 6)  # cả lớp: chỉ có 1 sinh viên có dữ liệu


def test_class_rate_counts_all_students(world):
    db.session.add(Enrollment(section=world["section"], student=world["other"]))
    mark_all(world, [P, P, P, P, P, P])  # sv01: 6 lượt có mặt
    for session, status in zip(world["sessions"], [A, A, A, A, P, P]):
        mark(session, world["other"], status)  # sv02: 4 lượt vắng, 2 lượt có mặt
    assert world["section"].get_attendance_rate() == pytest.approx((6 + 2) / 12)


def test_no_data_gives_zero(world):
    s = AttendanceService.attendance_summary(world["student"].id, world["section"].id)
    assert s["held"] == 0 and s["attendance_rate"] == 0.0 and s["absence_rate"] == 0.0
    assert world["section"].get_attendance_rate() == 0.0


def test_session_without_records_or_in_future_is_not_held(world):
    mark_all(world, [P, P, P, P, P, A])
    future = ClassSession(section=world["section"], session_date=TODAY + timedelta(days=7),
                          start_time=time(7, 0), end_time=time(9, 30))
    db.session.add(future)
    db.session.commit()
    mark(future, world["student"], E)  # đơn nghỉ được duyệt trước cho buổi tương lai (UC8)
    s = AttendanceService.attendance_summary(world["student"].id, world["section"].id)
    assert s["held"] == 6 and s["excused"] == 0


# ------------------------------------------------------------------ kiểm tra ngưỡng
def test_exactly_at_threshold_is_not_exceeded(world):
    # 1 vắng / 5 buổi = 20% = ngưỡng → chưa vượt
    for session, status in zip(world["sessions"][:5], [A, P, P, P, P]):
        mark(session, world["student"], status)
    result = check(world)
    assert result["held"] == 5 and result["absent"] == 1
    assert result["exceeded"] is False and result["notification_id"] is None
    assert count_notifications(world["student"].id) == 0


def test_exceeding_threshold_creates_notification(world):
    mark_all(world, [A, A, P, P, P, P])  # 2/6 = 33% > 20%
    result = check(world)
    assert result["exceeded"] is True
    assert result["held"] == 6 and result["absent"] == 2
    assert result["absence_rate"] == pytest.approx(2 / 6)
    n = db.session.get(Notification, result["notification_id"])
    assert n.user_id == world["student"].id and n.is_read is False
    assert "2/6" in n.message and "Lập trình Python" in n.message and "33.3%" in n.message and "20%" in n.message


def test_repeated_checks_do_not_duplicate(world):
    mark_all(world, [A, A, P, P, P, P])
    first = check(world)
    second = check(world)
    third = check(world, commit=True)
    assert first["notification_id"] is not None
    assert second["exceeded"] and third["exceeded"]
    assert second["notification_id"] is None and third["notification_id"] is None
    assert count_notifications(world["student"].id) == 1


def test_read_warning_still_counts_as_warned(world):
    mark_all(world, [A, A, P, P, P, P])
    n = db.session.get(Notification, check(world)["notification_id"])
    NotificationService.mark_as_read(world["student"].id, n.id)
    assert check(world)["notification_id"] is None
    assert count_notifications(world["student"].id) == 1


def test_more_absences_is_a_new_level(world):
    mark_all(world, [A, A, P, P, P, P])
    check(world, commit=True)
    # sinh viên vắng thêm một buổi nữa (giảng viên sửa P → A)
    attendance = Attendance.query.filter_by(session_id=world["sessions"][2].id).one()
    attendance.status = A
    db.session.commit()
    result = check(world, commit=True)
    assert result["absent"] == 3 and result["notification_id"] is not None
    assert count_notifications(world["student"].id) == 2


def test_seeded_warning_is_recognised(world):
    # đúng khuôn thông báo mẫu trong scripts/seed.py (sv05: 3/6) → không tạo trùng
    db.session.add(Notification(
        user_id=world["student"].id,
        message="Cảnh báo: bạn đã vắng 3/6 buổi môn Lập trình Python (50%), vượt ngưỡng 20%."))
    db.session.commit()
    mark_all(world, [A, A, A, P, P, P])
    result = check(world, commit=True)
    assert result["exceeded"] is True and result["notification_id"] is None
    assert count_notifications(world["student"].id) == 1


def test_threshold_comes_from_config(app, world):
    mark_all(world, [A, A, P, P, P, P])  # 33%
    app.config["ABSENCE_THRESHOLD"] = 0.5
    assert check(world)["exceeded"] is False


def test_unknown_section_student_or_not_enrolled(world):
    with pytest.raises(ServiceError) as e:
        AttendanceService.check_absence_threshold(world["student"].id, 9999)
    assert e.value.code == NOT_FOUND
    with pytest.raises(ServiceError) as e:
        AttendanceService.check_absence_threshold(9999, world["section"].id)
    assert e.value.code == NOT_FOUND
    with pytest.raises(ServiceError) as e:
        AttendanceService.check_absence_threshold(world["other"].id, world["section"].id)
    assert e.value.code == NOT_ENROLLED


# ------------------------------------------------------------------ M03: dữ liệu theo hợp đồng
def test_student_course_summaries_shape(world):
    mark_all(world, [A, A, P, P, P, P])
    (row,) = AttendanceService.student_course_summaries(world["student"].id)
    assert row["section_id"] == world["section"].id
    assert row["course_code"] == "INT1001" and row["course_name"] == "Lập trình Python"
    assert row["lecturer_name"] == "Nguyễn Văn An" and row["section_label"] == "2026-1 - A101"
    assert (row["held"], row["present"], row["absent"], row["late"], row["excused"]) == (6, 4, 2, 0, 0)
    assert row["attendance_rate"] == pytest.approx(4 / 6) and row["absence_rate"] == pytest.approx(2 / 6)
    assert row["over_threshold"] is True
    assert AttendanceService.student_course_summaries(world["other"].id) == []


# ------------------------------------------------------------------ NotificationService / Student.view_notifications
def add_notification(user_id, message, minutes_ago=0, is_read=False):
    n = Notification(user_id=user_id, message=message, is_read=is_read,
                     created_at=datetime.utcnow() - timedelta(minutes=minutes_ago))
    db.session.add(n)
    db.session.commit()
    return n


def test_list_newest_first_unread_filter_and_count(world):
    uid = world["student"].id
    old = add_notification(uid, "cũ", minutes_ago=30, is_read=True)
    new = add_notification(uid, "mới", minutes_ago=1)
    add_notification(world["other"].id, "của người khác")
    assert [n.id for n in NotificationService.list_for_user(uid)] == [new.id, old.id]
    assert [n.id for n in NotificationService.list_for_user(uid, unread_only=True)] == [new.id]
    assert NotificationService.count_unread(uid) == 1
    assert [n.id for n in world["student"].view_notifications()] == [new.id, old.id]
    assert [n.id for n in world["student"].view_notifications(unread_only=True)] == [new.id]


def test_mark_as_read_rules(world):
    uid = world["student"].id
    n = add_notification(uid, "x")
    NotificationService.mark_as_read(uid, n.id)
    assert db.session.get(Notification, n.id).is_read is True
    NotificationService.mark_as_read(uid, n.id)  # gọi lại không lỗi
    with pytest.raises(ServiceError) as e:
        NotificationService.mark_as_read(uid, 9999)
    assert e.value.code == NOT_FOUND
    with pytest.raises(ServiceError) as e:
        NotificationService.mark_as_read(world["other"].id, n.id)
    assert e.value.code == FORBIDDEN


# ------------------------------------------------------------------ route
def login(client, username="sv01", password="sv123"):
    return client.post("/login", data={"username": username, "password": password})


def rendered(app):
    captured = []

    def record(_sender, template, context, **_extra):
        captured.append((template.name, context))

    template_rendered.connect(record, app, weak=False)  # weak=False: không để blinker thu hồi hàm cục bộ
    return captured


def test_student_home_passes_contract_data(app, world):
    mark_all(world, [A, A, P, P, P, P])
    add_notification(world["student"].id, "cảnh báo")
    client = app.test_client()
    login(client)
    captured = rendered(app)
    assert client.get("/student/home").status_code == 200
    name, ctx = captured[-1]
    assert name == "student/home.html"
    assert len(ctx["courses"]) == 1 and ctx["courses"][0]["over_threshold"] is True
    assert ctx["unread_warnings"] == 1 and ctx["threshold"] == pytest.approx(0.20)
    assert ctx["unread_notifications"] == 1  # biến dùng cho menu


def test_notifications_page_and_mark_read(app, world):
    uid = world["student"].id
    n = add_notification(uid, "cảnh báo vắng")
    client = app.test_client()
    login(client)
    captured = rendered(app)
    assert client.get("/student/notifications").status_code == 200
    (item,) = captured[-1][1]["notifications"]
    assert (item["id"], item["message"], item["is_read"]) == (n.id, "cảnh báo vắng", False)
    assert item["created_at"] is not None
    response = client.post(f"/student/notifications/{n.id}/read")
    assert response.status_code == 302 and response.headers["Location"].endswith("/student/notifications")
    db.session.expire_all()
    assert db.session.get(Notification, n.id).is_read is True


def test_cannot_mark_other_users_notification(app, world):
    n = add_notification(world["other"].id, "của sv02")
    client = app.test_client()
    login(client)
    response = client.post(f"/student/notifications/{n.id}/read")
    assert response.status_code == 302  # chuyển về M07 kèm thông báo lỗi
    db.session.expire_all()
    assert db.session.get(Notification, n.id).is_read is False


def test_student_pages_require_student_role(app, world):
    anonymous = app.test_client()
    assert anonymous.get("/student/home").status_code == 302
    assert "/login" in anonymous.get("/student/notifications").headers["Location"]
    client = app.test_client()
    login(client, "gv01", "gv123")
    assert client.get("/student/home").status_code == 403
    assert client.get("/student/notifications").status_code == 403
