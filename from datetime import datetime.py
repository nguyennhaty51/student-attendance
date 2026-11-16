from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    student = db.relationship(
        "Student",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    lecturer = db.relationship(
        "Lecturer",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    student_code = db.Column(db.String(30), unique=True, nullable=False)
    faculty = db.Column(db.String(120))
    class_name = db.Column(db.String(50))

    user = db.relationship("User", back_populates="student")


class Lecturer(db.Model):
    __tablename__ = "lecturers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    lecturer_code = db.Column(db.String(30), unique=True, nullable=False)
    faculty = db.Column(db.String(120))

    user = db.relationship("User", back_populates="lecturer")


class Attendance(db.Model):
    """
    Minimal attendance reference used to prevent deleting
    accounts that already have attendance records.

    Replace this mapping with the group's actual attendance
    model when integrating with the main project.
    """
    __tablename__ = "attendances"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )