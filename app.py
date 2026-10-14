import os
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

db_url = os.environ.get("DATABASE_URL", "sqlite:///livora.db")
if db_url.startswith("postgres://"):  # Render/Heroku style URL fix
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
db = SQLAlchemy(app)

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
COMPONENTS = ["Whole Blood", "RBC", "Plasma", "Platelets"]
URGENCY = ["Normal", "Urgent", "Emergency"]
STATUSES = ["Pending", "Matched", "Dispatched", "Fulfilled"]


# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="donor")  # donor | staff | admin


class Donor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False)
    district = db.Column(db.String(60), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    hemoglobin = db.Column(db.Float, nullable=False)
    last_donation = db.Column(db.Date)

    def eligibility(self):
        """Return (eligible, reason). Simplified NRCS/WHO-style rules."""
        if not 18 <= self.age <= 60:
            return False, "Age must be between 18 and 60"
        if self.weight < 45:
            return False, "Weight must be at least 45 kg"
        if self.hemoglobin < 12.5:
            return False, "Hemoglobin must be at least 12.5 g/dL"
        if self.last_donation and (date.today() - self.last_donation).days < 90:
            next_ok = self.last_donation + timedelta(days=90)
            return False, f"Can donate again after {next_ok}"
        return True, "Eligible to donate"


class BloodUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(3), nullable=False)
    component = db.Column(db.String(20), nullable=False)
    collected_on = db.Column(db.Date, nullable=False)
    expires_on = db.Column(db.Date, nullable=False)
    bank = db.Column(db.String(100), default="Main Blood Bank")
    issued = db.Column(db.Boolean, default=False)


class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient = db.Column(db.String(100), nullable=False)
    hospital = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False)
    units = db.Column(db.Integer, default=1)
    urgency = db.Column(db.String(20), default="Normal")
    district = db.Column(db.String(60))
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------- Helpers ----------
def current_user():
    uid = session.get("uid")
    return db.session.get(User, uid) if uid else None


@app.context_processor
def inject_globals():
    return dict(me=current_user(), BLOOD_GROUPS=BLOOD_GROUPS, COMPONENTS=COMPONENTS,
                URGENCY=URGENCY, STATUSES=STATUSES, today=date.today())


def staff_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        u = current_user()
        if not u or u.role not in ("staff", "admin"):
            flash("Staff login required.", "error")
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


