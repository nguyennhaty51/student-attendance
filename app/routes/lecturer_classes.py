
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models.enums import Role
from app.services.class_service import ClassService
from app.utils.decorators import role_required


lecturer_classes_bp = Blueprint("lecturer_classes", __name__)


@lecturer_classes_bp.get("/lecturer/classes")
@login_required
@role_required(Role.LECTURER)
def teaching_classes():
    classes = ClassService.teaching_classes(current_user.id)

    return render_template(
        "lecturer/classes.html",
        classes=classes,
    )
