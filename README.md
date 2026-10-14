# Livora: Blood Donation & Blood Bank Management

## Run on your computer
```
python -m venv venv
venv\Scripts\activate        # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000
Default admin login: admin@livora.local / admin123 (change before deploying!)

## Deploy free on Render
1. Push this folder to a GitHub repo.
2. render.com -> New -> Web Service -> pick your repo.
3. Build command: `pip install -r requirements.txt`   Start command: `gunicorn app:app`
4. Environment variables: SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
5. For permanent data: New -> PostgreSQL (free), copy its Internal Database URL
   into an env var named DATABASE_URL. Without it, SQLite data resets on each deploy.
