import os

from flask import Flask

from app.extensions import db, bcrypt, csrf


def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "change-this-secret-key"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///attendance.db"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    from app.controllers.auth_controller import auth_bp
    from app.controllers.admin_controller import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

        # Create demo administrator only when no admin exists.
        from app.models import User

        admin = User.query.filter_by(role="ADMIN").first()

        if not admin:
            admin = User(
                username="admin",
                password_hash=bcrypt.generate_password_hash(
                    "Admin@12345"
                ).decode("utf-8"),
                full_name="System Administrator",
                email="admin@example.com",
                role="ADMIN",
                is_active=True
            )

            db.session.add(admin)
            db.session.commit()

    return app