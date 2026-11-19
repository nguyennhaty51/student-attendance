from datetime import date, datetime, time, timedelta

import pytest
from flask import template_rendered
from jinja2 import ChoiceLoader, DictLoader

from app import create_app
from app.errors import LEAVE_DUPLICATE, LEAVE_NOT_IN_CLASS, NOT_FOUND, VALIDATION_ERROR, ServiceError
from app.extensions import db
from app.models import (
    ClassSection, ClassSession, Course, Enrollment, LeaveRequest, LeaveStatus, Lecturer, Student,
)
from app.services.leave_service import LeaveService
from config import TestConfig

TODAY = date.today()


# ------------------------------------------------------------------ dựng dữ liệu
@pytest.fixture
def app():
    app = create_app(TestConfig)
    # Template của TV4 chưa chắc đã có: dùng bản giả để kiểm tra dữ liệu route truyền cho trang.
    app.jinja_env.loader = ChoiceLoader([
        DictLoader({"student/leave.html": "M06"}),
        app.jinja_env.loader,
    ])
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def world(app):
    """sv01 học lớp Python (1 buổi đã qua, 2 buổi sắp tới); sv02 chỉ học lớp CSDL; gv01 là giảng viên."""
    lecturer = Lecturer(username="gv01", password="gv123", full_name="Nguyễn Văn An", email="gv@x.vn",
                        lecturer_code="GV001")
    python = Course(code="INT1001", name="Lập trình Python", credits=3)
    database = Course(code="INT1002", name="Cơ sở dữ liệu", credits=3)
    sec_python = ClassSection(course=python, lecturer=lecturer, semester="2026-1", room="A101")
    sec_db = ClassSection(course=database, lecturer=lecturer, semester="2026-1", room="B201")
    sv01 = Student(username="sv01", password="sv123", full_name="SV 1", email="s1@x.vn", student_code="SV001")
    sv02 = Student(username="sv02", password="sv123", full_name="SV 2", email="s2@x.vn", student_code="SV002")

    def session(section, days, start=time(7, 0), end=time(9, 30)):
        return ClassSession(section=section, session_date=TODAY + timedelta(days=days), start_time=start, end_time=end)

    past = session(sec_python, -7)
    soon = session(sec_python, 3)
    later = session(sec_python, 10)
    other_class = session(sec_db, 4, time(13, 0), time(15, 30))
    db.session.add_all([
        lecturer, python, database, sec_python, sec_db, sv01, sv02, past, soon, later, other_class,
        Enrollment(section=sec_python, student=sv01), Enrollment(section=sec_db, student=sv02),
    ])
    db.session.commit()
    return {"sv01": sv01, "sv02": sv02, "past": past, "soon": soon, "later": later, "other_class": other_class}


def submit(world, session_key="soon", reason="Đi khám bệnh.", student_key="sv01"):
    return LeaveService.submit(world[student_key].id, world[session_key].id, reason)


def count_leaves():
    return LeaveRequest.query.count()


def error_code(callable_):
    with pytest.raises(ServiceError) as exc:
        callable_()
    return exc.value.code


# ------------------------------------------------------------------ LeaveService.submit
def test_submit_saves_pending_with_timestamp(world):
    before = datetime.utcnow() - timedelta(seconds=1)
    leave = submit(world, reason="  Đi khám bệnh.  ")
    saved = db.session.get(LeaveRequest, leave.id)
    assert saved.status == LeaveStatus.PENDING
    assert saved.reason == "Đi khám bệnh."  # đã bỏ khoảng trắng hai đầu
    assert saved.student_id == world["sv01"].id and saved.session_id == world["soon"].id
    assert saved.created_at >= before
    assert saved.reviewed_by is None and saved.reviewed_at is None


def test_reason_must_not_be_empty(world):
    assert error_code(lambda: submit(world, reason="")) == VALIDATION_ERROR
    assert error_code(lambda: submit(world, reason="   ")) == VALIDATION_ERROR
    assert error_code(lambda: submit(world, reason=None)) == VALIDATION_ERROR
    assert count_leaves() == 0


def test_reason_length_limit(world):
    assert error_code(lambda: submit(world, reason="a" * 256)) == VALIDATION_ERROR
    assert count_leaves() == 0
    submit(world, reason="a" * 255)  # đúng giới hạn thì được
    assert count_leaves() == 1


def test_session_must_belong_to_students_class(world):
    assert error_code(lambda: submit(world, "other_class")) == LEAVE_NOT_IN_CLASS  # lớp sv01 không học
    assert error_code(lambda: LeaveService.submit(world["sv01"].id, 9999, "x")) == LEAVE_NOT_IN_CLASS
    assert count_leaves() == 0


def test_unknown_student(world):
    assert error_code(lambda: LeaveService.submit(9999, world["soon"].id, "x")) == NOT_FOUND


def test_pending_request_blocks_second_one(world):
    submit(world)
    assert error_code(lambda: submit(world, reason="Gửi lại")) == LEAVE_DUPLICATE
    assert count_leaves() == 1
    submit(world, "later")  # buổi khác thì vẫn gửi được
    assert count_leaves() == 2


def test_other_student_can_request_same_session_in_own_class(world):
    sv02_leave = LeaveService.submit(world["sv02"].id, world["other_class"].id, "Việc gia đình.")
    assert sv02_leave.student_id == world["sv02"].id


