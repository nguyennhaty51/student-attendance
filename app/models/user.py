"""User (trừu tượng), Student, Lecturer, Admin – Hình 5.1; bảng users, students, lecturers – Hình 6.1.

Kế thừa: `users` chứa trường chung + cột `role`; `students` và `lecturers` là bảng riêng với
khóa chính `user_id` (cũng là khóa ngoại tới users.id). Admin dùng chung bảng `users`.
"""
import bcrypt

from app.extensions import db
from .enums import Role, enum_col


class User(db.Model):
    """Lớp trừu tượng: không tạo trực tiếp, chỉ tạo Student / Lecturer / Admin."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(enum_col(Role, "ck_users_role"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    __mapper_args__ = {"polymorphic_on": role}

    def __init__(self, **kwargs):
        if type(self) is User:
            raise TypeError("User là lớp trừu tượng; hãy tạo Student, Lecturer hoặc Admin.")
        password = kwargs.pop("password", None)
        super().__init__(**kwargs)
        if password is not None:
            self.set_password(password)

    # ----- hỗ trợ mật khẩu (NFR7: lưu băm bcrypt, không lưu văn bản thô) -----
    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode("utf-8"), self.password_hash.encode("ascii"))
        except ValueError:
            return False

    # ----- phương thức trong sơ đồ: login(), logout(), changePassword() -----
    def login(self, password: str) -> bool:
        """Đúng mật khẩu và tài khoản chưa bị khóa. Việc tạo phiên đăng nhập do AuthService (TV2) làm."""
        return bool(self.is_active and self.check_password(password))

    def logout(self) -> None:
        raise NotImplementedError("TODO TV2: AuthService.logout")

    def change_password(self, old_password: str, new_password: str) -> bool:
        raise NotImplementedError("TODO TV2: AuthService.change_password")

    def __repr__(self):
        return f"<{type(self).__name__} {self.username}>"


class Student(User):
    __tablename__ = "students"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False)
    class_name = db.Column(db.String(50))

    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendances = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    leave_requests = db.relationship("LeaveRequest", back_populates="student", cascade="all, delete-orphan")

    __mapper_args__ = {"polymorphic_identity": Role.STUDENT}

    def view_attendance_history(self, section_id: int | None = None):
        """UC2."""
        raise NotImplementedError("TODO TV2: AttendanceService.history_for_student")

    def check_in(self, code: str):
        """UC3 – điểm danh bằng mã (checkIn(code))."""
        raise NotImplementedError("TODO TV2: AttendanceService.check_in")

    def submit_leave_request(self, session_id: int, reason: str):
        """UC4."""
        raise NotImplementedError("TODO TV3: LeaveService.submit")

    def view_notifications(self, unread_only: bool = False):
        """UC15."""
        raise NotImplementedError("TODO TV3: NotificationService.list_for_user")


class Lecturer(User):
    __tablename__ = "lecturers"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lecturer_code = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100))

    sections = db.relationship("ClassSection", back_populates="lecturer")
    edited_logs = db.relationship("AttendanceLog", back_populates="editor")
    reviewed_requests = db.relationship("LeaveRequest", back_populates="reviewer")

    __mapper_args__ = {"polymorphic_identity": Role.LECTURER}

    def view_teaching_classes(self):
        """UC16."""
        raise NotImplementedError("TODO TV3: ClassService.teaching_classes")

    def take_attendance(self, session_id: int, records: dict):
        """UC5. records: {student_id: (AttendanceStatus, note)}."""
        raise NotImplementedError("TODO TV2: AttendanceService.take_attendance")

    def open_check_in_session(self, session_id: int, minutes: int = 5):
        """UC6."""
        raise NotImplementedError("TODO TV2: AttendanceService.open_check_in_session")

    def edit_attendance(self, attendance_id: int, new_status, reason: str):
        """UC7 – ghi AttendanceLog (BR6)."""
        raise NotImplementedError("TODO TV2: AttendanceService.edit_attendance")

    def review_leave(self, leave_id: int, approve: bool):
        """UC8."""
        raise NotImplementedError("TODO TV3: LeaveService.review")

    def view_report(self, **filters):
        """UC9 (chỉ các lớp của giảng viên – BR4)."""
        raise NotImplementedError("TODO TV3: ReportService.generate")


class Admin(User):
    """Quản trị viên: dùng chung bảng `users` (single-table inheritance), không thêm cột."""

    __mapper_args__ = {"polymorphic_identity": Role.ADMIN}

    def manage_users(self, action: str, **data):
        """UC11. action: create | update | lock | unlock | reset_password."""
        raise NotImplementedError("TODO TV3: UserService.manage_users")

    def manage_sections(self, action: str, **data):
        """UC12."""
        raise NotImplementedError("TODO TV3: ClassService.manage_sections")

    def manage_sessions(self, action: str, **data):
        """UC13."""
        raise NotImplementedError("TODO TV3: ClassService.manage_sessions")

    def view_report(self, **filters):
        """UC9 (toàn hệ thống)."""
        raise NotImplementedError("TODO TV3: ReportService.generate")
