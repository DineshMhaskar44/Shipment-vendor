"""Custom Flask CLI commands.

Usage:
  flask init-db          # creates tables (use only if not running migrations)
  flask seed-demo        # inserts demo admin, vendors, RFQs, shipments
  flask create-admin     # interactive admin user creation
"""
import click
from getpass import getpass
from .extensions import db
from .models import User
from seeds.seed_data import seed_all


def register_cli(app):

    @app.cli.command("init-db")
    def init_db():
        """Create all tables (alternative to flask db upgrade for quick start)."""
        with app.app_context():
            db.create_all()
            click.echo("Tables created.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Insert demo data (admin, vendor users, vendors, RFQs, shipments)."""
        with app.app_context():
            db.create_all()
            seed_all()
            click.echo("Demo data inserted.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    def create_admin(email, name):
        """Create an admin user interactively."""
        with app.app_context():
            if User.query.filter_by(email=email.lower()).first():
                click.echo("Email already exists.")
                return
            password = getpass("Password: ")
            confirm = getpass("Confirm: ")
            if password != confirm:
                click.echo("Passwords don't match.")
                return
            u = User(name=name, email=email.lower(), role="admin", is_active=True)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            click.echo(f"Admin {email} created.")
