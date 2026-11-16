
import math

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from werkzeug.exceptions import Forbidden

from app.services.check_in_common import CheckInResult
from app.services.check_in_service import check_in_service

TEMPLATE_M04 = "student/check_in.html"  # M04 do TV4/TV5 làm: đổi tên cho khớp

bp = Blueprint("student_check_in", __name__, url_prefix="/student")

MESSAGES = {
    CheckInResult.SUCCESS: "Điểm danh thành công.",
    CheckInResult.WRONG_CODE: "Mã không đúng hoặc phiên điểm danh đã đóng. Vui lòng kiểm tra lại.",
    CheckInResult.EXPIRED: "Mã đã hết hạn. Vui lòng nhờ giảng viên mở lại phiên.",
    CheckInResult.NOT_IN_CLASS: "Bạn không thuộc lớp của buổi học này.",
    CheckInResult.ALREADY_CHECKED_IN: "Bạn đã điểm danh buổi học này rồi.",
    CheckInResult.TOO_MANY_ATTEMPTS: "Bạn nhập sai quá nhiều lần. Vui lòng thử lại sau {minutes} phút.",
}

HTTP_STATUS = {
    CheckInResult.SUCCESS: 200,
    CheckInResult.WRONG_CODE: 400,
    CheckInResult.EXPIRED: 410,
    CheckInResult.NOT_IN_CLASS: 403,
    CheckInResult.ALREADY_CHECKED_IN: 409,
    CheckInResult.TOO_MANY_ATTEMPTS: 429,
}


def _current_student():
    from app.models import Student  # import trong hàm để tránh vòng lặp import
    user = current_user._get_current_object()
    if not isinstance(user, Student):
        raise Forbidden()
    return user


@bp.get("/check-in")
@login_required
def check_in_page():
    """M04: form nhập mã. Quét QR sẽ vào đây với ?code=<PIN> để điền sẵn."""
    _current_student()
    return render_template(TEMPLATE_M04, code=request.args.get("code", ""), result=None, message=None)


@bp.post("/check-in")
@login_required
def check_in_submit():
    student = _current_student()
    payload = request.get_json(silent=True) or {}
    code = payload.get("code") or request.form.get("code", "")

    result = student.check_in(code)

    retry_after = check_in_service.lock_seconds_left(student.id) if result is CheckInResult.TOO_MANY_ATTEMPTS else 0
    message = MESSAGES[result].format(minutes=max(1, math.ceil(retry_after / 60)))
    headers = {"Retry-After": str(retry_after)} if retry_after else {}
    status = HTTP_STATUS[result]

    if request.is_json:
        return jsonify(result=result.value, message=message), status, headers
    return render_template(TEMPLATE_M04, code="", result=result.value, message=message), status, headers
