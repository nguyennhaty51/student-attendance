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

CODE_PATTERN = re.compile(r"[0-9]{6}")  # chá»‰ chá»¯ sá»‘ ASCII, Ä‘Ãºng 6 kÃ½ tá»±


class CheckInThrottle:
    """Äáº¿m sá»‘ láº§n nháº­p sai liÃªn tiáº¿p theo tá»«ng sinh viÃªn, quÃ¡ ngÆ°á»¡ng thÃ¬ táº¡m khÃ³a (NFR11).

    LÆ°u trong bá»™ nhá»› tiáº¿n trÃ¬nh: Ä‘á»§ cho cháº¡y 1 tiáº¿n trÃ¬nh (flask run / 1 worker).
    Náº¿u triá»ƒn khai nhiá»u worker thÃ¬ chuyá»ƒn sang lÆ°u DB hoáº·c Redis, giá»¯ nguyÃªn cÃ¡c hÃ m bÃªn dÆ°á»›i.
    """

    def __init__(self, max_failures: int = MAX_FAILED_ATTEMPTS, lock_seconds: int = LOCK_SECONDS):
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self._failures: dict = {}
        self._locked_until: dict = {}
        self._mutex = threading.Lock()

    def seconds_locked(self, key) -> int:
        """Sá»‘ giÃ¢y cÃ²n bá»‹ khÃ³a (0 náº¿u khÃ´ng bá»‹ khÃ³a)."""
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
        # NFR11: Ä‘ang bá»‹ khÃ³a thÃ¬ khÃ´ng xá»­ lÃ½, khÃ´ng Ä‘á»ƒ dÃ² mÃ£ tiáº¿p
        if self.throttle.seconds_locked(student.id):
            return CheckInResult.TOO_MANY_ATTEMPTS

        code = (code or "").strip()
        session = self.repo.find_session_by_code(code) if CODE_PATTERN.fullmatch(code) else None

        # MÃ£ sai (hoáº·c phiÃªn Ä‘Ã£ Ä‘Ã³ng nÃªn mÃ£ Ä‘Ã£ bá»‹ xÃ³a)
        if session is None:
            self.throttle.register_failure(student.id)
            return CheckInResult.WRONG_CODE

        # MÃ£ Ä‘Ãºng nhÆ°ng Ä‘Ã£ háº¿t háº¡n
        if not session.is_code_valid():
            return CheckInResult.EXPIRED

              # QT3: sinh viÃªn pháº£i thuá»™c lá»›p cá»§a buá»•i há»c
        if not self.repo.is_student_in_section(student.id, session.section_id):
            return CheckInResult.NOT_IN_CLASS

        # QT1: má»—i buá»•i chá»‰ Ä‘iá»ƒm danh má»™t láº§n
        if self.repo.has_attendance(student.id, session.id):
            return CheckInResult.ALREADY_CHECKED_IN

        try:
            self.repo.add_present(student.id, session.id, utcnow())
            self.repo.commit()
        except IntegrityError:
            # Hai yÃªu cáº§u cÃ¹ng lÃºc: unique (student_id, class_session_id) cháº·n báº£n ghi thá»© hai
            self.repo.rollback()
            return CheckInResult.ALREADY_CHECKED_IN

        self.throttle.reset(student.id)
        self._after_check_in(student, session)
        return CheckInResult.SUCCESS

    def _after_check_in(self, student, session) -> None:
        """Kiá»ƒm tra ngÆ°á»¡ng váº¯ng sau khi Ä‘iá»ƒm danh."""
        try:
            from app.services.absence_service import check_absence_threshold
        except ImportError:
            return

        try:
            check_absence_threshold(student.id, session.section_id)
        except Exception:
            logger.exception(
                "Kiá»ƒm tra ngÆ°á»¡ng váº¯ng tháº¥t báº¡i (student=%s, section=%s)",
                student.id,
                session.section_id,
            )


check_in_service = CheckInService()
