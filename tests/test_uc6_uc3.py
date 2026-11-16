import base64
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

from app.services.check_in_common import (
    DEFAULT_CODE_MINUTES,
    NotSessionLecturerError,
    SessionNotFoundError,
)
from app.services.qr_session_service import QrSessionService, make_qr_base64


class FakeSession:
    def __init__(self, session_id=10, class_section_id=100):
        self.id = session_id
        self.class_section_id = class_section_id
        self.check_in_code = None
        self.code_expiry = None
        self._valid = True

    @property
    def is_open(self) -> bool:
        return bool(self.check_in_code)

    def generate_code(self, minutes=DEFAULT_CODE_MINUTES) -> str:
        self.check_in_code = "482910"
        self.code_expiry = datetime.utcnow() + timedelta(minutes=minutes)
        self._valid = True
        return self.check_in_code

    def close_code(self) -> None:
        self.check_in_code = None
        self.code_expiry = None

    def is_code_valid(self) -> bool:
        return self.is_open and self._valid


@pytest.fixture
def setup_service():
    repo = MagicMock()
    session = FakeSession(session_id=10, class_section_id=100)
    lecturer = MagicMock(id=1)

    repo.get_session.return_value = session
    repo.get_section_lecturer_id.return_value = 1
    repo.code_in_use.return_value = False
    repo.count_present.return_value = 15
    repo.count_students.return_value = 40

    service = QrSessionService(repo=repo)
    return service, repo, session, lecturer


def test_make_qr_base64_returns_valid_png():
    b64 = make_qr_base64("http://localhost:5000/student/check-in?code=123456")
    raw_bytes = base64.b64decode(b64)
    assert raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_open_session_success(setup_service):
    service, repo, session, lecturer = setup_service

    result = service.open_session(
        lecturer,
        session_id=10,
        qr_payload_factory=lambda pin: f"https://app.local/checkin?code={pin}",
    )

    assert result["session_id"] == 10
    assert result["is_open"] is True
    assert result["already_open"] is False
    assert result["pin"] == "482910"
    assert result["qr_base64"] is not None
    assert result["attended"] == 15
    assert result["total"] == 40
    repo.commit.assert_called_once()


def test_open_session_when_already_open_keeps_existing_pin(setup_service):
    service, repo, session, lecturer = setup_service
    session.check_in_code = "999888"
    session.code_expiry = datetime.utcnow() + timedelta(minutes=3)

    result = service.open_session(lecturer, session_id=10)

    assert result["already_open"] is True
    assert result["pin"] == "999888"
    repo.commit.assert_not_called()


def test_open_session_wrong_lecturer_raises_error(setup_service):
    service, repo, session, lecturer = setup_service
    repo.get_section_lecturer_id.return_value = 999

    with pytest.raises(NotSessionLecturerError):
        service.open_session(lecturer, session_id=10)


def test_open_session_not_found_raises_error(setup_service):
    service, repo, session, lecturer = setup_service
    repo.get_session.return_value = None

    with pytest.raises(SessionNotFoundError):
        service.open_session(lecturer, session_id=999)


def test_close_session_clears_pin(setup_service):
    service, repo, session, lecturer = setup_service
    session.generate_code(5)

    result = service.close_session(lecturer, session_id=10)

    assert result["is_open"] is False
    assert result["pin"] is None
    assert result["qr_base64"] is None
    repo.commit.assert_called_once()


def test_get_counts_returns_live_attendance(setup_service):
    service, repo, session, lecturer = setup_service
    session.generate_code(5)

    counts = service.get_counts(lecturer, session_id=10)

    assert counts == {
        "session_id": 10,
        "is_open": True,
        "is_expired": False,
        "attended": 15,
        "total": 40,
    }