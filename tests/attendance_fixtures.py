from datetime import date, time as dtime
from types import SimpleNamespace

import pytest
from jinja2 import ChoiceLoader, DictLoader

from app import create_app
from app.errors import ServiceError
from app.extensions import db
from app.models import (
    Attendance, CheckInMethod, AttendanceStatus as S, ClassSection, ClassSession, Course, Enrollment, Lecturer,
    Student,
)
from config import TestConfig

# Template M09 thật do TV5 làm; ở đây dùng bản giả chỉ in các biến hợp đồng để kiểm tra controller.
M09_STUB = (
    "{{ session.course_name }}|{{ session.id }}|has_saved={{ has_saved }}|err={{ error_code }}|"
    "{% for s in students %}{{ s.student_code }}={{ s.status.value if s.status else '-' }}"
    "/{{ s.note }}/{{ s.reason }};{% endfor %}"
)


def make_student(i, **extra):
    return Student(username=f"sv{i:03d}", password_hash="x", full_name=f"Sinh viên {i}",
                   email=f"sv{i:03d}@school.edu.vn", student_code=f"SV{i:03d}", **extra)


@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.jinja_env.loader = ChoiceLoader([DictLoader({"lecturer/attendance.html": M09_STUB}), app.jinja_env.loader])
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def world(app):
    "gv1 phụ trách `section` (SV 1-3 đã đăng ký, SV 4 không); gv2 phụ trách lớp khác."
    gv1 = Lecturer(username="gv01", password="gv123", full_name="GV 1", email="gv01@x.vn", lecturer_code="GV001")
    gv2 = Lecturer(username="gv02", password="gv123", full_name="GV 2", email="gv02@x.vn", lecturer_code="GV002")
    students = [make_student(i) for i in range(1, 5)]
    course = Course(code="INT1001", name="Lập trình Python", credits=3)
    db.session.add_all([gv1, gv2, course, *students])
    db.session.flush()

    section = ClassSection(course_id=course.id, lecturer_id=gv1.id, semester="2026-1", room="A101")
    other_section = ClassSection(course_id=course.id, lecturer_id=gv2.id, semester="2026-1", room="B201")
    db.session.add_all([section, other_section])
    db.session.flush()
    db.session.add_all(Enrollment(section_id=section.id, student_id=s.id) for s in students[:3])
    session = ClassSession(section_id=section.id, session_date=date(2026, 11, 2),
                           start_time=dtime(7, 0), end_time=dtime(9, 30))
    other_session = ClassSession(section_id=other_section.id, session_date=date(2026, 11, 3),
                                 start_time=dtime(7, 0), end_time=dtime(9, 30))
    db.session.add_all([session, other_session])
    db.session.commit()
    return SimpleNamespace(
        gv1=gv1.id, gv2=gv2.id, section=section.id, session=session.id, other_session=other_session.id,
        students=[s.id for s in students[:3]], outsider=students[3].id)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password="gv123"):
    return client.post("/login", data={"username": username, "password": password})


def url(world):
    return f"/lecturer/sessions/{world.session}/attendance"


def add_attendance(world, student_id, status=S.PRESENT, method=CheckInMethod.MANUAL, note=None):
    attendance = Attendance(session_id=world.session, student_id=student_id, status=status, method=method, note=note)
    db.session.add(attendance)
    db.session.commit()
    return attendance.id


def saved(world, student_id):
    db.session.expire_all()
    return Attendance.query.filter_by(session_id=world.session, student_id=student_id).one_or_none()


def fails_with(code, call, *args, **kwargs):
    with pytest.raises(ServiceError) as info:
        call(*args, **kwargs)
    assert info.value.code == code
    return info.value
