"""Course, ClassSection, Enrollment, ClassSession – Hình 5.1; bảng courses, class_sections, enrollments, class_sessions – Hình 6.1."""
import secrets
from datetime import datetime, timedelta

from sqlalchemy.dialects.mysql import TINYINT

from app.extensions import db


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    credits = db.Column(db.SmallInteger().with_variant(TINYINT(), "mysql"), nullable=False)

    sections = db.relationship("ClassSection", back_populates="course")

    def __repr__(self):
        return f"<Course {self.code}>"


class ClassSection(db.Model):
    __tablename__ = "class_sections"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.user_id"), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    room = db.Column(db.String(30))

    course = db.relationship("Course", back_populates="sections")
    lecturer = db.relationship("Lecturer", back_populates="sections")
    enrollments = db.relationship("Enrollment", back_populates="section", cascade="all, delete-orphan")
    sessions = db.relationship(
        "ClassSession", back_populates="section", cascade="all, delete-orphan",
        order_by="ClassSession.session_date, ClassSession.start_time",
    )

    def add_student(self, student_id: int):
        """UC12 – thêm sinh viên vào lớp (tạo Enrollment)."""
        raise NotImplementedError("TODO TV3: ClassService.add_student")

    def get_attendance_rate(self, student_id: int | None = None) -> float:
        """Tỷ lệ điểm danh (BR7). Có student_id: của sinh viên đó; không: toàn lớp."""
        raise NotImplementedError("TODO TV2: AttendanceService.attendance_rate")

    def __repr__(self):
        return f"<ClassSection {self.id} course={self.course_id} {self.semester}>"


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        db.UniqueConstraint("section_id", "student_id", name="uq_enrollments_section_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)

    section = db.relationship("ClassSection", back_populates="enrollments")
    student = db.relationship("Student", back_populates="enrollments")


class ClassSession(db.Model):
    """Một buổi học; giữ mã điểm danh (check_in_code, 6 chữ số) và hạn dùng (code_expiry)."""

    __tablename__ = "class_sessions"

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    check_in_code = db.Column(db.CHAR(6))
    code_expiry = db.Column(db.DateTime)

    section = db.relationship("ClassSection", back_populates="sessions")
    attendances = db.relationship("Attendance", back_populates="session", cascade="all, delete-orphan")
    leave_requests = db.relationship("LeaveRequest", back_populates="session", cascade="all, delete-orphan")

    def generate_code(self, minutes: int = 5) -> str:
        """UC6 – sinh PIN 6 chữ số, hiệu lực `minutes` phút (BR5, mặc định 5). Chưa commit."""
        self.check_in_code = "".join(secrets.choice("0123456789") for _ in range(6))
        self.code_expiry = datetime.utcnow() + timedelta(minutes=minutes)
        return self.check_in_code

    def close_code(self) -> None:
        """Đóng phiên sớm: mã hết hiệu lực ngay (M10 – Close session)."""
        self.code_expiry = datetime.utcnow()

    def is_code_valid(self, code: str | None = None) -> bool:
        """Mã còn hạn (và khớp, nếu truyền `code`). Không có cột trạng thái: phiên mở = có mã chưa hết hạn."""
        if not self.check_in_code or not self.code_expiry or datetime.utcnow() >= self.code_expiry:
            return False
        return code is None or secrets.compare_digest(self.check_in_code, str(code))
