import base64
import io
from typing import Callable, Optional

import qrcode

from app.repositories.attendance_repository import AttendanceRepository
from app.services.check_in_common import (
    DEFAULT_CODE_MINUTES,
    NotSessionLecturerError,
    SessionNotFoundError,
)

MAX_UNIQUE_TRIES = 20

# Nhận PIN, trả nội dung cần mã hóa vào QR (ví dụ URL trang điểm danh kèm ?code=PIN)
QrPayloadFactory = Callable[[str], str]


def make_qr_base64(payload: str) -> str:
    """Sinh ảnh QR (PNG) và trả về chuỗi base64 (chưa kèm tiền tố data:)."""
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class QrSessionService:
    def __init__(self, repo: Optional[AttendanceRepository] = None):
        self.repo = repo or AttendanceRepository()

    # ---------- API cho Lecturer / route ----------
    def open_session(self, lecturer, session_id, minutes=DEFAULT_CODE_MINUTES,
                     qr_payload_factory: Optional[QrPayloadFactory] = None) -> dict:
        """Mở phiên. Nếu buổi học đã có phiên đang mở thì trả lại mã hiện tại, không tạo mã mới."""
        session = self._get_owned_session(lecturer, session_id)
        already_open = session.is_open
        if not already_open:
            self._assign_unique_code(session, minutes)
            self.repo.commit()
        state = self._build_state(session, qr_payload_factory)
        state["already_open"] = already_open
        return state

    def close_session(self, lecturer, session_id) -> dict:
        """Đóng phiên (mã về rỗng). Gọi lại khi đã đóng thì không có tác dụng gì thêm."""
        session = self._get_owned_session(lecturer, session_id)
        if session.is_open:
            session.close_code()
            self.repo.commit()
        return self._build_state(session)

    def get_state(self, lecturer, session_id, qr_payload_factory: Optional[QrPayloadFactory] = None) -> dict:
        """Dữ liệu cho màn hình M10: PIN, ảnh QR, hạn mã, số đã điểm danh / tổng."""
        session = self._get_owned_session(lecturer, session_id)
        return self._build_state(session, qr_payload_factory)

    def get_counts(self, lecturer, session_id) -> dict:
        """Endpoint JSON nhẹ để M10 tự làm mới số đã điểm danh (không sinh lại QR)."""
        session = self._get_owned_session(lecturer, session_id)
        return {
            "session_id": session.id,
            "is_open": session.is_open,
            "is_expired": session.is_open and not session.is_code_valid(),
            "attended": self.repo.count_present(session.id),
            "total": self.repo.count_students(session.class_section_id),
        }

    # ---------- nội bộ ----------
    def _get_owned_session(self, lecturer, session_id):
        session = self.repo.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        if self.repo.get_section_lecturer_id(session.class_section_id) != lecturer.id:  # QT4
            raise NotSessionLecturerError(session_id)
        return session

    def _assign_unique_code(self, session, minutes) -> None:
        """Sinh PIN không trùng với phiên đang mở nào khác (vì sinh viên chỉ nhập mã, không chọn lớp)."""
        for _ in range(MAX_UNIQUE_TRIES):
            code = session.generate_code(minutes)
            if not self.repo.code_in_use(code, exclude_session_id=session.id):
                return
        session.close_code()
        raise RuntimeError("Không sinh được mã điểm danh duy nhất, vui lòng thử lại")

    def _build_state(self, session, qr_payload_factory: Optional[QrPayloadFactory] = None) -> dict:
        is_open = session.is_open
        expiry = session.code_expiry if is_open else None
        qr_base64 = None
        if is_open:
            payload = qr_payload_factory(session.check_in_code) if qr_payload_factory else session.check_in_code
            qr_base64 = make_qr_base64(payload)
        return {
            "session_id": session.id,
            "is_open": is_open,
            "is_expired": is_open and not session.is_code_valid(),
            "pin": session.check_in_code if is_open else None,
            "qr_base64": qr_base64,                                   # <img src="data:image/png;base64,{{ qr_base64 }}">
            "expires_at": expiry.isoformat() + "Z" if expiry else None,  # UTC
            "attended": self.repo.count_present(session.id),
            "total": self.repo.count_students(session.class_section_id),
        }


qr_session_service = QrSessionService()
