
from app.extensions import db
from app.models.academic import ClassSection


class ClassService:
    """Các nghiệp vụ liên quan đến lớp học phần."""

    @staticmethod
    def teaching_classes(lecturer_id: int):
        """Lấy danh sách lớp học phần do giảng viên phụ trách."""
        return (
            db.session.query(ClassSection)
            .filter(ClassSection.lecturer_id == lecturer_id)
            .order_by(ClassSection.id.desc())
            .all()
        )
