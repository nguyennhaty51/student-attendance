import pytest

from app.errors import REASON_REQUIRED, VALIDATION_ERROR, ServiceError
from app.models.enums import AttendanceStatus as S
from app.services import uc5_manual_attendance as uc5


def code_of(call, *args, **kwargs):
    try:
        call(*args, **kwargs)
    except ServiceError as exc:
        return exc.code
    return None


def test_clean_note():
    assert uc5.clean_note(None) is None
    assert uc5.clean_note("   ") is None
    assert uc5.clean_note("  đến trễ  ") == "đến trễ"
    assert uc5.clean_note("x" * 255) == "x" * 255
    assert code_of(uc5.clean_note, "x" * 256) == VALIDATION_ERROR
    assert code_of(uc5.clean_note, 5) == VALIDATION_ERROR


# ----------------------------------------------------------------------------- normalize_records
def test_normalize_records_ok():
    entries = uc5.normalize_records([
        {"student_id": "5", "status": "absent", "note": " ốm ", "reason": " r "},
        {"student_id": 6, "status": S.PRESENT},
    ])
    assert [e.student_id for e in entries] == [5, 6]
    assert entries[0].status is S.ABSENT and entries[0].note == "ốm" and entries[0].reason == "r"
    assert entries[1].note is uc5.KEEP_NOTE and entries[1].reason is None  # không truyền note → giữ nguyên


def test_normalize_records_rejects_bad_shape():
    bad_inputs = [
        None, [], "abc", {},
        [{"status": "PRESENT"}],                       # thiếu student_id
        [{"student_id": 1}],                           # thiếu status
        ["không phải dict"],
        [{"student_id": 1, "status": "SICK"}],         # trạng thái sai
        [{"student_id": 1, "status": "PRESENT", "note": "x" * 300}],
        [{"student_id": 1, "status": "PRESENT", "reason": "x" * 300}],
        [{"student_id": 1, "status": "PRESENT"}, {"student_id": "1", "status": "ABSENT"}],  # trùng sinh viên
    ]
    for bad in bad_inputs:
        assert code_of(uc5.normalize_records, bad) == VALIDATION_ERROR, bad


# ----------------------------------------------------------------------------- plan_changes
def entries(*rows):
    return uc5.normalize_records([dict(zip(("student_id", "status", "note", "reason"), r)) for r in rows])


def actions(plan):
    return [(p.entry.student_id, p.action) for p in plan]


def test_plan_create_for_students_without_record():
    plan = uc5.plan_changes({}, entries((1, "PRESENT", "", None), (2, "ABSENT", "ốm", None)))
    assert actions(plan) == [(1, uc5.ACTION_CREATE), (2, uc5.ACTION_CREATE)]


def test_plan_change_status_needs_reason():
    existing = {1: (S.PRESENT, None)}
    assert code_of(uc5.plan_changes, existing, entries((1, "ABSENT", "", None))) == REASON_REQUIRED
    assert code_of(uc5.plan_changes, existing, entries((1, "ABSENT", "", "   "))) == REASON_REQUIRED
    plan = uc5.plan_changes(existing, entries((1, "ABSENT", "", "nhập nhầm")))
    assert actions(plan) == [(1, uc5.ACTION_CHANGE_STATUS)]
    assert plan[0].old_status is S.PRESENT


def test_plan_reports_all_missing_reasons_once():
    existing = {1: (S.PRESENT, None), 2: (S.PRESENT, None), 3: (S.PRESENT, None)}
    with pytest.raises(ServiceError) as info:
        uc5.plan_changes(existing, entries((1, "ABSENT", "", None), (2, "LATE", "", ""), (3, "PRESENT", "", None)))
    assert info.value.code == REASON_REQUIRED
    assert "2 sinh viên" in info.value.message


def test_plan_note_only_and_unchanged_need_no_reason():
    existing = {1: (S.PRESENT, None), 2: (S.LATE, "trễ 10 phút")}
    plan = uc5.plan_changes(existing, entries((1, "PRESENT", "mới ghi chú", None), (2, "LATE", "trễ 10 phút", None)))
    assert actions(plan) == [(1, uc5.ACTION_UPDATE_NOTE), (2, uc5.ACTION_UNCHANGED)]


def test_plan_missing_note_keeps_existing_note():
    existing = {1: (S.LATE, "trễ 10 phút")}
    only_status = uc5.normalize_records([{"student_id": 1, "status": "LATE"}])
    assert actions(uc5.plan_changes(existing, only_status)) == [(1, uc5.ACTION_UNCHANGED)]


def test_plan_empty_note_clears_note():
    existing = {1: (S.LATE, "trễ 10 phút")}
    plan = uc5.plan_changes(existing, entries((1, "LATE", "", None)))
    assert actions(plan) == [(1, uc5.ACTION_UPDATE_NOTE)]


# ----------------------------------------------------------------------------- parse_attendance_form
def test_parse_form_reads_three_fields_per_student():
    form = {
        "csrf_token": "x",
        "status[11]": "PRESENT", "note[11]": "", "reason[11]": "",
        "status[12]": "ABSENT", "note[12]": "ốm", "reason[12]": "nhập nhầm",
    }
    assert uc5.parse_attendance_form(form) == [
        {"student_id": 11, "status": "PRESENT", "note": "", "reason": ""},
        {"student_id": 12, "status": "ABSENT", "note": "ốm", "reason": "nhập nhầm"},
    ]


def test_parse_form_skips_untouched_rows():
    form = {"status[1]": "PRESENT", "note[1]": "", "note[2]": "", "reason[2]": "  "}  # SV 2 chưa chọn, không nhập gì
    assert [r["student_id"] for r in uc5.parse_attendance_form(form)] == [1]


def test_parse_form_rejects_note_without_status():
    assert code_of(uc5.parse_attendance_form, {"note[2]": "ghi chú lạc"}) == VALIDATION_ERROR
    assert code_of(uc5.parse_attendance_form, {"status[2]": "", "reason[2]": "lý do lạc"}) == VALIDATION_ERROR


def test_parse_form_ignores_unrelated_keys():
    assert uc5.parse_attendance_form({"csrf_token": "x", "status[abc]": "PRESENT", "other": "1"}) == []
