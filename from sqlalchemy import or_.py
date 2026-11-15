from sqlalchemy import or_
from app.extensions import db
from app.models import User, Student, Lecturer, Attendance


class UserRepository:

    @staticmethod
    def get_by_id(user_id):
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_by_code(code):
        student = Student.query.filter_by(
            student_code=code
        ).first()

        if student:
            return student.user

        lecturer = Lecturer.query.filter_by(
            lecturer_code=code
        ).first()

        if lecturer:
            return lecturer.user

        return None

    @staticmethod
    def find_duplicate(username, email, code, exclude_id=None):
        query = User.query.filter(
            or_(
                User.username == username,
                User.email == email
            )
        )

        if exclude_id is not None:
            query = query.filter(User.id != exclude_id)

        duplicate_user = query.first()

        if duplicate_user:
            return True

        if code:
            student_query = Student.query.filter_by(
                student_code=code
            )

            lecturer_query = Lecturer.query.filter_by(
                lecturer_code=code
            )

            if exclude_id is not None:
                student_query = student_query.filter(
                    Student.user_id != exclude_id
                )
                lecturer_query = lecturer_query.filter(
                    Lecturer.user_id != exclude_id
                )

            if student_query.first() or lecturer_query.first():
                return True

        return False

    @staticmethod
    def search_users(keyword="", role="", page=1, per_page=10):
        query = User.query.outerjoin(Student).outerjoin(Lecturer)

        if keyword:
            pattern = f"%{keyword}%"

            query = query.filter(
                or_(
                    User.username.ilike(pattern),
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    Student.student_code.ilike(pattern),
                    Lecturer.lecturer_code.ilike(pattern)
                )
            )

        if role in ("STUDENT", "LECTURER"):
            query = query.filter(User.role == role)

        return query.order_by(User.id.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

    @staticmethod
    def has_attendance(user):
        if user.role != "STUDENT" or not user.student:
            return False

        return Attendance.query.filter_by(
            student_id=user.student.id
        ).first() is not None

    @staticmethod
    def save(user):
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def delete(user):
        db.session.delete(user)
        db.session.commit()

    @staticmethod
    def commit():
        db.session.commit()

    @staticmethod
    def rollback():
        db.session.rollback()