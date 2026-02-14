# Contro

Open-source headless CMS framework built with Django. This repository is a work in progress that targets feature parity with Strapi: dynamic content types, auto-generated REST/GraphQL APIs, media library, RBAC, i18n, plugins, draft/publish, webhooks, and API tokens.

## Quick start (local)

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

2. Configure environment variables (PostgreSQL is the default database):

```bash
cp .env.example .env
```

3. Run migrations and start the server:

```bash
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py runserver
```

## Environment variables

- `DATABASE_URL` (default: `sqlite:///db.sqlite3`)
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CORS_ALLOW_ALL_ORIGINS`

## Project structure

- `contro/` Django project configuration
- `contro/apps/` Modular apps for core, content, media, IAM, API, and GraphQL
- `manage.py` Django management entrypoint
