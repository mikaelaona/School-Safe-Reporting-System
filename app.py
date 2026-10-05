from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
from math import radians, sin, cos, sqrt, atan2
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DB_PATH = os.environ.get("DATABASE_PATH", "ojt_system.db")

# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            geofence_m INTEGER DEFAULT 150
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student','adviser','supervisor','admin')),
            email TEXT,
            company_id INTEGER,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS placements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER UNIQUE NOT NULL,
            company_id INTEGER NOT NULL,
            supervisor_id INTEGER,
            position TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            required_hours INTEGER DEFAULT 400,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY(supervisor_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            lat_in REAL,
            lng_in REAL,
            distance_in REAL,
            location_status TEXT,
            verification_status TEXT DEFAULT 'Pending',
            supervisor_comment TEXT,
            UNIQUE(student_id, work_date),
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            task TEXT NOT NULL,
            hours REAL DEFAULT 0,
            evidence_note TEXT,
            status TEXT DEFAULT 'Pending',
            supervisor_comment TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            summary TEXT NOT NULL,
            challenges TEXT,
            learnings TEXT,
            status TEXT DEFAULT 'Submitted',
            adviser_comment TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placement_id INTEGER NOT NULL,
            evaluator_id INTEGER NOT NULL,
            attendance_rating REAL DEFAULT 0,
            work_quality REAL DEFAULT 0,
            communication_rating REAL DEFAULT 0,
            professionalism_rating REAL DEFAULT 0,
            initiative_rating REAL DEFAULT 0,
            comment TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(placement_id, evaluator_id),
            FOREIGN KEY(placement_id) REFERENCES placements(id) ON DELETE CASCADE,
            FOREIGN KEY(evaluator_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    company = conn.execute(
        "SELECT id FROM companies WHERE name = ?",
        ("ABC Technology Solutions",),
    ).fetchone()

    if not company:
        cur = conn.execute(
            """
            INSERT INTO companies(name, address, latitude, longitude, geofence_m)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "ABC Technology Solutions",
                "Set company address in Admin > Companies",
                None,
                None,
                150,
            ),
        )
        company_id = cur.lastrowid
    else:
        company_id = company["id"]

    def add_user(username, password, full_name, role, email, user_company_id=None):
        exists = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not exists:
            conn.execute(
                """
                INSERT INTO users(
                    username, password_hash, full_name, role, email, company_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    generate_password_hash(password),
                    full_name,
                    role,
                    email,
                    user_company_id,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    add_user("admin", "admin123", "System Administrator", "admin", "admin@school.edu.ph")
    add_user("adviser", "adviser123", "OJT Adviser", "adviser", "adviser@school.edu.ph")
    supervisor = add_user(
        "supervisor",
        "supervisor123",
        "Company Supervisor",
        "supervisor",
        "supervisor@company.com",
        company_id,
    )
    student = add_user(
        "student",
        "student123",
        "Juan Dela Cruz",
        "student",
        "juan@student.edu.ph",
    )

    placement = conn.execute(
        "SELECT id FROM placements WHERE student_id = ?", (student["id"],)
    ).fetchone()
    if not placement:
        conn.execute(
            """
            INSERT INTO placements(
                student_id, company_id, supervisor_id, position,
                start_date, end_date, required_hours, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student["id"],
                company_id,
                supervisor["id"],
                "IT Intern",
                date.today().isoformat(),
                (date.today() + timedelta(days=60)).isoformat(),
                400,
                "Active",
            ),
        )

    if not conn.execute("SELECT id FROM announcements LIMIT 1").fetchone():
        conn.execute(
            "INSERT INTO announcements(title, message, created_at) VALUES (?, ?, ?)",
            (
                "OJT Monitoring Reminder",
                "Keep your attendance and weekly reports updated.",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    conn.commit()
    conn.close()


init_db()

# =========================================================
# HELPERS
# =========================================================

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)
    ).fetchone()
    conn.close()
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            session.clear()
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    allowed = {str(role).strip().lower() for role in roles}

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                session.clear()
                return redirect(url_for("login"))
            if str(user["role"]).strip().lower() not in allowed:
                flash("You do not have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def now():
    return datetime.now().isoformat(timespec="seconds")


def distance_m(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        r = 6371000
        p1 = radians(float(lat1))
        p2 = radians(float(lat2))
        dp = radians(float(lat2) - float(lat1))
        dl = radians(float(lon2) - float(lon1))
        a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
        return 2 * r * atan2(sqrt(a), sqrt(1 - a))
    except (TypeError, ValueError):
        return None


def placement_for(student_id):
    conn = db()
    placement = conn.execute(
        """
        SELECT
            p.*,
            c.name AS company_name,
            c.address AS company_address,
            c.latitude,
            c.longitude,
            c.geofence_m,
            u.full_name AS supervisor_name
        FROM placements p
        JOIN companies c ON c.id = p.company_id
        LEFT JOIN users u ON u.id = p.supervisor_id
        WHERE p.student_id = ?
        """,
        (student_id,),
    ).fetchone()
    conn.close()
    return placement


def notify(user_id, title, message):
    if not user_id:
        return
    conn = db()
    conn.execute(
        "INSERT INTO notifications(user_id, title, message, created_at) VALUES (?, ?, ?, ?)",
        (user_id, title, message, now()),
    )
    conn.commit()
    conn.close()


def total_hours(student_id):
    conn = db()
    rows = conn.execute(
        "SELECT time_in, time_out FROM attendance WHERE student_id = ?",
        (student_id,),
    ).fetchall()
    conn.close()

    total = 0.0
    for row in rows:
        if row["time_in"] and row["time_out"]:
            try:
                start = datetime.fromisoformat(row["time_in"])
                end = datetime.fromisoformat(row["time_out"])
                total += max(0.0, (end - start).total_seconds() / 3600)
            except ValueError:
                continue
    return round(total, 2)


def progress_for(student_id):
    placement = placement_for(student_id)
    if not placement:
        return 0
    hours = total_hours(student_id)
    required = max(1, int(placement["required_hours"] or 0))
    return min(100, round((hours / required) * 100))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# =========================================================
# UI
# =========================================================

CSS = """
:root{--navy:#0b1f3a;--blue:#1769d1;--blue2:#0d4fa8;--sky:#eaf3ff;--ink:#172033;--muted:#6b7688;--line:#e5eaf2;--white:#fff;--green:#15945c;--red:#d64545;--orange:#d98916;--shadow:0 12px 35px rgba(15,35,65,.08)}
*{box-sizing:border-box}
body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f8fc;color:var(--ink)}
a{text-decoration:none;color:inherit}
button,input,select,textarea{font:inherit}
.shell{display:flex;min-height:100vh}
.sidebar{width:250px;background:linear-gradient(180deg,#0b1f3a,#10345e);color:#fff;padding:22px 16px;position:fixed;top:0;bottom:0;left:0;overflow:auto}
.brand{display:flex;gap:11px;align-items:center;padding:8px 10px 25px}.logo{width:43px;height:43px;border-radius:12px;background:#fff;color:var(--blue);display:grid;place-items:center;font-weight:900}.brand strong{display:block;font-size:15px}.brand small{opacity:.68}
.nav a{display:flex;gap:12px;align-items:center;padding:12px 13px;margin:4px 0;border-radius:11px;color:#dbe7f7;font-size:14px}.nav a:hover,.nav a.active{background:rgba(255,255,255,.12);color:#fff}.nav-section{font-size:10px;text-transform:uppercase;letter-spacing:1.2px;opacity:.5;margin:20px 12px 7px}
.logout{position:absolute;bottom:18px;left:16px;right:16px}.main{margin-left:250px;width:calc(100% - 250px);min-height:100vh}.top{height:70px;background:#fff;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;padding:0 30px;position:sticky;top:0;z-index:5}.top h2{font-size:19px;margin:0}.userpill{display:flex;gap:10px;align-items:center}.avatar{width:38px;height:38px;border-radius:50%;background:var(--sky);color:var(--blue);display:grid;place-items:center;font-weight:800}
.content{padding:30px;max-width:1500px;margin:auto}.hero{background:linear-gradient(135deg,#0d4fa8,#1769d1);color:#fff;border-radius:22px;padding:28px;box-shadow:var(--shadow);display:flex;justify-content:space-between;gap:20px;overflow:hidden}.hero h1{margin:0 0 8px;font-size:27px}.hero p{margin:0;color:#dcecff}.hero-stat{text-align:right;min-width:180px}.hero-stat strong{font-size:38px;display:block}.grid{display:grid;gap:18px}.stats{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:20px}.card{background:#fff;border:1px solid var(--line);border-radius:17px;padding:20px;box-shadow:0 5px 22px rgba(15,35,65,.04)}.stat-label{font-size:12px;color:var(--muted)}.stat-value{font-size:27px;font-weight:800;margin:6px 0}.stat-icon{float:right;width:38px;height:38px;border-radius:11px;background:var(--sky);display:grid;place-items:center;color:var(--blue)}.section-title{display:flex;justify-content:space-between;align-items:center;margin:28px 0 12px}.section-title h3{margin:0;font-size:17px}.two{grid-template-columns:1.35fr .85fr}.three{grid-template-columns:repeat(3,1fr)}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:620px}th,td{padding:13px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}th{color:var(--muted);font-weight:650;font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.badge{display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:750;background:#eef2f7;color:#526071}.green{background:#e6f7ef;color:#12834f}.red{background:#fdecec;color:#b52d2d}.orange{background:#fff3dc;color:#a66a00}.blue{background:#e8f2ff;color:#1459ae}
.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}.field label{display:block;font-size:12px;font-weight:700;margin-bottom:7px}.field input,.field select,.field textarea{width:100%;border:1px solid #d8dfeb;border-radius:10px;padding:11px 12px;outline:none;background:#fff}.field input:focus,.field select:focus,.field textarea:focus{border-color:#1769d1;box-shadow:0 0 0 3px #e7f1ff}.field.full{grid-column:1/-1}
.btn{border:0;border-radius:10px;padding:11px 15px;background:var(--blue);color:#fff;font-weight:750;cursor:pointer;display:inline-block}.btn:hover{background:var(--blue2)}.btn.secondary{background:#eef3fa;color:#24405f}.btn.green{background:var(--green);color:#fff}.btn.red{background:var(--red);color:#fff}.actions{display:flex;gap:9px;flex-wrap:wrap}
.progress{height:9px;background:#e9edf4;border-radius:20px;overflow:hidden}.progress>span{display:block;height:100%;background:linear-gradient(90deg,#1769d1,#49a3ff);border-radius:20px}.notice{padding:13px 15px;border-radius:11px;background:#f5f8fd;border:1px solid var(--line);margin-bottom:10px}.flash{margin:0 0 15px;padding:12px 14px;border-radius:10px;background:#eaf3ff;color:#1459ae}.flash.error{background:#fdecec;color:#b52d2d}.flash.success{background:#e8f7ef;color:#12834f}
.login-page{min-height:100vh;background:radial-gradient(circle at top right,#2f80ed,#0b1f3a 55%,#061225);display:grid;place-items:center;padding:20px}.login-box{width:min(1040px,100%);display:grid;grid-template-columns:1.1fr .9fr;background:#fff;border-radius:26px;overflow:hidden;box-shadow:0 25px 80px rgba(0,0,0,.25)}.login-info{padding:55px;background:linear-gradient(150deg,#0b1f3a,#145cae);color:#fff}.login-info h1{font-size:39px;line-height:1.1;margin:20px 0 13px}.login-info p{color:#d7e6f9;max-width:480px}.feature{display:flex;gap:10px;margin-top:18px;color:#e9f3ff}.login-form{padding:48px}.login-form h2{margin:0 0 6px;font-size:27px}.login-form .sub{color:var(--muted);margin-bottom:25px}.login-form input{width:100%;padding:13px;border:1px solid #d8dfeb;border-radius:11px;margin-bottom:14px}
.demo{margin-top:20px;padding:12px;background:#f5f8fc;border-radius:12px;font-size:11px;color:#647084}.empty{text-align:center;padding:35px;color:var(--muted)}.mini{font-size:12px;color:var(--muted)}.profile-row{display:flex;justify-content:space-between;gap:20px;padding:10px 0;border-bottom:1px solid var(--line)}.profile-row span:first-child{color:var(--muted)}.checkin-box{border:2px dashed #c9d8eb;padding:25px;border-radius:15px;text-align:center;background:#f8fbff}.big-number{font-size:44px;font-weight:900}
@media(max-width:900px){.sidebar{width:220px}.main{margin-left:220px;width:calc(100% - 220px)}.stats{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}.three{grid-template-columns:1fr}.login-box{grid-template-columns:1fr}.login-info{display:none}}
@media(max-width:650px){.sidebar{position:static;width:100%;height:auto}.shell{display:block}.main{margin:0;width:100%}.nav{display:grid;grid-template-columns:repeat(2,1fr)}.logout{position:static;margin-top:10px}.top{padding:0 15px}.content{padding:18px}.stats{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.hero{display:block}.hero-stat{text-align:left;margin-top:20px}.login-form{padding:30px 22px}.userpill strong{display:none}}
"""

BASE = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{{ title }} · Smart OJT</title>
    <style>""" + CSS + """</style>
</head>
<body>
<div class="shell">
    <aside class="sidebar">
        <div class="brand">
            <div class="logo">OJT</div>
            <div><strong>SLSU-JGE</strong><small>Smart OJT System</small></div>
        </div>

        <nav class="nav">
            <a class='{{ "active" if request.endpoint in ["dashboard", "dashboard_alias"] else "" }}' href='{{ url_for("dashboard") }}'>⌂ Dashboard</a>

            {% if user and user.role == 'student' %}
                <div class="nav-section">Student</div>
                <a class='{{ "active" if request.endpoint == "student_attendance" else "" }}' href='{{ url_for("student_attendance") }}'>◷ Attendance / DTR</a>
                <a class='{{ "active" if request.endpoint == "student_logs" else "" }}' href='{{ url_for("student_logs") }}'>✓ Work Logs</a>
                <a class='{{ "active" if request.endpoint == "student_reports" else "" }}' href='{{ url_for("student_reports") }}'>▣ Weekly Reports</a>
                <a class='{{ "active" if request.endpoint == "student_evaluation" else "" }}' href='{{ url_for("student_evaluation") }}'>★ Evaluation</a>
            {% endif %}

            {% if user and user.role in ['adviser','admin'] %}
                <div class="nav-section">Monitoring</div>
                <a class='{{ "active" if request.endpoint == "monitoring" else "" }}' href='{{ url_for("monitoring") }}'>◉ Student Monitoring</a>
                <a class='{{ "active" if request.endpoint == "reports_review" else "" }}' href='{{ url_for("reports_review") }}'>▣ Weekly Reports</a>
            {% endif %}

            {% if user and user.role in ['supervisor','admin'] %}
                <div class="nav-section">Company</div>
                <a class='{{ "active" if request.endpoint == "supervisor_logs" else "" }}' href='{{ url_for("supervisor_logs") }}'>✓ Verify Work Logs</a>
                <a class='{{ "active" if request.endpoint == "supervisor_attendance" else "" }}' href='{{ url_for("supervisor_attendance") }}'>◷ Verify Attendance</a>
                <a class='{{ "active" if request.endpoint == "supervisor_evaluation" else "" }}' href='{{ url_for("supervisor_evaluation") }}'>★ Evaluation</a>
            {% endif %}

            {% if user and user.role == 'admin' %}
                <div class="nav-section">Administration</div>
                <a class='{{ "active" if request.endpoint == "users" else "" }}' href='{{ url_for("users") }}'>♙ Users</a>
                <a class='{{ "active" if request.endpoint == "companies" else "" }}' href='{{ url_for("companies") }}'>▦ Companies</a>
                <a class='{{ "active" if request.endpoint == "announcements" else "" }}' href='{{ url_for("announcements") }}'>✦ Announcements</a>
            {% endif %}
        </nav>

        <a class="btn secondary logout" href="{{ url_for('logout') }}">↪ Log out</a>
    </aside>

    <main class="main">
        <header class="top">
            <h2>{{ title }}</h2>
            <div class="userpill">
                {% if user %}
                    <span class="mini">{{ user.role|capitalize }}</span>
                    <div class="avatar">{{ user.full_name[0]|upper }}</div>
                    <strong>{{ user.full_name }}</strong>
                {% endif %}
            </div>
        </header>

        <section class="content">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endwith %}
            {{ body|safe }}
        </section>
    </main>
</div>
</body>
</html>
"""


def page(title, body, user=None):
    return render_template_string(BASE, title=title, body=body, user=user or current_user())

# =========================================================
# AUTHENTICATION
# =========================================================

LOGIN_PAGE = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Login · Smart OJT</title>
    <style>""" + CSS + """</style>
</head>
<body>
<div class="login-page">
    <div class="login-box">
        <div class="login-info">
            <div class="logo">OJT</div>
            <h1>Smart OJT Management & Monitoring</h1>
            <p>A professional platform for monitoring attendance, work activities, reports, evaluations, and OJT progress.</p>
            <div class="feature">✓ Verified attendance and work logs</div>
            <div class="feature">✓ GPS-based workplace check-in</div>
            <div class="feature">✓ Student, Adviser, Supervisor & Admin portals</div>
        </div>
        <div class="login-form">
            <h2>Welcome back</h2>
            <div class="sub">Sign in to continue to your OJT portal.</div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endwith %}

            <form method="post" autocomplete="on">
                <input name="username" placeholder="Username" autocomplete="username" required autofocus>
                <input name="password" type="password" placeholder="Password" autocomplete="current-password" required>
                <button class="btn" style="width:100%" type="submit">Sign In</button>
            </form>

            <div class="demo">
                <b>Demo accounts</b><br>
                Student: student / student123<br>
                Adviser: adviser / adviser123<br>
                Supervisor: supervisor / supervisor123<br>
                Admin: admin / admin123
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND active = 1",
            (username,),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password. Please try again.", "error")

    return render_template_string(LOGIN_PAGE)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================================================
# DASHBOARD
# =========================================================


def student_dashboard_view(user):
    conn = db()
    placement = placement_for(user["id"])
    hours = total_hours(user["id"])
    progress = progress_for(user["id"])

    attendance_rows = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? ORDER BY work_date DESC LIMIT 7",
        (user["id"],),
    ).fetchall()
    recent_logs = conn.execute(
        "SELECT * FROM work_logs WHERE student_id = ? ORDER BY work_date DESC, id DESC LIMIT 5",
        (user["id"],),
    ).fetchall()
    total_logs = conn.execute(
        "SELECT COUNT(*) AS n FROM work_logs WHERE student_id = ?",
        (user["id"],),
    ).fetchone()["n"]
    announcements_rows = conn.execute(
        "SELECT * FROM announcements ORDER BY id DESC LIMIT 3"
    ).fetchall()
    conn.close()

    verification = (
        "Verified"
        if any(row["verification_status"] == "Verified" for row in attendance_rows)
        else "Needs review"
    )

    body = render_template_string(
        """
        <div class="hero">
            <div>
                <h1>Hello, {{ u.full_name }} 👋</h1>
                <p>Keep your OJT records updated and verified.</p>
            </div>
            <div class="hero-stat">
                <span>OJT Progress</span>
                <strong>{{ progress }}%</strong>
            </div>
        </div>

        <div class="grid stats">
            <div class="card">
                <span class="stat-icon">◷</span>
                <div class="stat-label">Completed Hours</div>
                <div class="stat-value">{{ hours }}h</div>
                <div class="progress"><span style="width:{{ progress }}%"></span></div>
            </div>
            <div class="card">
                <span class="stat-icon">✓</span>
                <div class="stat-label">Work Logs</div>
                <div class="stat-value">{{ total_logs }}</div>
                <span class="badge blue">Keep logging</span>
            </div>
            <div class="card">
                <span class="stat-icon">▣</span>
                <div class="stat-label">Placement</div>
                <div class="stat-value" style="font-size:18px">{{ placement.company_name if placement else 'Not assigned' }}</div>
            </div>
            <div class="card">
                <span class="stat-icon">!</span>
                <div class="stat-label">Verification</div>
                <div class="stat-value" style="font-size:18px">{{ verification }}</div>
            </div>
        </div>

        <div class="grid two">
            <div>
                <div class="section-title">
                    <h3>Recent attendance</h3>
                    <a class="btn secondary" href="{{ url_for('student_attendance') }}">View all</a>
                </div>
                <div class="card">
                    <div class="table-wrap">
                        <table>
                            <tr><th>Date</th><th>Time In</th><th>Time Out</th><th>Location</th><th>Status</th></tr>
                            {% for a in attendance_rows %}
                            <tr>
                                <td>{{ a.work_date }}</td>
                                <td>{{ a.time_in[11:16] if a.time_in else '—' }}</td>
                                <td>{{ a.time_out[11:16] if a.time_out else '—' }}</td>
                                <td>{{ a.location_status or '—' }}</td>
                                <td><span class="badge {{ 'green' if a.verification_status == 'Verified' else 'orange' }}">{{ a.verification_status }}</span></td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" class="empty">No attendance yet.</td></tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>
            </div>

            <div>
                <div class="section-title"><h3>Latest updates</h3></div>
                <div class="card">
                    {% for a in announcements_rows %}
                    <div class="notice"><b>{{ a.title }}</b><div class="mini">{{ a.message }}</div></div>
                    {% else %}
                    <div class="empty">No announcements.</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="section-title"><h3>Recent Work Logs</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Date</th><th>Task</th><th>Hours</th><th>Status</th></tr>
                {% for log in recent_logs %}
                <tr>
                    <td>{{ log.work_date }}</td>
                    <td>{{ log.task }}</td>
                    <td>{{ log.hours }}</td>
                    <td><span class="badge {{ 'green' if log.status == 'Verified' else 'red' if log.status == 'Rejected' else 'orange' }}">{{ log.status }}</span></td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="empty">No work logs yet.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        u=user,
        placement=placement,
        hours=hours,
        progress=progress,
        total_logs=total_logs,
        attendance_rows=attendance_rows,
        announcements_rows=announcements_rows,
        recent_logs=recent_logs,
        verification=verification,
    )
    return page("Student Dashboard", body, user)


def monitoring_dashboard_view(user):
    conn = db()
    students = conn.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role = 'student'"
    ).fetchone()["n"]
    active = conn.execute(
        "SELECT COUNT(*) AS n FROM placements WHERE status = 'Active'"
    ).fetchone()["n"]
    pending = conn.execute(
        "SELECT COUNT(*) AS n FROM work_logs WHERE status = 'Pending'"
    ).fetchone()["n"]
    rows = conn.execute(
        """
        SELECT u.id, u.full_name, p.position, p.status, c.name AS company_name
        FROM users u
        JOIN placements p ON p.student_id = u.id
        JOIN companies c ON c.id = p.company_id
        WHERE u.role = 'student'
        ORDER BY u.full_name
        """
    ).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="hero">
            <div><h1>OJT Monitoring Center</h1><p>Monitor attendance, verified tasks, reports and student progress.</p></div>
            <div class="hero-stat"><span>Active Placements</span><strong>{{ active }}</strong></div>
        </div>
        <div class="grid stats">
            <div class="card"><div class="stat-label">Students</div><div class="stat-value">{{ students }}</div></div>
            <div class="card"><div class="stat-label">Active OJT</div><div class="stat-value">{{ active }}</div></div>
            <div class="card"><div class="stat-label">Pending Work Logs</div><div class="stat-value">{{ pending }}</div></div>
            <div class="card"><div class="stat-label">System Status</div><div class="stat-value"><span class="badge green">Operational</span></div></div>
        </div>
        <div class="section-title"><h3>Student Monitoring</h3><a class="btn" href="{{ url_for('monitoring') }}">Open Monitoring</a></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Student</th><th>Company</th><th>Position</th><th>Status</th></tr>
                {% for r in rows %}
                <tr><td>{{ r.full_name }}</td><td>{{ r.company_name }}</td><td>{{ r.position }}</td><td><span class="badge green">{{ r.status }}</span></td></tr>
                {% else %}
                <tr><td colspan="4" class="empty">No students found.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        students=students,
        active=active,
        pending=pending,
        rows=rows,
    )
    return page("Monitoring Dashboard", body, user)


def supervisor_dashboard_view(user):
    conn = db()
    rows = conn.execute(
        """
        SELECT
            u.full_name,
            COUNT(w.id) AS logs,
            COALESCE(SUM(CASE WHEN w.status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending
        FROM users u
        JOIN placements p ON p.student_id = u.id
        LEFT JOIN work_logs w ON w.student_id = u.id
        WHERE p.supervisor_id = ?
        GROUP BY u.id
        ORDER BY u.full_name
        """,
        (user["id"],),
    ).fetchall()
    company = conn.execute(
        "SELECT * FROM companies WHERE id = ?", (user["company_id"],)
    ).fetchone()
    conn.close()

    body = render_template_string(
        """
        <div class="hero">
            <div><h1>Supervisor Portal</h1><p>Verify student work and attendance from one place.</p></div>
            <div class="hero-stat"><span>Assigned Company</span><strong style="font-size:21px">{{ company.name if company else '—' }}</strong></div>
        </div>
        <div class="section-title"><h3>Assigned OJT Students</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Student</th><th>Work Logs</th><th>Pending</th><th>Action</th></tr>
                {% for r in rows %}
                <tr>
                    <td>{{ r.full_name }}</td>
                    <td>{{ r.logs }}</td>
                    <td><span class="badge {{ 'orange' if r.pending else 'green' }}">{{ r.pending }}</span></td>
                    <td><a class="btn secondary" href="{{ url_for('supervisor_logs', student=r.full_name) }}">Review</a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="empty">No assigned students.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
        company=company,
    )
    return page("Supervisor Dashboard", body, user)


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    role = str(user["role"]).strip().lower()
    if role == "student":
        return student_dashboard_view(user)
    if role in ("adviser", "admin"):
        return monitoring_dashboard_view(user)
    if role == "supervisor":
        return supervisor_dashboard_view(user)
    session.clear()
    flash("Your account role could not be recognized.", "error")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard_alias():
    return dashboard()

# =========================================================
# STUDENT
# =========================================================

@app.route("/student/attendance")
@role_required("student")
def student_attendance():
    user = current_user()
    conn = db()
    rows = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? ORDER BY work_date DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    placement = placement_for(user["id"])
    today = date.today().isoformat()
    today_row = next((row for row in rows if row["work_date"] == today), None)

    body = render_template_string(
        """
        <div class="grid two">
            <div class="card">
                <h3>Today's Attendance</h3>
                <p class="mini">GPS check-in helps confirm that you are at your registered OJT workplace.</p>
                <div class="checkin-box">
                    <div class="big-number">{{ today_row.time_in[11:16] if today_row and today_row.time_in else '—' }}</div>
                    <div class="mini">Time In</div>
                    <br>
                    <div class="actions" style="justify-content:center">
                        {% if not today_row or not today_row.time_in %}
                            <button class="btn" onclick="checkIn()">📍 Check In with GPS</button>
                        {% elif not today_row.time_out %}
                            <button class="btn green" onclick="checkOut()">✓ Check Out</button>
                        {% else %}
                            <span class="badge green">Day completed</span>
                        {% endif %}
                    </div>
                    <p id="gpsmsg" class="mini"></p>
                </div>
            </div>

            <div class="card">
                <h3>OJT Verification</h3>
                <div class="profile-row"><span>Company</span><b>{{ placement.company_name if placement else '—' }}</b></div>
                <div class="profile-row"><span>Geofence</span><b>{{ placement.geofence_m if placement and placement.geofence_m else 'Not set' }} m</b></div>
                <div class="profile-row"><span>Hours Completed</span><b>{{ hours }} / {{ placement.required_hours if placement else 0 }}</b></div>
                <div class="profile-row"><span>Progress</span><b>{{ progress }}%</b></div>
            </div>
        </div>

        <div class="section-title"><h3>Attendance History</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Date</th><th>Time In</th><th>Time Out</th><th>GPS</th><th>Verification</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.work_date }}</td>
                    <td>{{ row.time_in[11:19] if row.time_in else '—' }}</td>
                    <td>{{ row.time_out[11:19] if row.time_out else '—' }}</td>
                    <td>{{ row.distance_in|round(0) if row.distance_in is not none else '—' }} m</td>
                    <td><span class="badge {{ 'green' if row.verification_status == 'Verified' else 'orange' }}">{{ row.verification_status }}</span></td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="empty">No records yet.</td></tr>
                {% endfor %}
            </table>
        </div>

        <script>
        async function sendLocation(url) {
            const msg = document.getElementById('gpsmsg');
            msg.textContent = 'Requesting your location...';

            if (!navigator.geolocation) {
                msg.textContent = 'GPS is not supported by this browser.';
                return;
            }

            navigator.geolocation.getCurrentPosition(async position => {
                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({lat: position.coords.latitude, lng: position.coords.longitude})
                    });
                    const data = await response.json();
                    msg.textContent = data.message;
                    if (data.ok) setTimeout(() => location.reload(), 800);
                } catch (error) {
                    msg.textContent = 'Unable to save your attendance. Please try again.';
                }
            }, () => {
                msg.textContent = 'Location permission was denied. Please allow GPS and try again.';
            }, {enableHighAccuracy: true, timeout: 10000, maximumAge: 0});
        }

        function checkIn() { sendLocation('{{ url_for("checkin") }}'); }
        function checkOut() { sendLocation('{{ url_for("checkout") }}'); }
        </script>
        """,
        rows=rows,
        placement=placement,
        hours=total_hours(user["id"]),
        progress=progress_for(user["id"]),
        today_row=today_row,
    )
    return page("Attendance / DTR", body, user)


@app.post("/student/checkin")
@role_required("student")
def checkin():
    user = current_user()
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify(ok=False, message="GPS coordinates were not received.")

    placement = placement_for(user["id"])
    if not placement:
        return jsonify(ok=False, message="No OJT placement is assigned to your account.")

    today = date.today().isoformat()
    conn = db()
    existing = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND work_date = ?",
        (user["id"], today),
    ).fetchone()

    if existing and existing["time_in"]:
        conn.close()
        return jsonify(ok=False, message="You are already checked in today.")

    distance = (
        distance_m(lat, lng, placement["latitude"], placement["longitude"])
        if placement["latitude"] is not None and placement["longitude"] is not None
        else None
    )

    radius = int(placement["geofence_m"] or 150)
    if distance is None:
        location_status = "Pending company GPS setup"
        verification_status = "Pending"
    elif distance <= radius:
        location_status = f"Verified · {round(distance)}m from site"
        verification_status = "Verified"
    else:
        location_status = f"Outside site · {round(distance)}m away"
        verification_status = "Pending"

    timestamp = now()
    conn.execute(
        """
        INSERT INTO attendance(
            student_id, work_date, time_in, lat_in, lng_in, distance_in,
            location_status, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, work_date) DO UPDATE SET
            time_in = excluded.time_in,
            lat_in = excluded.lat_in,
            lng_in = excluded.lng_in,
            distance_in = excluded.distance_in,
            location_status = excluded.location_status,
            verification_status = excluded.verification_status
        """,
        (
            user["id"],
            today,
            timestamp,
            safe_float(lat),
            safe_float(lng),
            distance,
            location_status,
            verification_status,
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(ok=True, message="Check-in recorded. Your location and time were saved.")


@app.post("/student/checkout")
@role_required("student")
def checkout():
    user = current_user()
    today = date.today().isoformat()
    conn = db()
    row = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND work_date = ?",
        (user["id"], today),
    ).fetchone()

    if not row or not row["time_in"]:
        conn.close()
        return jsonify(ok=False, message="Please check in first.")
    if row["time_out"]:
        conn.close()
        return jsonify(ok=False, message="You are already checked out today.")

    conn.execute("UPDATE attendance SET time_out = ? WHERE id = ?", (now(), row["id"]))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message="Check-out recorded successfully.")


@app.route("/student/logs", methods=["GET", "POST"])
@role_required("student")
def student_logs():
    user = current_user()
    conn = db()

    if request.method == "POST":
        task = request.form.get("task", "").strip()
        evidence = request.form.get("evidence_note", "").strip()
        hours_value = request.form.get("hours", "0")
        hours = safe_float(hours_value, -1)

        if not task:
            flash("Please enter the task or activity.", "error")
        elif hours < 0 or hours > 24:
            flash("Hours must be between 0 and 24.", "error")
        else:
            conn.execute(
                """
                INSERT INTO work_logs(
                    student_id, work_date, task, hours, evidence_note, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], date.today().isoformat(), task, hours, evidence, "Pending", now()),
            )
            conn.commit()
            placement = placement_for(user["id"])
            if placement and placement["supervisor_id"]:
                notify(
                    placement["supervisor_id"],
                    "New Work Log",
                    f"{user['full_name']} submitted a work log for review.",
                )
            flash("Work log submitted for supervisor verification.", "success")
        conn.close()
        return redirect(url_for("student_logs"))

    rows = conn.execute(
        "SELECT * FROM work_logs WHERE student_id = ? ORDER BY work_date DESC, id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Daily Work Log</h3>
            <p class="mini">Describe what you actually worked on. Your supervisor will verify it.</p>
            <form method="post">
                <div class="form-grid">
                    <div class="field full">
                        <label>Task / Activity</label>
                        <textarea name="task" rows="4" required placeholder="Example: Assisted in troubleshooting desktop computers and installed required software."></textarea>
                    </div>
                    <div class="field">
                        <label>Hours for this task</label>
                        <input name="hours" type="number" min="0" max="24" step="0.5" value="8">
                    </div>
                    <div class="field">
                        <label>Evidence / Notes</label>
                        <input name="evidence_note" placeholder="Ticket number, output, task reference, etc.">
                    </div>
                </div>
                <br>
                <button class="btn" type="submit">Submit Work Log</button>
            </form>
        </div>

        <div class="section-title"><h3>My Work Logs</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Date</th><th>Task</th><th>Hours</th><th>Status</th><th>Supervisor Comment</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.work_date }}</td>
                    <td>{{ row.task }}</td>
                    <td>{{ row.hours }}</td>
                    <td><span class="badge {{ 'green' if row.status == 'Verified' else 'red' if row.status == 'Rejected' else 'orange' }}">{{ row.status }}</span></td>
                    <td>{{ row.supervisor_comment or '—' }}</td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="empty">No work logs yet.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
    )
    return page("Work Logs", body, user)


@app.route("/student/reports", methods=["GET", "POST"])
@role_required("student")
def student_reports():
    user = current_user()
    conn = db()

    if request.method == "POST":
        week_start = request.form.get("week_start", "").strip()
        week_end = request.form.get("week_end", "").strip()
        summary = request.form.get("summary", "").strip()
        challenges = request.form.get("challenges", "").strip()
        learnings = request.form.get("learnings", "").strip()

        if not week_start or not week_end or not summary:
            flash("Please complete the week dates and work summary.", "error")
        elif week_start > week_end:
            flash("Week End cannot be earlier than Week Start.", "error")
        else:
            conn.execute(
                """
                INSERT INTO weekly_reports(
                    student_id, week_start, week_end, summary,
                    challenges, learnings, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    week_start,
                    week_end,
                    summary,
                    challenges,
                    learnings,
                    "Submitted",
                    now(),
                ),
            )
            conn.commit()
            flash("Weekly report submitted.", "success")
        conn.close()
        return redirect(url_for("student_reports"))

    rows = conn.execute(
        "SELECT * FROM weekly_reports WHERE student_id = ? ORDER BY week_start DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    monday = date.today() - timedelta(days=date.today().weekday())
    sunday = monday + timedelta(days=6)

    body = render_template_string(
        """
        <div class="card">
            <h3>Submit Weekly Report</h3>
            <form method="post">
                <div class="form-grid">
                    <div class="field"><label>Week Start</label><input type="date" name="week_start" value="{{ monday }}" required></div>
                    <div class="field"><label>Week End</label><input type="date" name="week_end" value="{{ sunday }}" required></div>
                    <div class="field full"><label>Work Summary</label><textarea name="summary" rows="4" required placeholder="Summarize the tasks you completed this week."></textarea></div>
                    <div class="field"><label>Challenges</label><textarea name="challenges" rows="3"></textarea></div>
                    <div class="field"><label>Learnings</label><textarea name="learnings" rows="3"></textarea></div>
                </div>
                <br>
                <button class="btn" type="submit">Submit Report</button>
            </form>
        </div>

        <div class="section-title"><h3>Report History</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Week</th><th>Status</th><th>Adviser Comment</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.week_start }} → {{ row.week_end }}</td>
                    <td><span class="badge {{ 'green' if row.status == 'Approved' else 'orange' if row.status == 'Submitted' else 'red' }}">{{ row.status }}</span></td>
                    <td>{{ row.adviser_comment or '—' }}</td>
                </tr>
                {% else %}
                <tr><td colspan="3" class="empty">No reports submitted.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
        monday=monday.isoformat(),
        sunday=sunday.isoformat(),
    )
    return page("Weekly Reports", body, user)


@app.route("/student/evaluation")
@role_required("student")
def student_evaluation():
    user = current_user()
    placement = placement_for(user["id"])
    conn = db()
    evaluations = []
    if placement:
        evaluations = conn.execute(
            """
            SELECT e.*, u.full_name AS evaluator
            FROM evaluations e
            JOIN users u ON u.id = e.evaluator_id
            WHERE e.placement_id = ?
            ORDER BY e.id DESC
            """,
            (placement["id"],),
        ).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>OJT Evaluation</h3>
            <p class="mini">Evaluations are completed by your authorized supervisor or adviser.</p>
            {% for e in evaluations %}
                <div class="grid three">
                    <div><div class="stat-label">Attendance</div><div class="stat-value">{{ e.attendance_rating }}/5</div></div>
                    <div><div class="stat-label">Work Quality</div><div class="stat-value">{{ e.work_quality }}/5</div></div>
                    <div><div class="stat-label">Professionalism</div><div class="stat-value">{{ e.professionalism_rating }}/5</div></div>
                </div>
                <div class="notice"><b>{{ e.evaluator }}</b><br>{{ e.comment or 'No comment.' }}</div>
            {% else %}
                <div class="empty">No evaluation has been submitted yet.</div>
            {% endfor %}
        </div>
        """,
        evaluations=evaluations,
    )
    return page("Evaluation", body, user)

# =========================================================
# SUPERVISOR
# =========================================================

@app.route("/supervisor/logs", methods=["GET", "POST"])
@role_required("supervisor", "admin")
def supervisor_logs():
    user = current_user()
    student_filter = request.args.get("student", "").strip()
    conn = db()

    if request.method == "POST":
        log_id = request.form.get("log_id")
        status = request.form.get("status", "")
        comment = request.form.get("comment", "").strip()

        log = conn.execute(
            """
            SELECT w.*, p.supervisor_id
            FROM work_logs w
            JOIN placements p ON p.student_id = w.student_id
            WHERE w.id = ?
            """,
            (log_id,),
        ).fetchone()

        if status not in {"Verified", "Rejected"}:
            flash("Invalid work log status.", "error")
        elif log and (user["role"] == "admin" or log["supervisor_id"] == user["id"]):
            conn.execute(
                "UPDATE work_logs SET status = ?, supervisor_comment = ? WHERE id = ?",
                (status, comment, log_id),
            )
            conn.commit()
            notify(log["student_id"], "Work Log Updated", f"Your work log was marked {status}.")
            flash("Work log updated.", "success")
        else:
            flash("You are not allowed to update this work log.", "error")

        conn.close()
        return redirect(url_for("supervisor_logs", student=student_filter))

    query = """
        SELECT w.*, u.full_name AS student_name, c.name AS company_name
        FROM work_logs w
        JOIN users u ON u.id = w.student_id
        JOIN placements p ON p.student_id = u.id
        JOIN companies c ON c.id = p.company_id
        WHERE 1 = 1
    """
    args = []

    if user["role"] == "supervisor":
        query += " AND p.supervisor_id = ?"
        args.append(user["id"])

    if student_filter:
        query += " AND u.full_name LIKE ?"
        args.append(f"%{student_filter}%")

    query += " ORDER BY w.work_date DESC, w.id DESC"
    rows = conn.execute(query, args).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <form>
                <div class="actions">
                    <input name="student" value="{{ student_filter }}" placeholder="Search student" style="padding:11px;border:1px solid #d8dfeb;border-radius:10px">
                    <button class="btn" type="submit">Search</button>
                </div>
            </form>
        </div>

        <div class="section-title"><h3>Work Log Verification</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Date</th><th>Student</th><th>Task</th><th>Hours</th><th>Status</th><th>Action</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.work_date }}</td>
                    <td>{{ row.student_name }}</td>
                    <td>{{ row.task }}</td>
                    <td>{{ row.hours }}</td>
                    <td><span class="badge {{ 'green' if row.status == 'Verified' else 'red' if row.status == 'Rejected' else 'orange' }}">{{ row.status }}</span></td>
                    <td>
                        <form method="post" class="actions">
                            <input type="hidden" name="log_id" value="{{ row.id }}">
                            <input name="comment" placeholder="Comment" style="width:130px;padding:8px;border:1px solid #ddd;border-radius:8px">
                            <button name="status" value="Verified" class="btn green" type="submit">Verify</button>
                            <button name="status" value="Rejected" class="btn red" type="submit">Reject</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="6" class="empty">No work logs found.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
        student_filter=student_filter,
    )
    return page("Verify Work Logs", body, user)


@app.route("/supervisor/attendance")
@role_required("supervisor", "admin")
def supervisor_attendance():
    user = current_user()
    conn = db()
    query = """
        SELECT a.*, u.full_name AS student_name
        FROM attendance a
        JOIN users u ON u.id = a.student_id
        JOIN placements p ON p.student_id = u.id
        WHERE 1 = 1
    """
    args = []
    if user["role"] == "supervisor":
        query += " AND p.supervisor_id = ?"
        args.append(user["id"])
    query += " ORDER BY a.work_date DESC"

    rows = conn.execute(query, args).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Attendance Verification</h3>
            <p class="mini">GPS status is evidence, not absolute proof. Supervisors should still review attendance.</p>
        </div>
        <div class="card table-wrap">
            <table>
                <tr><th>Date</th><th>Student</th><th>Time In</th><th>Time Out</th><th>Distance</th><th>GPS Status</th><th>Review</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.work_date }}</td>
                    <td>{{ row.student_name }}</td>
                    <td>{{ row.time_in[11:16] if row.time_in else '—' }}</td>
                    <td>{{ row.time_out[11:16] if row.time_out else '—' }}</td>
                    <td>{{ row.distance_in|round(0) if row.distance_in is not none else '—' }} m</td>
                    <td><span class="badge {{ 'green' if row.location_status and row.location_status.startswith('Verified') else 'orange' }}">{{ row.location_status or '—' }}</span></td>
                    <td><span class="badge {{ 'green' if row.verification_status == 'Verified' else 'orange' }}">{{ row.verification_status }}</span></td>
                </tr>
                {% else %}
                <tr><td colspan="7" class="empty">No attendance records.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
    )
    return page("Verify Attendance", body, user)


@app.route("/supervisor/evaluation", methods=["GET", "POST"])
@role_required("supervisor", "admin")
def supervisor_evaluation():
    user = current_user()
    conn = db()

    if request.method == "POST":
        placement_id = request.form.get("placement_id")
        ratings = {
            "attendance_rating": min(5, max(1, safe_float(request.form.get("attendance_rating"), 0))),
            "work_quality": min(5, max(1, safe_float(request.form.get("work_quality"), 0))),
            "communication_rating": min(5, max(1, safe_float(request.form.get("communication_rating"), 0))),
            "professionalism_rating": min(5, max(1, safe_float(request.form.get("professionalism_rating"), 0))),
            "initiative_rating": min(5, max(1, safe_float(request.form.get("initiative_rating"), 0))),
        }
        comment = request.form.get("comment", "").strip()

        placement = conn.execute(
            "SELECT * FROM placements WHERE id = ?", (placement_id,)
        ).fetchone()

        if placement and (
            user["role"] == "admin" or placement["supervisor_id"] == user["id"]
        ):
            conn.execute(
                """
                INSERT INTO evaluations(
                    placement_id, evaluator_id, attendance_rating,
                    work_quality, communication_rating, professionalism_rating,
                    initiative_rating, comment, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(placement_id, evaluator_id) DO UPDATE SET
                    attendance_rating = excluded.attendance_rating,
                    work_quality = excluded.work_quality,
                    communication_rating = excluded.communication_rating,
                    professionalism_rating = excluded.professionalism_rating,
                    initiative_rating = excluded.initiative_rating,
                    comment = excluded.comment,
                    created_at = excluded.created_at
                """,
                (
                    placement_id,
                    user["id"],
                    ratings["attendance_rating"],
                    ratings["work_quality"],
                    ratings["communication_rating"],
                    ratings["professionalism_rating"],
                    ratings["initiative_rating"],
                    comment,
                    now(),
                ),
            )
            conn.commit()
            notify(
                placement["student_id"],
                "OJT Evaluation Updated",
                "Your supervisor submitted or updated an evaluation.",
            )
            flash("Evaluation saved.", "success")
        else:
            flash("You are not allowed to evaluate this placement.", "error")

        conn.close()
        return redirect(url_for("supervisor_evaluation"))

    query = """
        SELECT p.id, p.student_id, u.full_name AS student_name, c.name AS company_name
        FROM placements p
        JOIN users u ON u.id = p.student_id
        JOIN companies c ON c.id = p.company_id
        WHERE 1 = 1
    """
    args = []
    if user["role"] == "supervisor":
        query += " AND p.supervisor_id = ?"
        args.append(user["id"])

    placements = conn.execute(query, args).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Supervisor Evaluation</h3>
            {% if placements %}
            <form method="post">
                <div class="form-grid">
                    <div class="field"><label>Student / Placement</label><select name="placement_id" required>{% for p in placements %}<option value="{{ p.id }}">{{ p.student_name }} · {{ p.company_name }}</option>{% endfor %}</select></div>
                    <div class="field"><label>Attendance (1-5)</label><input name="attendance_rating" type="number" min="1" max="5" step="0.1" value="5" required></div>
                    <div class="field"><label>Work Quality (1-5)</label><input name="work_quality" type="number" min="1" max="5" step="0.1" value="5" required></div>
                    <div class="field"><label>Communication (1-5)</label><input name="communication_rating" type="number" min="1" max="5" step="0.1" value="5" required></div>
                    <div class="field"><label>Professionalism (1-5)</label><input name="professionalism_rating" type="number" min="1" max="5" step="0.1" value="5" required></div>
                    <div class="field"><label>Initiative (1-5)</label><input name="initiative_rating" type="number" min="1" max="5" step="0.1" value="5" required></div>
                    <div class="field full"><label>Comments</label><textarea name="comment" rows="4"></textarea></div>
                </div>
                <br><button class="btn" type="submit">Save Evaluation</button>
            </form>
            {% else %}
            <div class="empty">No assigned student placements are available.</div>
            {% endif %}
        </div>
        """,
        placements=placements,
    )
    return page("Evaluation", body, user)

# =========================================================
# ADVISER / ADMIN MONITORING
# =========================================================

@app.route("/monitoring")
@role_required("adviser", "admin")
def monitoring():
    conn = db()
    rows = conn.execute(
        """
        SELECT u.id, u.full_name, c.name AS company_name,
               p.position, p.required_hours, p.status
        FROM users u
        JOIN placements p ON p.student_id = u.id
        JOIN companies c ON c.id = p.company_id
        WHERE u.role = 'student'
        ORDER BY u.full_name
        """
    ).fetchall()

    data = []
    for row in rows:
        hours = total_hours(row["id"])
        required = max(1, int(row["required_hours"] or 0))
        progress = min(100, round((hours / required) * 100))
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM work_logs WHERE student_id = ? AND status = 'Pending'",
            (row["id"],),
        ).fetchone()["n"]
        data.append((row, hours, progress, pending))
    conn.close()

    body = render_template_string(
        """
        <div class="card"><h3>Student Monitoring</h3><p class="mini">Progress is based on recorded OJT hours. It does not guarantee physical presence.</p></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Student</th><th>Company</th><th>Hours</th><th>Progress</th><th>Pending Logs</th><th>Status</th></tr>
                {% for row, hours, progress, pending in data %}
                <tr>
                    <td><b>{{ row.full_name }}</b></td>
                    <td>{{ row.company_name }}</td>
                    <td>{{ hours }} / {{ row.required_hours }}h</td>
                    <td style="min-width:160px"><b>{{ progress }}%</b><div class="progress"><span style="width:{{ progress }}%"></span></div></td>
                    <td><span class="badge {{ 'orange' if pending else 'green' }}">{{ pending }}</span></td>
                    <td><span class="badge green">{{ row.status }}</span></td>
                </tr>
                {% else %}
                <tr><td colspan="6" class="empty">No students found.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        data=data,
    )
    return page("Student Monitoring", body, current_user())


@app.route("/reports-review", methods=["GET", "POST"])
@role_required("adviser", "admin")
def reports_review():
    user = current_user()
    conn = db()

    if request.method == "POST":
        report_id = request.form.get("report_id")
        status = request.form.get("status")
        comment = request.form.get("comment", "").strip()

        report = conn.execute(
            "SELECT * FROM weekly_reports WHERE id = ?", (report_id,)
        ).fetchone()

        if status not in {"Approved", "Needs Revision"}:
            flash("Invalid report status.", "error")
        elif report:
            conn.execute(
                "UPDATE weekly_reports SET status = ?, adviser_comment = ? WHERE id = ?",
                (status, comment, report_id),
            )
            conn.commit()
            notify(
                report["student_id"],
                "Weekly Report Reviewed",
                f"Your weekly report was marked {status}.",
            )
            flash("Report updated.", "success")
        else:
            flash("Report not found.", "error")

        conn.close()
        return redirect(url_for("reports_review"))

    rows = conn.execute(
        """
        SELECT w.*, u.full_name AS student_name
        FROM weekly_reports w
        JOIN users u ON u.id = w.student_id
        ORDER BY w.created_at DESC
        """
    ).fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card table-wrap">
            <table>
                <tr><th>Student</th><th>Week</th><th>Summary</th><th>Status</th><th>Review</th></tr>
                {% for row in rows %}
                <tr>
                    <td>{{ row.student_name }}</td>
                    <td>{{ row.week_start }} → {{ row.week_end }}</td>
                    <td style="max-width:320px">{{ row.summary }}</td>
                    <td><span class="badge {{ 'green' if row.status == 'Approved' else 'red' if row.status == 'Needs Revision' else 'orange' }}">{{ row.status }}</span></td>
                    <td>
                        <form method="post" class="actions">
                            <input type="hidden" name="report_id" value="{{ row.id }}">
                            <input name="comment" placeholder="Comment" style="padding:8px;border:1px solid #ddd;border-radius:8px">
                            <button class="btn green" name="status" value="Approved" type="submit">Approve</button>
                            <button class="btn red" name="status" value="Needs Revision" type="submit">Revision</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="empty">No reports.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
    )
    return page("Weekly Report Review", body, user)

# =========================================================
# ADMIN
# =========================================================

@app.route("/admin/users", methods=["GET", "POST"])
@role_required("admin")
def users():
    conn = db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "student")
        email = request.form.get("email", "").strip()
        company_id = request.form.get("company_id") or None

        if not username or not password or not full_name:
            flash("Full Name, Username, and Password are required.", "error")
        elif role not in {"student", "adviser", "supervisor", "admin"}:
            flash("Invalid account role.", "error")
        else:
            try:
                conn.execute(
                    """
                    INSERT INTO users(username, password_hash, full_name, role, email, company_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        full_name,
                        role,
                        email,
                        company_id,
                        now(),
                    ),
                )
                conn.commit()
                flash("User account created.", "success")
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")

        conn.close()
        return redirect(url_for("users"))

    rows = conn.execute(
        """
        SELECT u.*, c.name AS company_name
        FROM users u
        LEFT JOIN companies c ON c.id = u.company_id
        ORDER BY u.role, u.full_name
        """
    ).fetchall()
    companies_rows = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Create Account</h3>
            <form method="post">
                <div class="form-grid">
                    <div class="field"><label>Full Name</label><input name="full_name" required></div>
                    <div class="field"><label>Username</label><input name="username" required></div>
                    <div class="field"><label>Password</label><input name="password" type="password" required></div>
                    <div class="field"><label>Email</label><input name="email" type="email"></div>
                    <div class="field"><label>Role</label><select name="role"><option value="student">Student</option><option value="adviser">Adviser</option><option value="supervisor">Supervisor</option><option value="admin">Admin</option></select></div>
                    <div class="field"><label>Company (optional)</label><select name="company_id"><option value="">None</option>{% for c in companies_rows %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}</select></div>
                </div>
                <br><button class="btn" type="submit">Create Account</button>
            </form>
        </div>

        <div class="section-title"><h3>Accounts</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Name</th><th>Username</th><th>Role</th><th>Company</th><th>Status</th></tr>
                {% for row in rows %}
                <tr><td>{{ row.full_name }}</td><td>{{ row.username }}</td><td>{{ row.role }}</td><td>{{ row.company_name or '—' }}</td><td><span class="badge {{ 'green' if row.active else 'red' }}">{{ 'Active' if row.active else 'Inactive' }}</span></td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
        companies_rows=companies_rows,
    )
    return page("User Management", body, current_user())


@app.route("/admin/companies", methods=["GET", "POST"])
@role_required("admin")
def companies():
    conn = db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        lat_text = request.form.get("latitude", "").strip()
        lng_text = request.form.get("longitude", "").strip()
        radius_text = request.form.get("geofence_m", "150").strip()

        if not name or not address:
            flash("Company Name and Address are required.", "error")
        else:
            latitude = safe_float(lat_text, None) if lat_text else None
            longitude = safe_float(lng_text, None) if lng_text else None
            radius = int(safe_float(radius_text, 150))
            radius = max(20, radius)
            conn.execute(
                "INSERT INTO companies(name, address, latitude, longitude, geofence_m) VALUES (?, ?, ?, ?, ?)",
                (name, address, latitude, longitude, radius),
            )
            conn.commit()
            flash("Company added.", "success")

        conn.close()
        return redirect(url_for("companies"))

    rows = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Add OJT Company</h3>
            <p class="mini">Enter the company's GPS coordinates so student geofencing can work. Coordinates can be obtained from Google Maps.</p>
            <form method="post">
                <div class="form-grid">
                    <div class="field"><label>Company Name</label><input name="name" required></div>
                    <div class="field"><label>Address</label><input name="address" required></div>
                    <div class="field"><label>Latitude</label><input name="latitude" type="number" step="any"></div>
                    <div class="field"><label>Longitude</label><input name="longitude" type="number" step="any"></div>
                    <div class="field"><label>Allowed Radius (meters)</label><input name="geofence_m" type="number" min="20" value="150"></div>
                </div>
                <br><button class="btn" type="submit">Add Company</button>
            </form>
        </div>

        <div class="section-title"><h3>Registered Companies</h3></div>
        <div class="card table-wrap">
            <table>
                <tr><th>Company</th><th>Address</th><th>Coordinates</th><th>Radius</th></tr>
                {% for row in rows %}
                <tr><td>{{ row.name }}</td><td>{{ row.address }}</td><td>{{ row.latitude or 'Not set' }}, {{ row.longitude or 'Not set' }}</td><td>{{ row.geofence_m }}m</td></tr>
                {% else %}
                <tr><td colspan="4" class="empty">No companies registered.</td></tr>
                {% endfor %}
            </table>
        </div>
        """,
        rows=rows,
    )
    return page("Company Management", body, current_user())


@app.route("/admin/announcements", methods=["GET", "POST"])
@role_required("admin")
def announcements():
    conn = db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        if not title or not message:
            flash("Title and Message are required.", "error")
        else:
            conn.execute(
                "INSERT INTO announcements(title, message, created_at) VALUES (?, ?, ?)",
                (title, message, now()),
            )
            conn.commit()
            flash("Announcement published.", "success")
        conn.close()
        return redirect(url_for("announcements"))

    rows = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    conn.close()

    body = render_template_string(
        """
        <div class="card">
            <h3>Publish Announcement</h3>
            <form method="post">
                <div class="field"><label>Title</label><input name="title" required></div><br>
                <div class="field"><label>Message</label><textarea name="message" rows="4" required></textarea></div><br>
                <button class="btn" type="submit">Publish</button>
            </form>
        </div>

        <div class="section-title"><h3>Announcements</h3></div>
        <div class="card">
            {% for a in rows %}
                <div class="notice"><b>{{ a.title }}</b><br>{{ a.message }}<div class="mini">{{ a.created_at }}</div></div>
            {% else %}
                <div class="empty">No announcements.</div>
            {% endfor %}
        </div>
        """,
        rows=rows,
    )
    return page("Announcements", body, current_user())

# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(_error):
    user = current_user()
    if user:
        body = """
        <div class="card empty">
            <h3>404</h3>
            <p>The page you requested was not found.</p>
            <a class="btn" href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        </div>
        """
        return page("Page Not Found", render_template_string(body), user), 404
    return redirect(url_for("login"))


@app.errorhandler(413)
def too_large(_error):
    return "File too large.", 413

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
