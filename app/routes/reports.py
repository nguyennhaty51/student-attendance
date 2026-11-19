from datetime import date
from tempfile import NamedTemporaryFile
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.models.academic import ClassSection, Course
from app.models.enums import Role
from app.services.report_service import ReportService
from app.errors import ServiceError
from app.utils.decorators import role_required

reports_bp = Blueprint("reports", __name__)

def _filters():
    return {key: request.args.get(key, "").strip()
            for key in ("semester", "course_id", "section_id", "date_from", "date_to")}

def _sections(filters):
    query = ClassSection.query
    if current_user.role == Role.LECTURER:
        query = query.filter_by(lecturer_id=current_user.id)
    if filters["semester"]:
        query = query.filter_by(semester=filters["semester"])
    if filters["course_id"]:
        try: query = query.filter_by(course_id=int(filters["course_id"]))
        except ValueError: query = query.filter(ClassSection.id == -1)
    return query.order_by(ClassSection.id.desc()).all()

@reports_bp.get("/reports")
@login_required
@role_required(Role.LECTURER, Role.ADMIN)
def index():
    filters = _filters()
    sections = _sections(filters)
    rows, threshold = [], 0.20
    if filters["section_id"]:
        try:
            report = ReportService.generate_by_section(
                current_user, int(filters["section_id"]), filters["date_from"] or None,
                filters["date_to"] or None)
            rows, threshold = report["rows"], report["threshold"]
        except (ValueError, ServiceError) as exc:
            flash(getattr(exc, "message", "Mã lớp không hợp lệ."), "danger")
    semesters_query = ClassSection.query
    if current_user.role == Role.LECTURER:
        semesters_query = semesters_query.filter_by(lecturer_id=current_user.id)
    semesters = [x[0] for x in semesters_query.with_entities(ClassSection.semester).distinct().order_by(ClassSection.semester).all()]
    courses_query = Course.query.join(ClassSection)
    if current_user.role == Role.LECTURER:
        courses_query = courses_query.filter(ClassSection.lecturer_id == current_user.id)
    courses = courses_query.distinct().order_by(Course.code).all()
    return render_template("reports/index.html",
        filter_options={"semesters": semesters, "courses": courses, "sections": sections},
        filters=filters, rows=rows, threshold=threshold)

@reports_bp.get("/reports/export")
@login_required
@role_required(Role.LECTURER, Role.ADMIN)
def export():
    fmt = request.args.get("format", "").lower()
    if fmt not in ("xlsx", "pdf"):
        abort(400)
    filters = _filters()
    if not filters["section_id"]:
        flash("Vui lòng chọn lớp học phần trước khi xuất báo cáo.", "warning")
        return redirect(url_for("reports.index"))
    try:
        report = ReportService.generate_by_section(current_user, int(filters["section_id"]),
            filters["date_from"] or None, filters["date_to"] or None)
    except (ValueError, ServiceError) as exc:
        flash(getattr(exc, "message", "Bộ lọc không hợp lệ."), "danger")
        return redirect(url_for("reports.index", **filters))
    tmp = NamedTemporaryFile(suffix="."+fmt, delete=False)
    tmp.close()
    if fmt == "xlsx":
        ReportService.export_excel(report, tmp.name)
        mimetype, filename = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "bao-cao-diem-danh.xlsx"
    else:
        ReportService.export_pdf(report, tmp.name)
        mimetype, filename = "application/pdf", "bao-cao-diem-danh.pdf"
    return send_file(tmp.name, as_attachment=True, download_name=filename, mimetype=mimetype)
