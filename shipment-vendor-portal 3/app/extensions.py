"""Flask extensions are instantiated here without an app, then bound in create_app().

Doing it this way avoids circular imports between models/blueprints.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()
csrf = CSRFProtect()

# Login manager defaults
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
