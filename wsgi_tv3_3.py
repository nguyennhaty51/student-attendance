
"""Separate application entry point for TV3-3."""

from app import create_app

from app_routes_tv3_3 import tv3_3_bp


app = create_app()

app.register_blueprint(tv3_3_bp)
