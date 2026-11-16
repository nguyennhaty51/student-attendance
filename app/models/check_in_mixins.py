import secrets
from datetime import timedelta

from app.services.check_in_common import CODE_LENGTH, DEFAULT_CODE_MINUTES, utcnow


class ClassSessionCheckInMixin:
    """UC6 – mã điểm danh của một buổi học."""

    @property
    def is_open(self) -> bool:
        """Phiên đang mở khi buổi học còn giữ mã (đóng phiên = mã về rỗng)."""
        return bool(self.check_in_code)

    def generate_code(self, minutes: int = DEFAULT_CODE_MINUTES) -> str:
        """Sinh PIN 6 chữ số ngẫu nhiên bằng secrets, lưu check_in_code và code_expiry."""
        if minutes <= 0:
            raise ValueError("minutes phải lớn hơn 0")
        code = f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"
        self.check_in_code = code
        self.code_expiry = utcnow() + timedelta(minutes=minutes)
        return code

    def is_code_valid(self) -> bool:
        """Mã còn tồn tại và chưa quá hạn."""
        return (
            bool(self.check_in_code)
            and self.code_expiry is not None
            and utcnow() < self.code_expiry
        )

    def close_code(self) -> None:
        """Đóng phiên: đặt mã và hạn về rỗng."""
        self.check_in_code = None
        self.code_expiry = None


class LecturerCheckInMixin:
    """UC6 – giảng viên mở/đóng phiên điểm danh."""

    def open_check_in_session(self, session_id, minutes=DEFAULT_CODE_MINUTES, qr_payload_factory=None) -> dict:
        from app.services.qr_session_service import qr_session_service
        return qr_session_service.open_session(self, session_id, minutes, qr_payload_factory)

    def close_check_in_session(self, session_id) -> dict:
        from app.services.qr_session_service import qr_session_service
        return qr_session_service.close_session(self, session_id)


class StudentCheckInMixin:
    """UC3 – sinh viên điểm danh bằng mã."""

    def check_in(self, code: str):
        """Trả về CheckInResult."""
        from app.services.check_in_service import check_in_service
        return check_in_service.check_in(self, code)
