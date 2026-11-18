
"""Lecturer routes for UC16 - View Teaching Classes."""

from flask import (
    Blueprint,
    render_template,
    request
)

from flask_login import current_user

from werkzeug.exceptions import (
    NotFound,
    Forbidden
)

from app.extensions import db
from app.errors import ServiceError

from app.models import ClassSection
from app.models.enums import Role

from app.services.class_service import ClassService
from app.utils.decorators import role_required


bp = Blueprint(
    "lecturer_classes",
    __name__
)


@bp.get("/classes")
@role_required(Role.LECTURER)
def classes():

    semester = request.args.get(
        "semester", ""
    ).strip()

    semesters = sorted({
        row[0]
        for row in db.session.query(
            ClassSection.semester
        )
        .filter_by(
            lecturer_id=current_user.id
        )
        .distinct()
        .all()
    }, reverse=True)

    if not semester and semesters:
        semester = semesters[0]

    rows = current_user.view_teaching_classes(
        semester or None
    )

    return render_template(
        "lecturer/classes.html",
        classes=rows,
        semesters=semesters,
        selected_semester=semester
    )


@bp.get("/classes/<int:section_id>/sessions")
@role_required(Role.LECTURER)
def class_detail(section_id):

    try:
        (
            section,
            pagination,
            students,
            sessions
        ) = ClassService.teaching_class_detail(
            current_user.id,
            section_id,
            student_page=request.args.get(
                "page", 1, type=int
            ),
            per_page=20
        )

    except ServiceError as error:

        if error.http_status == 404:
            raise NotFound(error.message)

        if error.http_status == 403:
            raise Forbidden(error.message)

        raise

    return render_template(
        "lecturer/class_detail.html",
        section=section,
        student_pagination=pagination,
        students=students,
        sessions=sessions
    )
