# LIVORA — Flask backend with accounts and saved blood requests

## Features
- Registration with hashed passwords and server-side validation
- Sign in / sign out using a secure, HTTP-only session cookie
- Blood requests saved in a SQL database
- Signed-in users can list requests; phone and notes are only shown to the requester and hospital/blood-bank roles
- Request status updates with server-side authorization checks
- Existing LIVORA dashboard kept in `public/index.html`

## Run locally
Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Set a development secret if desired, then run:

```bash
python app.py
```

Open http://127.0.0.1:10000. Without `DATABASE_URL`, local testing uses `livora_local.db`.

## Deploy to Render
In your existing Web Service settings use:
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

Set these environment variables in Render:
- `SECRET_KEY`: a long random secret (do not use the development fallback)
- `DATABASE_URL`: PostgreSQL connection string from your hosted PostgreSQL provider (for example, a database you create separately). Use the provider's internal URL only when the app and database are in the same provider/network; otherwise use the external URL.

**Important persistence note:** The local SQLite fallback is for development only. Render's ordinary service filesystem can be ephemeral, so a deployed app must use PostgreSQL through `DATABASE_URL` if blood requests should survive restarts and redeploys. Keep the database URL private and never commit it to GitHub.

After changing files, commit and push to GitHub; Render will deploy the latest commit if auto-deploy is enabled.

## API endpoints
- `POST /api/register` JSON: `{ "name", "email", "password", "role" }`
- `POST /api/login` JSON: `{ "email", "password" }`
- `POST /api/logout`
- `GET /api/me`
- `POST /api/blood-requests` (signed in)
- `GET /api/blood-requests` (signed in)
- `PATCH /api/blood-requests/<id>` JSON: `{ "status": "In Progress" }`
- `GET /api/health`

This is a prototype, not a clinical or verified blood-bank system. It does not verify donors or live inventory and does not send alerts. Do not use it for emergency medical decisions. Use verified local medical services for urgent needs. Before real public use, add email verification, rate limiting, CSRF protection, audit logging, backups, stronger role-based review, and privacy/legal review.
