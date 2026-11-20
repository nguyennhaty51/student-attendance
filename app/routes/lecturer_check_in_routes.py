from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest, Forbidden, NotFound
from werkzeug.routing import BuildError

from app.services.check_in_common import (
    DEFAULT_CODE_MINUTES,
    MAX_CODE_MINUTES,
    NotSessionLecturerError,
    SessionNotFoundError,
)
from app.services.qr_session_service import qr_session_service

TEMPLATE_M10 = "lecturer/check_in_session.html"  # M10 do TV4/TV5 làm: đổi tên cho khớp

bp = Blueprint("lecturer_check_in", __name__, url_prefix="/lecturer/sessions")


@bp.errorhandler(SessionNotFoundError)
def _session_not_found(_error):
    return NotFound()


@bp.errorhandler(NotSessionLecturerError)  # QT4: giảng viên lớp khác
def _not_session_lecturer(_error):
    return Forbidden()


def _current_lecturer():
    from app.models import Lecturer  # import trong hàm để tránh vòng lặp import
    user = current_user._get_current_object()
    if not isinstance(user, Lecturer):
        raise Forbidden()
    return user


def _qr_payload(code: str) -> str:
    """QR chứa link trang điểm danh kèm sẵn mã; chưa có route sinh viên thì QR chứa chính PIN."""
    try:
        return url_for("student_check_in.check_in_page", code=code, _external=True)
    except BuildError:
        return code


@bp.get("/<int:session_id>/check-in")
@login_required
def view(session_id):
    """M10: PIN, ảnh QR, thời điểm hết hạn, số đã điểm danh / tổng."""
    state = qr_session_service.get_state(_current_lecturer(), session_id, _qr_payload)
    return render_template(TEMPLATE_M10, **state)


@bp.post("/<int:session_id>/check-in/open")
@login_required
def open_session(session_id):
    minutes = request.form.get("minutes", default=DEFAULT_CODE_MINUTES, type=int)
    if minutes is None or not 1 <= minutes <= MAX_CODE_MINUTES:
        raise BadRequest(f"Thời hạn mã phải từ 1 đến {MAX_CODE_MINUTES} phút")
    _current_lecturer().open_check_in_session(session_id, minutes, _qr_payload)
    return redirect(url_for(".view", session_id=session_id))


@bp.post("/<int:session_id>/check-in/close")
@login_required
def close_session(session_id):
    _current_lecturer().close_check_in_session(session_id)
    return redirect(url_for(".view", session_id=session_id))


@bp.get("/<int:session_id>/check-in/count")
@login_required
def count(session_id):
    """JSON cho M10 tự làm mới số đã điểm danh (gọi định kỳ bằng fetch)."""
    return jsonify(qr_session_service.get_counts(_current_lecturer(), session_id))
