import logging
import math
import re
import threading
import time
from typing import Optional

from sqlalchemy.exc import IntegrityError

from app.repositories.attendance_repository import AttendanceRepository
from app.services.check_in_common import (
    LOCK_SECONDS,
    MAX_FAILED_ATTEMPTS,
    CheckInResult,
    utcnow,
)

logger = logging.getLogger(__name__)

CODE_PATTERN = re.compile(r"[0-9]{6}")  # chỉ chữ số ASCII, đúng 6 ký tự


class CheckInThrottle:
    """Đếm số lần nhập sai liên tiếp theo từng sinh viên, quá ngưỡng thì tạm khóa (NFR11).

    Lưu trong bộ nhớ tiến trình: đủ cho chạy 1 tiến trình (flask run / 1 worker).
    Nếu triển khai nhiều worker thì chuyển sang lưu DB hoặc Redis, giữ nguyên các hàm bên dưới.
    """

    def __init__(self, max_failures: int = MAX_FAILED_ATTEMPTS, lock_seconds: int = LOCK_SECONDS):
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self._failures: dict = {}
        self._locked_until: dict = {}
        self._mutex = threading.Lock()

    def seconds_locked(self, key) -> int:
        """Số giây còn bị khóa (0 nếu không bị khóa)."""
        with self._mutex:
            until = self._locked_until.get(key)
            if until is None:
                return 0
            remaining = until - time.monotonic()
            if remaining <= 0:
                self._locked_until.pop(key, None)
                self._failures.pop(key, None)
                return 0
            return math.ceil(remaining)

    def register_failure(self, key) -> None:
        with self._mutex:
            count = self._failures.get(key, 0) + 1
            if count >= self.max_failures:
                self._locked_until[key] = time.monotonic() + self.lock_seconds
                self._failures.pop(key, None)
            else:
                self._failures[key] = count

    def reset(self, key) -> None:
        with self._mutex:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)


class CheckInService:
    def __init__(self, repo: Optional[AttendanceRepository] = None, throttle: Optional[CheckInThrottle] = None):
        self.repo = repo or AttendanceRepository()
        self.throttle = throttle or CheckInThrottle()

    def lock_seconds_left(self, student_id) -> int:
        return self.throttle.seconds_locked(student_id)

    def check_in(self, student, code) -> CheckInResult:
        # NFR11: đang bị khóa thì không xử lý, không để dò mã tiếp
        if self.throttle.seconds_locked(student.id):
            return CheckInResult.TOO_MANY_ATTEMPTS

        code = (code or "").strip()
        session = self.repo.find_session_by_code(code) if CODE_PATTERN.fullmatch(code) else None

        # Mã sai (hoặc phiên đã đóng nên mã đã bị xóa)
        if session is None:
            self.throttle.register_failure(student.id)
            return CheckInResult.WRONG_CODE

        # Mã đúng nhưng đã hết hạn
        if not session.is_code_valid():
            return CheckInResult.EXPIRED

        # QT3: sinh viên phải thuộc lớp của buổi học
        if not self.repo.is_student_in_section(student.id, session.class_section_id):
            self.throttle.register_failure(student.id)
            return CheckInResult.NOT_IN_CLASS

        # QT1: mỗi buổi chỉ điểm danh một lần
        if self.repo.has_attendance(student.id, session.id):
            return CheckInResult.ALREADY_CHECKED_IN

        try:
            self.repo.add_present(student.id, session.id, utcnow())
            self.repo.commit()
        except IntegrityError:
            # Hai yêu cầu cùng lúc: unique (student_id, class_session_id) chặn bản ghi thứ hai
            self.repo.rollback()
            return CheckInResult.ALREADY_CHECKED_IN

        self.throttle.reset(student.id)
        self._after_check_in(student, session)
        return CheckInResult.SUCCESS

    def _after_check_in(self, student, session) -> None:
        """Sau khi ghi nhận, gọi kiểm tra ngưỡng vắng (TV2-3). Lỗi ở đây không được làm hỏng điểm danh."""
        try:
            from app.services.absence_service import check_absence_threshold  # TV2-3
        except ImportError:
            return  # TV2-3 chưa được merge
        try:
            check_absence_threshold(student.id, session.class_section_id)
        except Exception:
            logger.exception("Kiểm tra ngưỡng vắng thất bại (student=%s, class=%s)", student.id, session.class_section_id)


check_in_service = CheckInService()
