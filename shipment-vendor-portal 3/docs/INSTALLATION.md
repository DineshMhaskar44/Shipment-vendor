# Installation Guide

This guide walks through a fresh install on macOS or Linux. Windows works too via WSL.

## 1. Prerequisites

- Python 3.11 or newer
- MySQL 8.x (or MariaDB 10.6+)
- pip + virtualenv
- (Optional) git

```bash
python3 --version    # >= 3.11
mysql --version
```

## 2. Database setup

Log in to MySQL as root and create a dedicated database & user:

```sql
CREATE DATABASE shipment_vendor_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'svp_user'@'localhost' IDENTIFIED BY 'svp_password';
GRANT ALL PRIVILEGES ON shipment_vendor_portal.* TO 'svp_user'@'localhost';
FLUSH PRIVILEGES;
```

> **Tip:** if you don't have MySQL handy you can keep the default in `config.py`, which falls back to a SQLite file under `instance/svp.db`. Everything works the same.

## 3. Get the code

```bash
unzip shipment-vendor-portal.zip   # or git clone <repo>
cd shipment-vendor-portal
```

## 4. Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```ini
SECRET_KEY=<run "python -c 'import secrets;print(secrets.token_urlsafe(48))'">
JWT_SECRET_KEY=<another random string>
DATABASE_URL=mysql+pymysql://svp_user:svp_password@localhost:3306/shipment_vendor_portal

# Email — Gmail example
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your.account@gmail.com
MAIL_PASSWORD=app-password-from-google
MAIL_DEFAULT_SENDER="Shipment Portal <noreply@yourdomain.com>"
ADMIN_NOTIFY_EMAIL=admin@yourdomain.com
```

## 6. Initialise database

The fastest path is to run the seeder, which creates all tables and inserts demo data:

```bash
flask --app run.py seed-demo
```

If you'd rather use Alembic migrations:

```bash
flask --app run.py db init       # only first time
flask --app run.py db migrate -m "initial"
flask --app run.py db upgrade
flask --app run.py create-admin  # interactively create your first admin
```

## 7. Run the dev server

```bash
flask --app run.py run --debug
```

Open <http://localhost:5000> and log in with one of the seeded accounts (see README).

## 8. Common issues

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'MySQLdb'` | `pip install pymysql cryptography` (already in requirements) |
| Email send fails silently | Check `EmailLog` in admin → Email log |
| Vendor cannot see RFQ | Vendor user must be linked to a Vendor profile (admin → Users / Vendors) |
| Migrations conflict | `rm -rf migrations/` and re-run `db init` once |
