from app.errors import REASON_REQUIRED, VALIDATION_ERROR, ServiceError
from app.models.enums import AttendanceStatus as S
from app.services import attendance_common as common


def code_of(call, *args, **kwargs):
    """Gọi hàm, trả về mã lỗi ServiceError (hoặc None nếu không lỗi)."""
    try:
        call(*args, **kwargs)
    except ServiceError as exc:
        return exc.code
    return None


def test_parse_status_accepts_enum_and_names():
    assert common.parse_status(S.LATE) is S.LATE
    assert common.parse_status("present") is S.PRESENT
    assert common.parse_status("  Excused ") is S.EXCUSED


def test_parse_status_rejects_other_values():
    for bad in ("SICK", "", None, 3, "Có mặt"):
        assert code_of(common.parse_status, bad) == VALIDATION_ERROR


def test_require_reason_qt6():
    assert common.require_reason("  nhập nhầm  ") == "nhập nhầm"
    for blank in (None, "", "   ", "\n\t"):
        assert code_of(common.require_reason, blank) == REASON_REQUIRED
    assert code_of(common.require_reason, "x" * 255) is None
    assert code_of(common.require_reason, "x" * 256) == VALIDATION_ERROR


def test_to_positive_int():
    assert common.to_positive_int("12", "id") == 12
    assert common.to_positive_int(7, "id") == 7
    for bad in (0, -1, "abc", "1.5", None, True, 2.0):
        assert code_of(common.to_positive_int, bad, "id") == VALIDATION_ERROR
