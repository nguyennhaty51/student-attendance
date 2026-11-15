from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config

from .extensions import db, migrate


@event.listens_for(Engine, "connect")
def _sqlite_enable_fk(dbapi_connection, _record):
    """SQLite mặc định không kiểm tra khóa ngoại; bật lên để khớp MySQL."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    # render_as_batch=True để Alembic sửa bảng được trên SQLite
    migrate.init_app(app, db, render_as_batch=True)

    from . import models  # noqa: F401  (đăng ký model cho Flask-Migrate)
    from app.routes import main_bp

    app.register_blueprint(main_bp)
    return app