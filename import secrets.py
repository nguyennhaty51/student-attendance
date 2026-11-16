import secrets
import string

from app.extensions import db, bcrypt
from app.models import User, Student, Lecturer
from app.repositories.user_repository import UserRepository


class UserService:

    @staticmethod
    def list_users(keyword="", role="", page=1):
        return UserRepository.search_users(
            keyword=keyword,
            role=role,
            page=page,
            per_page=10
        )

    @staticmethod
    def create_user(data):
        role = data.get("role", "").upper()
        username = data.get("username", "").strip()
        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        code = data.get("code", "").strip()
        faculty = data.get("faculty", "").strip()
        class_name = data.get("class_name", "").strip()

        if role not in ("STUDENT", "LECTURER"):
            raise ValueError("Invalid user role.")

        if not username or not full_name or not email or not code:
            raise ValueError("All required fields must be completed.")

        if "@" not in email:
            raise ValueError("Invalid email address.")

        if UserRepository.find_duplicate(username, email, code):
            raise ValueError("Username, email or code already exists.")

        temporary_password = UserService.generate_temporary_password()

        password_hash = bcrypt.generate_password_hash(
            temporary_password
        ).decode("utf-8")

        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            email=email,
            role=role,
            is_active=True
        )

        try:
            db.session.add(user)
            db.session.flush()

            if role == "STUDENT":
                profile = Student(
                    user_id=user.id,
                    student_code=code,
                    faculty=faculty,
                    class_name=class_name
                )
                db.session.add(profile)

            else:
                profile = Lecturer(
                    user_id=user.id,
                    lecturer_code=code,
                    faculty=faculty
                )
                db.session.add(profile)

            db.session.commit()

            return user, temporary_password

        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update_user(user_id, data):
        user = UserRepository.get_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        username = data.get("username", "").strip()
        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        code = data.get("code", "").strip()
        faculty = data.get("faculty", "").strip()
        class_name = data.get("class_name", "").strip()

        if not username or not full_name or not email or not code:
            raise ValueError("All required fields must be completed.")

        if "@" not in email:
            raise ValueError("Invalid email address.")

        if UserRepository.find_duplicate(
            username,
            email,
            code,
            exclude_id=user.id
        ):
            raise ValueError("Username, email or code already exists.")

        try:
            user.username = username
            user.full_name = full_name
            user.email = email

            if user.role == "STUDENT":
                if not user.student:
                    raise ValueError("Student profile not found.")

                user.student.student_code = code
                user.student.faculty = faculty
                user.student.class_name = class_name

            elif user.role == "LECTURER":
                if not user.lecturer:
                    raise ValueError("Lecturer profile not found.")

                user.lecturer.lecturer_code = code
                user.lecturer.faculty = faculty

            db.session.commit()
            return user

        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def toggle_active(user_id):
        user = UserRepository.get_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        user.is_active = not user.is_active
        UserRepository.commit()

        return user

    @staticmethod
    def reset_password(user_id):
        user = UserRepository.get_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        temporary_password = UserService.generate_temporary_password()

        user.password_hash = bcrypt.generate_password_hash(
            temporary_password
        ).decode("utf-8")

        UserRepository.commit()

        # Return the temporary password once to the controller.
        return temporary_password

    @staticmethod
    def generate_temporary_password(length=12):
        characters = string.ascii_letters + string.digits + "!@#$%"
        return "".join(
            secrets.choice(characters)
            for _ in range(length)
        )

    @staticmethod
    def delete_user(user_id):
        user = UserRepository.get_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        if UserRepository.has_attendance(user):
            raise ValueError(
                "This account has attendance data and can only be locked."
            )

        UserRepository.delete(user)
        return True