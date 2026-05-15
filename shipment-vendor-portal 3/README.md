# Shipment & Vendor Management Portal

A production-ready Flask + MySQL web application for managing **shipment tracking**, **vendor RFQs**, and **logistics MIS reporting**, built for Mosambee.

- **Backend:** Python 3.11+, Flask 3, SQLAlchemy 2, Flask-Migrate, Flask-Login, Flask-JWT-Extended
- **Frontend:** Bootstrap 5, Bootstrap Icons, Chart.js, DataTables, Jinja templates (with dark/light mode)
- **Database:** MySQL 8 (PostgreSQL/SQLite also supported via `DATABASE_URL`)
- **Email:** SMTP via Flask-Mail (Gmail / Outlook / SES / etc.)
- **Excel & PDF:** openpyxl + reportlab — bulk import, exports, six MIS reports

## Features at a glance

- Role-based authentication (Admin, Staff, Vendor) with password reset and session management
- Full **Shipment CRUD** with all 30+ tracking columns and **auto-calculated** delay/payment metrics
- **Dashboard** with KPI cards, OEM/vendor summaries, status doughnut, monthly volume bar chart
- **Vendor RFQ workflow:** create RFQ → email invites with secure tokens → vendor portal submission → comparison table → award
- **Excel import** of shipments, **Excel/PDF export** of any filtered list, **6 MIS reports**
- **REST API (v1)** with JWT, ready for mobile/integration consumers
- Email automation (RFQ invite, quotation received, shipment delay, password reset, user welcome)
- Audit log of every mutation + email log
- Mobile-responsive UI with sidebar navigation and dark/light theme toggle

## Quick start

```bash
# 1. Clone and enter
cd shipment-vendor-portal

# 2. Virtual env
python3 -m venv .venv && source .venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# edit .env — set SECRET_KEY, DATABASE_URL, MAIL_*

# 5. Initialise DB + seed demo data
flask --app run.py seed-demo

# 6. Run
flask --app run.py run --debug
# → http://localhost:5000
```

### Demo credentials (after `seed-demo`)

| Role   | Email                          | Password   |
|--------|--------------------------------|------------|
| Admin  | admin@example.com           | admin123   |
| Staff  | staff@example.com           | staff123   |
| Vendor | vendor.blue@example.com     | vendor123  |
| Vendor | vendor.air@example.com      | vendor123  |
| Vendor | vendor.oem@example.com      | vendor123  |

## Documentation

- [INSTALLATION.md](docs/INSTALLATION.md) — full local setup with MySQL
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Mac Mini, AWS, DigitalOcean, generic VPS
- [API.md](docs/API.md) — REST API reference

## Project layout

```
shipment-vendor-portal/
├── app/                     # Flask application package
│   ├── __init__.py          # application factory
│   ├── extensions.py        # SQLAlchemy, LoginManager, etc.
│   ├── models.py            # all DB models
│   ├── cli.py               # flask init-db / seed-demo / create-admin
│   ├── auth/                # login, logout, password reset
│   ├── admin/               # user mgmt, vendor approval, activity & email log
│   ├── shipments/           # CRUD + Excel import/export + PDF
│   ├── vendors/             # vendor CRUD
│   ├── rfq/                 # RFQ + vendor portal
│   ├── dashboard/           # KPI dashboard + chart endpoints
│   ├── reports/             # 6 MIS reports
│   ├── api/                 # REST API v1 + JWT
│   ├── utils/               # calculations, email, excel, decorators, audit, tokens
│   ├── templates/           # Jinja templates (Bootstrap 5)
│   └── static/              # CSS, JS, uploads
├── seeds/seed_data.py       # demo data
├── migrations/              # alembic migrations (auto-generated)
├── tests/                   # pytest sample tests
├── docs/                    # installation, deployment, API
├── config.py                # env-driven config
├── run.py                   # development entrypoint
├── wsgi.py                  # production entrypoint (gunicorn)
├── requirements.txt
├── .env.example
└── README.md
```

## Future-ready architecture

The codebase is intentionally modular so the following can be added without restructure:

- **WhatsApp alerts** — drop a `utils/whatsapp.py` mirror of `utils/email.py`
- **Mobile app** — REST API already exposes shipments, vendors, RFQs, quotations
- **AI analytics** — pure-Python calculations make it easy to plug models into reports
- **Live courier API integration** — `Shipment.logistics_partner` relationship lets you store API IDs/tokens per partner
- **Webhook ingestion** — register a new blueprint under `/api/v1/webhooks/...`