@pytest.mark.parametrize("status, word", [(LeaveStatus.APPROVED, "duyệt"), (LeaveStatus.REJECTED, "từ chối")])
def test_decided_request_also_reported_as_duplicate(world, status, word):
    # UNIQUE (student_id, session_id) theo ERD: đơn đã xử lý không đổi được (BR8) và không gửi lại được
    leave = submit(world)
    leave.status = status
    db.session.commit()
    with pytest.raises(ServiceError) as exc:
        submit(world, reason="Gửi lại")
    assert exc.value.code == LEAVE_DUPLICATE and word in exc.value.message
    assert count_leaves() == 1


def test_student_submit_leave_request_method(world):
    leave = world["sv01"].submit_leave_request(world["soon"].id, "Có việc đột xuất.")
    assert leave.status == LeaveStatus.PENDING and leave.student_id == world["sv01"].id


# ------------------------------------------------------------------ dữ liệu cho M06
def test_upcoming_sessions_only_future_of_own_classes(world):
    items = LeaveService.list_upcoming_sessions(world["sv01"].id)
    assert [i["session_id"] for i in items] == [world["soon"].id, world["later"].id]  # không có buổi đã qua, buổi lớp khác
    expected_date = (TODAY + timedelta(days=3)).strftime("%d/%m/%Y")
    assert items[0]["label"] == f"INT1001 - Lập trình Python · {expected_date} 07:00-09:30"
    assert [i["session_id"] for i in LeaveService.list_upcoming_sessions(world["sv02"].id)] == [world["other_class"].id]


def test_upcoming_sessions_include_today(world):
    today_session = ClassSession(section=world["soon"].section, session_date=TODAY,
                                 start_time=time(23, 0), end_time=time(23, 30))
    db.session.add(today_session)
    db.session.commit()
    ids = [i["session_id"] for i in LeaveService.list_upcoming_sessions(world["sv01"].id)]
    assert ids[0] == today_session.id


def test_requests_for_student_newest_first_with_status(world):
    first = submit(world, "soon", "Lý do 1")
    first.created_at = datetime.utcnow() - timedelta(hours=1)
    first.status = LeaveStatus.APPROVED
    db.session.commit()
    second = submit(world, "later", "Lý do 2")
    LeaveService.submit(world["sv02"].id, world["other_class"].id, "của sv02")

    items = LeaveService.requests_for_student(world["sv01"].id)
    assert [i["id"] for i in items] == [second.id, first.id]
    assert [i["status"] for i in items] == ["PENDING", "APPROVED"]
    assert items[0]["reason"] == "Lý do 2" and items[0]["created_at"] is not None
    assert "INT1001" in items[0]["session_label"]
    assert LeaveService.requests_for_student(9999) == []


# ------------------------------------------------------------------ route M06
def login(client, username="sv01", password="sv123"):
    return client.post("/login", data={"username": username, "password": password})


def rendered(app):
    captured = []

    def record(_sender, template, context, **_extra):
        captured.append((template.name, context))

    template_rendered.connect(record, app, weak=False)  # weak=False: không để blinker thu hồi hàm cục bộ
    return captured


def test_get_passes_contract_data(app, world):
    submit(world)
    client = app.test_client()
    login(client)
    captured = rendered(app)
    assert client.get("/student/leave").status_code == 200
    name, ctx = captured[-1]
    assert name == "student/leave.html"
    assert [s["session_id"] for s in ctx["upcoming_sessions"]] == [world["soon"].id, world["later"].id]
    assert [r["status"] for r in ctx["my_requests"]] == ["PENDING"]
    assert ctx["error_code"] is None and ctx["error_message"] is None


def test_post_success_redirects_and_saves(app, world):
    client = app.test_client()
    login(client)
    response = client.post("/student/leave", data={"session_id": world["soon"].id, "reason": "Đi khám bệnh."})
    assert response.status_code == 302 and response.headers["Location"].endswith("/student/leave")
    db.session.expire_all()
    (leave,) = LeaveRequest.query.all()
    assert leave.status == LeaveStatus.PENDING and leave.student_id == world["sv01"].id


def test_post_errors_show_page_again_with_code(app, world):
    client = app.test_client()
    login(client)
    captured = rendered(app)

    missing_reason = client.post("/student/leave", data={"session_id": world["soon"].id, "reason": "  "})
    assert missing_reason.status_code == 400
    ctx = captured[-1][1]
    assert ctx["error_code"] == VALIDATION_ERROR and ctx["error_message"]
    assert ctx["form"]["session_id"] == str(world["soon"].id)  # giữ lại nội dung đã chọn

    no_session = client.post("/student/leave", data={"reason": "x"})
    assert no_session.status_code == 400 and captured[-1][1]["error_code"] == VALIDATION_ERROR

    wrong_class = client.post("/student/leave", data={"session_id": world["other_class"].id, "reason": "x"})
    assert wrong_class.status_code == 400 and captured[-1][1]["error_code"] == LEAVE_NOT_IN_CLASS

    assert client.post("/student/leave", data={"session_id": world["soon"].id, "reason": "ok"}).status_code == 302
    duplicate = client.post("/student/leave", data={"session_id": world["soon"].id, "reason": "ok"})
    assert duplicate.status_code == 409 and captured[-1][1]["error_code"] == LEAVE_DUPLICATE
    db.session.expire_all()
    assert count_leaves() == 1


def test_leave_page_requires_student_role(app, world):
    anonymous = app.test_client()
    assert "/login" in anonymous.get("/student/leave").headers["Location"]
    client = app.test_client()
    login(client, "gv01", "gv123")
    assert client.get("/student/leave").status_code == 403
    assert client.post("/student/leave", data={"session_id": world["soon"].id, "reason": "x"}).status_code == 403
