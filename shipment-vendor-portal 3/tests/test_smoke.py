"""Smoke tests — app boots, login page renders, login works against seeded data."""
import os
import pytest


@pytest.fixture
def app():
    os.environ["FLASK_ENV"] = "testing"
    from app import create_app
    from app.extensions import db
    from seeds.seed_data import seed_all

    a = create_app()
    with a.app_context():
        db.create_all()
        seed_all()
        yield a
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_page(client):
    rv = client.get("/auth/login")
    assert rv.status_code == 200
    assert b"Sign in" in rv.data


def test_login_redirects_to_dashboard(client):
    rv = client.post("/auth/login",
                     data={"email": "admin@example.com",
                           "password": "admin123"},
                     follow_redirects=True)
    assert rv.status_code == 200
    assert b"Dashboard" in rv.data or b"Total Shipments" in rv.data


def test_api_login(client):
    rv = client.post("/api/v1/auth/login",
                     json={"email": "admin@example.com",
                           "password": "admin123"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "access_token" in data
    assert data["role"] == "admin"
