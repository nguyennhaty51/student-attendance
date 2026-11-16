"""Kiểm tra nhanh UC1/UC14 và role_required. (Kiểm thử chính thức làm sau, theo Testing Document Template.)"""
import pytest

from app import create_app
from app.extensions import db
from app.models import Admin, Student
from app.models.enums import Role
from app.utils.decorators import role_required
from config import TestConfig


class AuthTestConfig(TestConfig):
    WTF_CSRF_ENABLED = False  # test gửi form không cần csrf_token


@pytest.fixture
def app():
    app = create_app(AuthTestConfig)

    @app.route("/_admin_only")
    @role_required(Role.ADMIN)
    def admin_only():
        return "ok"

    with app.app_context():
        db.create_all()
        db.session.add_all([
            Admin(username="admin", password="admin123", full_name="Admin", email="a@x.vn"),
            Student(username="sv01", password="sv123", full_name="SV 1", email="s1@x.vn",
                    student_code="SV001"),
            Student(username="locked", password="sv123", full_name="Bị khóa", email="s2@x.vn",
                    student_code="SV002", is_active=False),
        ])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def test_login_redirects_by_role(client):
    assert login(client, "sv01", "sv123").headers["Location"] == "/student/home"


def test_wrong_credentials_generic_message(client):
    r1 = login(client, "sv01", "sai")
    r2 = login(client, "khongco", "sv123")
    assert r1.status_code == r2.status_code == 200
    assert "Tên đăng nhập hoặc mật khẩu không chính xác" in r1.get_data(as_text=True)
    assert "Tên đăng nhập hoặc mật khẩu không chính xác" in r2.get_data(as_text=True)


def test_locked_account_reported(client):
    r = login(client, "locked", "sv123")
    assert "bị khóa" in r.get_data(as_text=True)


def test_next_param_only_internal(client):
    ok = client.post("/login?next=/student/history", data={"username": "sv01", "password": "sv123"})
    assert ok.headers["Location"] == "/student/history"


def test_next_param_external_ignored(client):
    r = client.post("/login?next=//evil.com", data={"username": "sv01", "password": "sv123"})
    assert r.headers["Location"] == "/student/home"


def test_logout_ends_session(client):
    login(client, "sv01", "sv123")
    client.post("/logout")
    assert client.get("/change-password").status_code == 302  # bị đưa về /login


def test_role_required_denies_other_role(client):
    login(client, "sv01", "sv123")
    assert client.get("/_admin_only").status_code == 403


def test_role_required_allows_role(client):
    login(client, "admin", "admin123")
    assert client.get("/_admin_only").status_code == 200


def test_change_password_flow(client):
    login(client, "sv01", "sv123")
    bad_old = client.post("/change-password", data={"old_password": "x", "new_password": "abcdef", "confirm_password": "abcdef"})
    assert "Mật khẩu cũ không chính xác" in bad_old.get_data(as_text=True)
    too_short = client.post("/change-password", data={"old_password": "sv123", "new_password": "abc", "confirm_password": "abc"})
    assert "ít nhất 6 ký tự" in too_short.get_data(as_text=True)
    mismatch = client.post("/change-password", data={"old_password": "sv123", "new_password": "abcdef", "confirm_password": "abcdeg"})
    assert "không khớp" in mismatch.get_data(as_text=True)
    ok = client.post("/change-password", data={"old_password": "sv123", "new_password": "abcdef", "confirm_password": "abcdef"})
    assert ok.status_code == 302
    client.post("/logout")
    assert login(client, "sv01", "abcdef").headers["Location"] == "/student/home"