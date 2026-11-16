"""Enum theo Hình 5.1 / 6.1. Giá trị lưu trong CSDL là tên viết hoa (PRESENT, QR_PIN...).

MySQL: kiểu ENUM thật. SQLite: VARCHAR + ràng buộc CHECK.
"""
import enum

from app.extensions import db


class Role(enum.Enum):
    STUDENT = "STUDENT"
    LECTURER = "LECTURER"
    ADMIN = "ADMIN"


class AttendanceStatus(enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class CheckInMethod(enum.Enum):
    MANUAL = "MANUAL"
    QR_PIN = "QR_PIN"


class LeaveStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def enum_col(enum_cls, name):
    return db.Enum(enum_cls, name=name, create_constraint=True)
