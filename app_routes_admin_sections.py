
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from flask_login import current_user
from sqlalchemy import distinct

from app.extensions import db
from app.errors import ServiceError

from app.models import (
    Attendance,
    ClassSection,
    ClassSession,
    Course,
    Enrollment,
    Lecturer,
    Student
)

from app.services.class_service import ClassService
from app.utils.decorators import role_required
from app.models.enums import Role


bp = Blueprint("admin_sections", __name__)


def _section_page(page=None):

    semester = request.args.get(
        "semester", ""
    ).strip()

    pagination = ClassService.list_sections(
        semester or None,
        page or request.args.get("page", 1, type=int),
        20
    )

    selected_id = request.args.get(
        "section_id", type=int
    )

    selected = (
        db.session.get(ClassSection, selected_id)
        if selected_id else None
    )

    students = []

    if selected:

        enrolled = (
            Student.query
            .join(
                Enrollment,
                Enrollment.student_id == Student.user_id
            )
            .filter(
                Enrollment.section_id == selected.id
            )
            .order_by(Student.student_code)
            .all()
        )

        for student in enrolled:

            has_attendance = (
                db.session.query(Attendance.id)
                .join(
                    ClassSession,
                    Attendance.session_id == ClassSession.id
                )
                .filter(
                    ClassSession.section_id == selected.id,
                    Attendance.student_id == student.user_id
                )
                .first()
                is not None
            )

            students.append({
                "student": student,
                "has_attendance": has_attendance
            })

    import_result = session.pop(
        "tv3_2_import_result", None
    )

    semesters = [
        row[0]
        for row in db.session.query(
            distinct(ClassSection.semester)
        ).order_by(
            ClassSection.semester.desc()
        ).all()
    ]

    return render_template(
        "admin/sections.html",
        pagination=pagination,
        sections=pagination.items,
        semester=semester,
        semesters=semesters,
        courses=Course.query.order_by(Course.code).all(),
        lecturers=Lecturer.query.order_by(
            Lecturer.full_name
        ).all(),
        selected_section=selected,
        students=students,
        import_result=import_result
    )


@bp.get("/sections")
@role_required(Role.ADMIN)
def sections():
    return _section_page()


@bp.post("/courses")
@role_required(Role.ADMIN)
def create_course():

    try:
        current_user.manage_sections(
            "create_course",
            code=request.form.get("code"),
            name=request.form.get("name"),
            credits=request.form.get("credits")
        )

        flash("Course created successfully.", "success")

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for("admin_sections.sections")
    )


@bp.post("/courses/<int:course_id>/edit")
@role_required(Role.ADMIN)
def edit_course(course_id):

    try:
        current_user.manage_sections(
            "update_course",
            course_id=course_id,
            code=request.form.get("code"),
            name=request.form.get("name"),
            credits=request.form.get("credits")
        )

        flash("Course updated successfully.", "success")

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for("admin_sections.sections")
    )


@bp.post("/courses/<int:course_id>/delete")
@role_required(Role.ADMIN)
def delete_course(course_id):

    try:
        current_user.manage_sections(
            "delete_course",
            course_id=course_id
        )

        flash("Course deleted successfully.", "success")

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for("admin_sections.sections")
    )


@bp.post("/sections")
@role_required(Role.ADMIN)
def create_section():

    try:
        current_user.manage_sections(
            "create_section",
            course_id=request.form.get(
                "course_id", type=int
            ),
            semester=request.form.get("semester"),
            room=request.form.get("room"),
            lecturer_id=request.form.get(
                "lecturer_id", type=int
            )
        )

        flash(
            "Class section created successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sections.sections",
            semester=request.form.get("semester", "")
        )
    )


@bp.post("/sections/<int:section_id>/edit")
@role_required(Role.ADMIN)
def edit_section(section_id):

    try:
        current_user.manage_sections(
            "update_section",
            section_id=section_id,
            course_id=request.form.get(
                "course_id", type=int
            ),
            semester=request.form.get("semester"),
            room=request.form.get("room"),
            lecturer_id=request.form.get(
                "lecturer_id", type=int
            )
        )

        flash(
            "Class section updated successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sections.sections",
            section_id=section_id
        )
    )


@bp.post("/sections/<int:section_id>/students")
@role_required(Role.ADMIN)
def add_student(section_id):

    try:
        current_user.manage_sections(
            "add_student_by_code",
            section_id=section_id,
            student_code=request.form.get("student_code")
        )

        flash(
            "Student added successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sections.sections",
            section_id=section_id
        )
    )


@bp.post("/sections/<int:section_id>/students/import")
@role_required(Role.ADMIN)
def import_students(section_id):

    try:
        result = ClassService.import_students_excel(
            section_id,
            request.files.get("file")
        )

        session["tv3_2_import_result"] = result

        flash(
            f"Import completed: "
            f"{result['success_count']} imported, "
            f"{result['skipped_count']} skipped, "
            f"{result['error_count']} errors.",
            "success" if result["error_count"] == 0
            else "warning"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sections.sections",
            section_id=section_id
        )
    )


@bp.post("/sections/<int:section_id>/students/<int:student_id>/remove")
@role_required(Role.ADMIN)
def remove_student(section_id, student_id):

    try:
        current_user.manage_sections(
            "remove_student",
            section_id=section_id,
            student_id=student_id
        )

        flash(
            "Student removed successfully.",
            "success"
        )

    except ServiceError as error:
        flash(error.message, "danger")

    return redirect(
        url_for(
            "admin_sections.sections",
            section_id=section_id
        )
    )
