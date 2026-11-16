import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///attendance.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ABSENCE_THRESHOLD = 0.20      # BR7: ngưỡng cảnh báo vắng 20%
    CODE_LENGTH = 6               # BR5: PIN 6 chữ số
    CODE_TTL_MINUTES = 5          # BR5: hiệu lực mặc định 5 phút


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # test gửi form không cần csrf_token