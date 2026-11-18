
"""Admin routes for UC13 - Manage Sessions."""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for
)

from flask_login import current_user

from app.extensions import db
from app.errors import ServiceError

from app.models import (
    Attendance,
    ClassSection,
    ClassSession,
    Course
)

from app.models.enums import Role
from app.utils.decorators import role_required


bp = Blueprint("admin_sessions", __name__)


@bp.get("/sessions")
@role_required(Role.ADMIN)
def sessions():

    sections = (
        ClassSection.query
        .join(Course)
        .order_by(
            ClassSection.semester.desc(),
            Course.code
        )
        .all()
    )

    selected_id = request.args.get(
        "section_id", type=int
    )

    selected = (
        db.session.get(ClassSection, selected_id)
        if selected_id else None
    )

    items = []

    if selected:

        session_list = (
            ClassSession.query
            .filter_by(section_id=selected.id)
            .order_by(
                ClassSession.session_date,
                ClassSession.start_time
            )
            .all()
        )

        for item in session_list:

            has_attendance = (
                Attendance.query
                .filter_by(session_id=item.id)
                .first() is not None
            )

            items.append({
                "session": item,
                "has_attendance": has_attendance
            })

    return render_template(
        "admin/sessions.html",
        sections=sections,
        selected_section=selected,
        sessions=items
    )


@bp.post("/sessions")
@role_required(Role.ADMIN)
def create_session():

    section_id = request.form.get(
        "section_id", type=int
    )

    try:
        current_user.manage_sessions(
            "create",
            section_id=section_id,
            session_date=request.form.get("session_date"),
            start_time=request.form.get("start_time"),
            end_time=request.form.get("end_time")
        )

        flash(
            "Session created successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sessions.sessions",
            section_id=section_id
        )
    )


@bp.post("/sessions/weekly")
@role_required(Role.ADMIN)
def create_weekly_sessions():

    section_id = request.form.get(
        "section_id", type=int
    )

    try:
        created = current_user.manage_sessions(
            "create_weekly",
            section_id=section_id,
            start_date=request.form.get("start_date"),
            weekday=request.form.get("weekday"),
            start_time=request.form.get("start_time"),
            end_time=request.form.get("end_time"),
            count=request.form.get("count")
        )

        flash(
            f"{len(created)} weekly sessions created successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sessions.sessions",
            section_id=section_id
        )
    )


@bp.post("/sessions/<int:session_id>/edit")
@role_required(Role.ADMIN)
def edit_session(session_id):

    item = db.session.get(
        ClassSession,
        session_id
    )

    section_id = (
        item.section_id
        if item
        else request.form.get("section_id", type=int)
    )

    try:
        current_user.manage_sessions(
            "update",
            session_id=session_id,
            session_date=request.form.get("session_date"),
            start_time=request.form.get("start_time"),
            end_time=request.form.get("end_time")
        )

        flash(
            "Session updated successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sessions.sessions",
            section_id=section_id
        )
    )


@bp.post("/sessions/<int:session_id>/delete")
@role_required(Role.ADMIN)
def delete_session(session_id):

    item = db.session.get(
        ClassSession,
        session_id
    )

    section_id = (
        item.section_id
        if item
        else request.form.get("section_id", type=int)
    )

    try:
        current_user.manage_sessions(
            "delete",
            session_id=session_id
        )

        flash(
            "Session deleted successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sessions.sessions",
            section_id=section_id
        )
    )
