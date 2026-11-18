from flask import Flask, render_template
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config
from .extensions import db, migrate, login_manager, csrf, bcrypt


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
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)

    from . import models  # noqa: F401
    from app.routes import main_bp
    from app.routes.auth import auth_bp
    from app.routes.lecturer_attendance import attendance_bp
    from app.routes.lecturer_classes import lecturer_classes_bp
    from app.routes.student_leave import student_leave_bp
    from app.routes.notifications import notification_bp 

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(lecturer_classes_bp)
    app.register_blueprint(student_leave_bp)
    app.register_blueprint(notification_bp)
    

    @app.errorhandler(403)
    def forbidden(_error):
        """Sai vai trò (role_required) → trang 403."""
        return render_template("errors/403.html"), 403

    return app