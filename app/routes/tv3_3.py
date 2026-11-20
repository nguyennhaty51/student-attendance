
"""TV3-3 routes: UC8, UC9 and UC10."""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for
)

from flask_login import current_user

from app.errors import ServiceError
from app.models import Role

from app.services.tv3_3_service import (
    LeaveService,
    ReportService
)

from app.utils.decorators import role_required


tv3_3_bp = Blueprint("tv3_3", __name__)


def handle_service_error(exc):

    if exc.http_status == 403:
        abort(403)

    if exc.http_status == 404:
        abort(404)

    flash(exc.message, "danger")


# ==================================================
# UC8 - LEAVE APPROVAL
# ==================================================

@tv3_3_bp.route(
    "/lecturer/leave",
    methods=["GET"]
)
@role_required(Role.LECTURER)
def leave_requests():

    status = request.args.get(
        "status",
        "PENDING"
    )

    try:

        requests_list = LeaveService.list_requests(
            current_user.id,
            status
        )

    except ServiceError as exc:

        handle_service_error(exc)

        requests_list = []

    return render_template(
        "lecturer/leave_approval.html",
        leave_requests=requests_list,
        selected_status=status
    )


@tv3_3_bp.route(
    "/lecturer/leave/<int:leave_id>/<action>",
    methods=["POST"]
)
@role_required(Role.LECTURER)
def review_leave(leave_id, action):

    if action not in ("approve", "reject"):
        abort(404)

    try:

        LeaveService.review(
            current_user.id,
            leave_id,
            action == "approve"
        )

    except ServiceError as exc:

        handle_service_error(exc)

    else:

        if action == "approve":

            flash(
                "Đã duyệt đơn xin nghỉ.",
                "success"
            )

        else:

            flash(
                "Đã từ chối đơn xin nghỉ.",
                "success"
            )

    return redirect(
        url_for("tv3_3.leave_requests")
    )


# ==================================================
# UC9 - REPORTS AND STATISTICS
# ==================================================

@tv3_3_bp.route(
    "/reports",
    methods=["GET"]
)
@role_required(
    Role.LECTURER,
    Role.ADMIN
)
def reports():

    filters = {

        "semester": request.args.get(
            "semester", ""
        ).strip(),

        "course_id": request.args.get(
            "course_id", ""
        ).strip(),

        "section_id": request.args.get(
            "section_id", ""
        ).strip(),

        "date_from": request.args.get(
            "date_from", ""
        ).strip(),

        "date_to": request.args.get(
            "date_to", ""
        ).strip(),

        "student_id": request.args.get(
            "student_id", ""
        ).strip()

    }

    filters = {
        key: value
        for key, value in filters.items()
        if value
    }

    try:

        options = ReportService.filter_options(
            current_user
        )

        report = ReportService.generate(
            current_user,
            filters
        )

    except (ServiceError, ValueError) as exc:

        if isinstance(exc, ServiceError):
            handle_service_error(exc)
        else:
            flash(
                "Bộ lọc báo cáo không hợp lệ.",
                "danger"
            )

        options = ReportService.filter_options(
            current_user
        )

        report = {

            "rows": [],

            "summary": {
                "students": 0,
                "sessions": 0,
                "over_threshold": 0
            },

            "generated_at": None,

            "filters": filters

        }

    return render_template(
        "reports/report.html",
        report=report,
        options=options
    )


# ==================================================
# UC10 - EXPORT EXCEL AND PDF
# ==================================================

@tv3_3_bp.route(
    "/reports/export/<file_format>",
    methods=["GET"]
)
@role_required(
    Role.LECTURER,
    Role.ADMIN
)
def export_report(file_format):

    if file_format not in ("excel", "pdf"):
        abort(404)

    filters = {

        key: request.args.get(
            key, ""
        ).strip()

        for key in (
            "semester",
            "course_id",
            "section_id",
            "date_from",
            "date_to",
            "student_id"
        )

        if request.args.get(key, "").strip()

    }

    try:

        report = ReportService.generate(
            current_user,
            filters
        )

        if file_format == "excel":

            stream = ReportService.export_excel(
                report
            )

            return send_file(

                stream,

                as_attachment=True,

                download_name="attendance_report.xlsx",

                mimetype=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )

            )

        stream = ReportService.export_pdf(
            report
        )

        return send_file(

            stream,

            as_attachment=True,

            download_name="attendance_report.pdf",

            mimetype="application/pdf"

        )

    except ServiceError as exc:

        handle_service_error(exc)

        return redirect(
            url_for(
                "tv3_3.reports",
                **filters
            )
        )
