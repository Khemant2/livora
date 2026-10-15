import os
import re
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

app = Flask(__name__, static_folder='public')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-this-secret-before-deploying')

# Set DATABASE_URL to a PostgreSQL connection string for persistent hosted storage.
# SQLite is only a local fallback; Render's local filesystem can be ephemeral.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///livora_local.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
connect_args = {'check_same_thread': False} if database_url.startswith('sqlite:') else {}
engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def init_db():
    id_type = 'INTEGER PRIMARY KEY AUTOINCREMENT' if engine.dialect.name == 'sqlite' else 'SERIAL PRIMARY KEY'
    with engine.begin() as conn:
        conn.execute(text(f'''CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            name VARCHAR(120) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role VARCHAR(40) NOT NULL DEFAULT 'Individual / Patient',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )'''))
        conn.execute(text(f'''CREATE TABLE IF NOT EXISTS blood_requests (
            id {id_type},
            user_id INTEGER NOT NULL REFERENCES users(id),
            patient_name VARCHAR(120) NOT NULL,
            blood_group VARCHAR(3) NOT NULL,
            units INTEGER NOT NULL,
            hospital VARCHAR(180) NOT NULL,
            city VARCHAR(100) NOT NULL,
            needed_by VARCHAR(40) NOT NULL,
            contact_phone VARCHAR(40) NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )'''))


init_db()


def rowdict(row):
    return dict(row._mapping)


def current_user():
    if not session.get('user_id'):
        return None
    with engine.connect() as conn:
        row = conn.execute(text('SELECT id, name, email, role FROM users WHERE id=:id'), {'id': session['user_id']}).first()
        return rowdict(row) if row else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({'error': 'Please sign in first.'}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.get('/')
def home():
    return send_from_directory('public', 'index.html')


@app.get('/api/health')
def health():
    return jsonify({'ok': True, 'app': 'LIVORA', 'database': 'connected'})


@app.get('/api/me')
def me():
    user = current_user()
    return jsonify({'user': user})


@app.post('/api/register')
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    role = str(data.get('role', 'Individual / Patient')).strip()
    allowed_roles = {'Individual / Patient', 'Registered Donor', 'Hospital / Medical Facility', 'Blood Bank Partner'}
    if len(name) < 2:
        return jsonify({'error': 'Please enter your full name.'}), 400
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return jsonify({'error': 'Please enter a valid email address.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400
    if role not in allowed_roles:
        return jsonify({'error': 'Please choose a valid account type.'}), 400
    try:
        with engine.begin() as conn:
            result = conn.execute(text('INSERT INTO users (name,email,password_hash,role) VALUES (:name,:email,:password_hash,:role) RETURNING id'), {
                'name': name, 'email': email, 'password_hash': generate_password_hash(password), 'role': role
            })
            user_id = result.scalar_one()
        session.clear()
        session['user_id'] = user_id
        return jsonify({'message': 'Account created successfully.', 'user': current_user()}), 201
    except IntegrityError:
        return jsonify({'error': 'An account with that email already exists. Please sign in.'}), 409


@app.post('/api/login')
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    with engine.connect() as conn:
        row = conn.execute(text('SELECT id, name, email, password_hash, role FROM users WHERE email=:email'), {'email': email}).first()
    if not row or not check_password_hash(row.password_hash, password):
        return jsonify({'error': 'Incorrect email or password.'}), 401
    session.clear()
    session['user_id'] = row.id
    return jsonify({'message': 'Signed in successfully.', 'user': current_user()})


@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify({'message': 'Signed out.'})


@app.post('/api/blood-requests')
@login_required
def create_blood_request():
    user = current_user()
    data = request.get_json(silent=True) or {}
    patient_name = str(data.get('patient_name', '')).strip()
    blood_group = str(data.get('blood_group', '')).strip().upper()
    hospital = str(data.get('hospital', '')).strip()
    city = str(data.get('city', '')).strip()
    phone = str(data.get('contact_phone', '')).strip()
    needed_by = str(data.get('needed_by', '')).strip()
    notes = str(data.get('notes', '')).strip()[:2000]
    try:
        units = int(data.get('units', 0))
    except (TypeError, ValueError):
        units = 0
    if not patient_name or not hospital or not city or not phone or not needed_by:
        return jsonify({'error': 'Please complete all required fields.'}), 400
    if blood_group not in {'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'}:
        return jsonify({'error': 'Please select a valid blood group.'}), 400
    if units < 1 or units > 20:
        return jsonify({'error': 'Units must be between 1 and 20.'}), 400
    with engine.begin() as conn:
        result = conn.execute(text('''INSERT INTO blood_requests
            (user_id,patient_name,blood_group,units,hospital,city,needed_by,contact_phone,notes)
            VALUES (:user_id,:patient_name,:blood_group,:units,:hospital,:city,:needed_by,:phone,:notes)
            RETURNING id, patient_name, blood_group, units, hospital, city, needed_by, status, created_at'''), {
            'user_id': user['id'], 'patient_name': patient_name, 'blood_group': blood_group,
            'units': units, 'hospital': hospital, 'city': city, 'needed_by': needed_by,
            'phone': phone, 'notes': notes
        }).first()
    return jsonify({'message': 'Blood request saved.', 'request': rowdict(result)}), 201


@app.get('/api/blood-requests')
@login_required
def list_blood_requests():
    user = current_user()
    with engine.connect() as conn:
        rows = conn.execute(text('''SELECT r.id, r.patient_name, r.blood_group, r.units, r.hospital,
            r.city, r.needed_by, r.status, r.created_at, r.user_id,
            CASE WHEN r.user_id=:uid OR :is_hospital THEN r.contact_phone ELSE NULL END AS contact_phone,
            CASE WHEN r.user_id=:uid OR :is_hospital THEN r.notes ELSE '' END AS notes,
            u.name AS requester_name
            FROM blood_requests r JOIN users u ON u.id=r.user_id
            ORDER BY r.created_at DESC LIMIT 200'''), {
            'uid': user['id'], 'is_hospital': user['role'] in {'Hospital / Medical Facility', 'Blood Bank Partner'}
        }).all()
    requests_list = []
    for row in rows:
        item = rowdict(row)
        item.pop('user_id', None)
        requests_list.append(item)
    return jsonify({'requests': requests_list})


@app.patch('/api/blood-requests/<int:request_id>')
@login_required
def update_blood_request(request_id):
    user = current_user()
    data = request.get_json(silent=True) or {}
    status = str(data.get('status', '')).strip()
    if status not in {'Pending', 'In Progress', 'Fulfilled', 'Cancelled'}:
        return jsonify({'error': 'Invalid request status.'}), 400
    with engine.begin() as conn:
        row = conn.execute(text('SELECT user_id FROM blood_requests WHERE id=:id'), {'id': request_id}).first()
        if not row:
            return jsonify({'error': 'Blood request not found.'}), 404
        if row.user_id != user['id'] and user['role'] not in {'Hospital / Medical Facility', 'Blood Bank Partner'}:
            return jsonify({'error': 'You are not allowed to update this request.'}), 403
        conn.execute(text('UPDATE blood_requests SET status=:status WHERE id=:id'), {'status': status, 'id': request_id})
    return jsonify({'message': 'Request status updated.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