# ---------- Public pages ----------
@app.route("/")
def index():
    stock = {bg: BloodUnit.query.filter_by(blood_group=bg, issued=False)
             .filter(BloodUnit.expires_on >= date.today()).count() for bg in BLOOD_GROUPS}
    open_requests = BloodRequest.query.filter(BloodRequest.status != "Fulfilled").count()
    return render_template("index.html", stock=stock, donors=Donor.query.count(),
                           open_requests=open_requests)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        if User.query.filter_by(email=f["email"].lower()).first():
            flash("That email is already registered. Log in instead.", "error")
            return redirect(url_for("login"))
        user = User(name=f["name"], email=f["email"].lower(),
                    password_hash=generate_password_hash(f["password"]))
        db.session.add(user)
        db.session.flush()
        last = f.get("last_donation")
        donor = Donor(user_id=user.id, name=f["name"], phone=f["phone"],
                      blood_group=f["blood_group"], district=f["district"].strip().title(),
                      age=int(f["age"]), weight=float(f["weight"]),
                      hemoglobin=float(f["hemoglobin"]),
                      last_donation=datetime.strptime(last, "%Y-%m-%d").date() if last else None)
        db.session.add(donor)
        db.session.commit()
        session["uid"] = user.id
        ok, reason = donor.eligibility()
        flash(f"Registered. {reason}.", "ok" if ok else "warn")
        return redirect(url_for("donors"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(email=request.form["email"].lower()).first()
        if u and check_password_hash(u.password_hash, request.form["password"]):
            session["uid"] = u.id
            return redirect(url_for("dashboard") if u.role != "donor" else url_for("index"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/donors")
def donors():
    q = Donor.query
    bg, district = request.args.get("blood_group", ""), request.args.get("district", "").strip()
    if bg:
        q = q.filter_by(blood_group=bg)
    if district:
        q = q.filter(Donor.district.ilike(f"%{district}%"))
    rows = [(d, *d.eligibility()) for d in q.order_by(Donor.name).all()]
    return render_template("donors.html", rows=rows, bg=bg, district=district)


@app.route("/request", methods=["GET", "POST"])
def new_request():
    if request.method == "POST":
        f = request.form
        r = BloodRequest(patient=f["patient"], hospital=f["hospital"], contact=f["contact"],
                         blood_group=f["blood_group"], units=int(f["units"]),
                         urgency=f["urgency"], district=f["district"].strip().title())
        db.session.add(r)
        db.session.commit()
        flash(f"Request #{r.id} submitted. Save this number to track it.", "ok")
        return redirect(url_for("track", rid=r.id))
    return render_template("request.html")


@app.route("/track", methods=["GET", "POST"])
@app.route("/track/<int:rid>")
def track(rid=None):
    if request.method == "POST":
        rid = request.form.get("rid", type=int)
    r = db.session.get(BloodRequest, rid) if rid else None
    matches = []
    if r:
        matches = Donor.query.filter_by(blood_group=r.blood_group).all()
        matches = [d for d in matches if d.eligibility()[0] and
                   (not r.district or d.district.lower() == r.district.lower())]
    return render_template("track.html", r=r, rid=rid, matches=matches)


# ---------- Staff pages ----------
@app.route("/dashboard")
@staff_required
def dashboard():
    soon = date.today() + timedelta(days=7)
    near_expiry = BloodUnit.query.filter(BloodUnit.issued == False,
                                         BloodUnit.expires_on <= soon).count()
    stock = {bg: BloodUnit.query.filter_by(blood_group=bg, issued=False)
             .filter(BloodUnit.expires_on >= date.today()).count() for bg in BLOOD_GROUPS}
    low = [bg for bg, n in stock.items() if n < 3]
    reqs = BloodRequest.query.order_by(BloodRequest.created_at.desc()).limit(50).all()
    return render_template("dashboard.html", stock=stock, low=low,
                           near_expiry=near_expiry, reqs=reqs)


@app.route("/request/<int:rid>/status", methods=["POST"])
@staff_required
def update_status(rid):
    r = db.get_or_404(BloodRequest, rid)
    r.status = request.form["status"]
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/inventory", methods=["GET", "POST"])
@staff_required
def inventory():
    if request.method == "POST":
        f = request.form
        collected = datetime.strptime(f["collected_on"], "%Y-%m-%d").date()
        shelf_days = {"Whole Blood": 35, "RBC": 42, "Plasma": 365, "Platelets": 5}[f["component"]]
        for _ in range(int(f["count"])):
            db.session.add(BloodUnit(blood_group=f["blood_group"], component=f["component"],
                                     collected_on=collected,
                                     expires_on=collected + timedelta(days=shelf_days),
                                     bank=f.get("bank") or "Main Blood Bank"))
        db.session.commit()
        flash("Units added to stock.", "ok")
        return redirect(url_for("inventory"))
    units = BloodUnit.query.filter_by(issued=False).order_by(BloodUnit.expires_on).all()
    return render_template("inventory.html", units=units)


@app.route("/inventory/<int:uid>/issue", methods=["POST"])
@staff_required
def issue_unit(uid):
    u = db.get_or_404(BloodUnit, uid)
    u.issued = True
    db.session.commit()
    return redirect(url_for("inventory"))


# ---------- Startup ----------
def init_db():
    db.create_all()
    email = os.environ.get("ADMIN_EMAIL", "admin@livora.local").lower()
    if not User.query.filter_by(email=email).first():
        db.session.add(User(name="Admin", email=email, role="admin",
                            password_hash=generate_password_hash(
                                os.environ.get("ADMIN_PASSWORD", "admin123"))))
        db.session.commit()


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
