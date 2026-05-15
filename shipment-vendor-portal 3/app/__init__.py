"""Flask application factory.

Composition order:
  1. Build app, load config
  2. Bind extensions (db, migrate, login, mail, jwt, csrf)
  3. Register blueprints
  4. Register error handlers + context processors + CLI commands
"""
import os
from flask import Flask, render_template
from .extensions import db, migrate, login_manager, mail, jwt, csrf
from config import get_config


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class or get_config())

    # Make sure instance + upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ---- Bind extensions ----
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ---- Register blueprints ----
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .shipments.routes import shipments_bp
    from .vendors.routes import vendors_bp
    from .rfq.routes import rfq_bp
    from .reports.routes import reports_bp
    from .admin.routes import admin_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(shipments_bp, url_prefix="/shipments")
    app.register_blueprint(vendors_bp, url_prefix="/vendors")
    app.register_blueprint(rfq_bp, url_prefix="/rfq")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    csrf.exempt(api_bp)  # API uses JWT, not CSRF tokens

    # ---- Context processors ----
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {"now": datetime.utcnow, "app_name": "Shipment & Vendor Portal"}

    # ---- Error handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # ---- CLI commands ----
    from .cli import register_cli
    register_cli(app)

    return app
