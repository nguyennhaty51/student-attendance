import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret")
    # SQLite mặc định (dev). MySQL: mysql+pymysql://user:pass@localhost/attendance?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "attendance.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # BR7: ngưỡng cảnh báo vắng mặc định 20% (không có cột riêng trong ERD nên đặt ở cấu hình)
    ABSENCE_THRESHOLD = 0.20
    # BR5: PIN 6 chữ số, hiệu lực mặc định 5 phút
    CODE_LENGTH = 6
    CODE_TTL_MINUTES = 5
