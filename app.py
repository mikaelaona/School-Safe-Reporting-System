from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "smart-ojt-secret-key-change-this"

DATABASE = "ojt_system.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            student_id TEXT,
            company TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            company TEXT,
            position TEXT,
            required_hours INTEGER DEFAULT 600,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            check_in TEXT,
            check_out TEXT,
            location TEXT,
            status TEXT DEFAULT 'Present',
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            task TEXT,
            evidence TEXT,
            status TEXT DEFAULT 'Pending',
            supervisor_comment TEXT,
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            week TEXT,
            summary TEXT,
            hours INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            adviser_comment TEXT,
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            supervisor_id INTEGER,
            attendance_score INTEGER DEFAULT 0,
            performance_score INTEGER DEFAULT 0,
            attitude_score INTEGER DEFAULT 0,
            skills_score INTEGER DEFAULT 0,
            comments TEXT,
            date TEXT,
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            created_at TEXT,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # -----------------------------------------------------
    # DEMO ACCOUNTS
    # -----------------------------------------------------

    demo_users = [
        (
            "Miah Villanueva",
            "student@ojt.com",
            "student123",
            "student",
            "2026-001",
            "ABC Technology Solutions"
        ),
        (
            "Juan Adviser",
            "adviser@ojt.com",
            "adviser123",
            "adviser",
            "",
            ""
        ),
        (
            "Maria Supervisor",
            "company@ojt.com",
            "company123",
            "company",
            "",
            "ABC Technology Solutions"
        ),
        (
            "System Administrator",
            "admin@ojt.com",
            "admin123",
            "admin",
            "",
            ""
        )
    ]

    for user in demo_users:
        existing = cur.execute(
            "SELECT id FROM users WHERE email = ?",
            (user[1],)
        ).fetchone()

        if not existing:
            cur.execute("""
                INSERT INTO users
                (name, email, password, role, student_id, company)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user[0],
                user[1],
                generate_password_hash(user[2]),
                user[3],
                user[4],
                user[5]
            ))

    conn.commit()

    # -----------------------------------------------------
    # DEMO STUDENT APPLICATION
    # -----------------------------------------------------

    student = cur.execute(
        "SELECT id FROM users WHERE email = 'student@ojt.com'"
    ).fetchone()

    if student:
        existing_app = cur.execute(
            "SELECT id FROM applications WHERE student_id = ?",
            (student["id"],)
        ).fetchone()

        if not existing_app:
            cur.execute("""
                INSERT INTO applications
                (student_id, company, position, required_hours,
                 start_date, end_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                student["id"],
                "ABC Technology Solutions",
                "IT Intern",
                600,
                "2026-08-01",
                "2026-11-30",
                "Approved"
            ))

    conn.commit()
    conn.close()


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(role=None):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("You are not authorized to access this page.", "error")
                return redirect(url_for("dashboard"))

            return func(*args, **kwargs)

        return wrapper

    return decorator


# =========================================================
# HELPERS
# =========================================================

def current_user():
    if "user_id" not in session:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return user


def add_notification(user_id, message):
    conn = get_db()

    conn.execute("""
        INSERT INTO notifications
        (user_id, message, created_at)
        VALUES (?, ?, ?)
    """, (
        user_id,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()


def calculate_progress(student_id):

    conn = get_db()

    # Attendance
    attendance = conn.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id = ?
        AND status = 'Present'
    """, (student_id,)).fetchone()["total"]

    attendance_score = min(attendance / 20 * 100, 100)

    # Verified work logs
    logs_total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE student_id = ?
    """, (student_id,)).fetchone()["total"]

    logs_verified = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE student_id = ?
        AND status = 'Verified'
    """, (student_id,)).fetchone()["total"]

    if logs_total:
        work_score = logs_verified / logs_total * 100
    else:
        work_score = 0

    # Weekly reports
    reports_total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM weekly_reports
        WHERE student_id = ?
    """, (student_id,)).fetchone()["total"]

    reports_approved = conn.execute("""
        SELECT COUNT(*) AS total
        FROM weekly_reports
        WHERE student_id = ?
        AND status = 'Approved'
    """, (student_id,)).fetchone()["total"]

    if reports_total:
        report_score = reports_approved / reports_total * 100
    else:
        report_score = 0

    # Evaluation
    evaluation = conn.execute("""
        SELECT
        AVG(attendance_score) AS attendance_score,
        AVG(performance_score) AS performance_score,
        AVG(attitude_score) AS attitude_score,
        AVG(skills_score) AS skills_score
        FROM evaluations
        WHERE student_id = ?
    """, (student_id,)).fetchone()

    if evaluation["performance_score"] is not None:

        evaluation_score = (
            evaluation["attendance_score"] +
            evaluation["performance_score"] +
            evaluation["attitude_score"] +
            evaluation["skills_score"]
        ) / 4 * 10

    else:
        evaluation_score = 0

    progress = (
        attendance_score * 0.30 +
        work_score * 0.25 +
        report_score * 0.20 +
        evaluation_score * 0.25
    )

    conn.close()

    return round(progress)


# =========================================================
# BASE HTML
# =========================================================

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{{ title or "Smart OJT" }}</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f7fb;
    color: #172033;
}

.sidebar {
    position: fixed;
    left: 0;
    top: 0;
    width: 250px;
    height: 100vh;
    background: #0757b8;
    color: white;
    padding: 25px 16px;
    overflow-y: auto;
}

.logo {
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 35px;
    padding-left: 12px;
}

.logo span {
    opacity: .75;
    font-size: 13px;
    display: block;
    margin-top: 4px;
}

.nav-title {
    font-size: 11px;
    opacity: .65;
    padding: 10px 12px;
    text-transform: uppercase;
}

.sidebar a {
    display: block;
    color: white;
    text-decoration: none;
    padding: 12px;
    border-radius: 9px;
    margin-bottom: 5px;
    font-size: 14px;
}

.sidebar a:hover {
    background: rgba(255,255,255,.15);
}

.logout {
    margin-top: 25px;
    background: rgba(0,0,0,.15);
}

.main {
    margin-left: 250px;
    padding: 30px;
}

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
}

.topbar h1 {
    margin: 0;
    font-size: 26px;
}

.user-box {
    background: white;
    padding: 10px 15px;
    border-radius: 10px;
    box-shadow: 0 3px 12px rgba(0,0,0,.05);
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    margin-bottom: 25px;
}

.card {
    background: white;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 3px 15px rgba(0,0,0,.06);
}

.card-title {
    color: #718096;
    font-size: 13px;
    margin-bottom: 10px;
}

.card-value {
    font-size: 27px;
    font-weight: bold;
}

.blue {
    color: #0757b8;
}

.green {
    color: #16a34a;
}

.orange {
    color: #ea580c;
}

.red {
    color: #dc2626;
}

.progress {
    height: 12px;
    background: #e7edf5;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 12px;
}

.progress-bar {
    height: 100%;
    background: #0757b8;
}

.section {
    background: white;
    border-radius: 15px;
    padding: 22px;
    margin-bottom: 22px;
    box-shadow: 0 3px 15px rgba(0,0,0,.05);
}

.section h2 {
    margin-top: 0;
    font-size: 19px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    background: #f4f7fb;
    text-align: left;
    padding: 12px;
    font-size: 13px;
}

td {
    padding: 12px;
    border-bottom: 1px solid #edf0f4;
    font-size: 13px;
}

.badge {
    padding: 5px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: bold;
    display: inline-block;
}

.badge-green {
    background: #dcfce7;
    color: #15803d;
}

.badge-yellow {
    background: #fef3c7;
    color: #b45309;
}

.badge-red {
    background: #fee2e2;
    color: #b91c1c;
}

.badge-blue {
    background: #dbeafe;
    color: #1d4ed8;
}

.btn {
    display: inline-block;
    border: none;
    background: #0757b8;
    color: white;
    padding: 11px 16px;
    border-radius: 8px;
    cursor: pointer;
    text-decoration: none;
    font-size: 13px;
}

.btn:hover {
    background: #064a9d;
}

.btn-green {
    background: #16a34a;
}

.btn-red {
    background: #dc2626;
}

.btn-gray {
    background: #64748b;
}

input, select, textarea {
    width: 100%;
    padding: 11px;
    border: 1px solid #d9e0e8;
    border-radius: 8px;
    margin-top: 6px;
    margin-bottom: 15px;
    font-family: inherit;
}

textarea {
    min-height: 110px;
    resize: vertical;
}

label {
    font-size: 13px;
    font-weight: bold;
}

.form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
}

.alert {
    padding: 12px 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    background: #fee2e2;
    color: #991b1b;
}

.success {
    background: #dcfce7;
    color: #166534;
}

.login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg,#0757b8,#0c77e8);
}

.login-card {
    width: 400px;
    max-width: 92%;
    background: white;
    padding: 35px;
    border-radius: 20px;
    box-shadow: 0 15px 50px rgba(0,0,0,.2);
}

.login-logo {
    text-align: center;
    margin-bottom: 25px;
}

.login-logo h1 {
    color: #0757b8;
    margin-bottom: 5px;
}

.login-logo p {
    color: #718096;
    font-size: 13px;
}

.profile {
    display: flex;
    align-items: center;
    gap: 18px;
}

.avatar {
    width: 65px;
    height: 65px;
    background: #dbeafe;
    color: #0757b8;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    font-weight: bold;
}

@media(max-width: 900px) {

    .sidebar {
        width: 210px;
    }

    .main {
        margin-left: 210px;
    }

    .card-grid {
        grid-template-columns: repeat(2,1fr);
    }

}

@media(max-width: 650px) {

    .sidebar {
        position: relative;
        width: 100%;
        height: auto;
    }

    .main {
        margin-left: 0;
        padding: 18px;
    }

    .card-grid {
        grid-template-columns: 1fr;
    }

    .form-grid {
        grid-template-columns: 1fr;
    }

    .topbar {
        display: block;
    }

    .user-box {
        margin-top: 10px;
    }

    table {
        min-width: 600px;
    }

    .section {
        overflow-x: auto;
    }

}

</style>

</head>

<body>

{% if session.get('user_id') %}

<div class="sidebar">

    <div class="logo">
        Smart OJT
        <span>Management & Monitoring</span>
    </div>

    <div class="nav-title">Main</div>

    <a href="{{ url_for('dashboard') }}">📊 Dashboard</a>

    {% if session.get('role') == 'student' %}

        <a href="{{ url_for('profile') }}">👤 My Profile</a>
        <a href="{{ url_for('application') }}">📝 OJT Application</a>
        <a href="{{ url_for('attendance') }}">⏱️ Attendance / DTR</a>
        <a href="{{ url_for('work_logs') }}">📋 Daily Work Logs</a>
        <a href="{{ url_for('weekly_reports') }}">📄 Weekly Reports</a>
        <a href="{{ url_for('student_evaluation') }}">⭐ Evaluation</a>
        <a href="{{ url_for('notifications') }}">🔔 Notifications</a>

    {% elif session.get('role') == 'company' %}

        <a href="{{ url_for('company_students') }}">👨‍🎓 Students</a>
        <a href="{{ url_for('verify_logs') }}">📋 Work Logs</a>
        <a href="{{ url_for('company_evaluation') }}">⭐ Evaluation</a>
        <a href="{{ url_for('notifications') }}">🔔 Notifications</a>

    {% elif session.get('role') == 'adviser' %}

        <a href="{{ url_for('monitor_students') }}">📊 Student Monitoring</a>
        <a href="{{ url_for('adviser_reports') }}">📄 Weekly Reports</a>
        <a href="{{ url_for('notifications') }}">🔔 Notifications</a>

    {% elif session.get('role') == 'admin' %}

        <a href="{{ url_for('admin_students') }}">👨‍🎓 Students</a>
        <a href="{{ url_for('admin_users') }}">👥 Users</a>
        <a href="{{ url_for('admin_reports') }}">📊 System Reports</a>

    {% endif %}

    <a class="logout" href="{{ url_for('logout') }}">🚪 Logout</a>

</div>

{% endif %}

<div class="main">

{% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
        <div class="alert {% if category == 'success' %}success{% endif %}">
            {{ message }}
        </div>
    {% endfor %}
{% endwith %}

{{ content|safe }}

</div>

</body>
</html>
"""


def page(title, body):
    user = current_user()

    return render_template_string(
        BASE,
        title=title,
        content=render_template_string(
            body,
            user=user,
            session=session
        )
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    html = """
    <div class="login-page">

        <div class="login-card">

            <div class="login-logo">
                <h1>Smart OJT</h1>
                <p>Management & Monitoring System</p>
            </div>

            <form method="POST">

                <label>Email</label>
                <input
                    type="email"
                    name="email"
                    placeholder="Enter your email"
                    required
                >

                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    placeholder="Enter your password"
                    required
                >

                <button class="btn" style="width:100%;">
                    Login
                </button>

            </form>

            <div style="margin-top:20px;font-size:12px;color:#64748b;">
                <b>Demo Accounts</b><br><br>

                Student: student@ojt.com / student123<br>
                Adviser: adviser@ojt.com / adviser123<br>
                Company: company@ojt.com / company123<br>
                Admin: admin@ojt.com / admin123
            </div>

        </div>

    </div>
    """

    return render_template_string(
        BASE,
        title="Login",
        content=render_template_string(html)
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required()
def dashboard():

    user = current_user()

    if user["role"] == "student":

        progress = calculate_progress(user["id"])

        conn = get_db()

        attendance_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM attendance
            WHERE student_id = ?
        """, (user["id"],)).fetchone()["total"]

        work_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM work_logs
            WHERE student_id = ?
            AND status = 'Verified'
        """, (user["id"],)).fetchone()["total"]

        report_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM weekly_reports
            WHERE student_id = ?
            AND status = 'Approved'
        """, (user["id"],)).fetchone()["total"]

        application = conn.execute("""
            SELECT * FROM applications
            WHERE student_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user["id"],)).fetchone()

        conn.close()

        if progress >= 80:
            status = "Good Standing"
            status_class = "badge-green"
        elif progress >= 60:
            status = "Monitor"
            status_class = "badge-yellow"
        else:
            status = "At Risk"
            status_class = "badge-red"

        body = """
        <div class="topbar">
            <div>
                <h1>Student Dashboard</h1>
                <p>Welcome back, {{ user['name'] }} 👋</p>
            </div>

            <div class="user-box">
                👨‍🎓 Student
            </div>
        </div>

        <div class="card-grid">

            <div class="card">
                <div class="card-title">OJT Progress</div>
                <div class="card-value blue">{{ progress }}%</div>

                <div class="progress">
                    <div
                        class="progress-bar"
                        style="width:{{ progress }}%"
                    ></div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">Attendance Records</div>
                <div class="card-value">{{ attendance_count }}</div>
            </div>

            <div class="card">
                <div class="card-title">Verified Work Logs</div>
                <div class="card-value green">{{ work_count }}</div>
            </div>

            <div class="card">
                <div class="card-title">Approved Reports</div>
                <div class="card-value">{{ report_count }}</div>
            </div>

        </div>

        <div class="section">

            <h2>OJT Status</h2>

            <p>
                Current Status:
                <span class="badge {{ status_class }}">
                    {{ status }}
                </span>
            </p>

            {% if application %}

            <p>
                <b>Company:</b> {{ application['company'] }}
            </p>

            <p>
                <b>Position:</b> {{ application['position'] }}
            </p>

            <p>
                <b>Required Hours:</b>
                {{ application['required_hours'] }} hours
            </p>

            {% endif %}

        </div>
        """

        return page("Dashboard", render_template_string(
            body,
            user=user,
            progress=progress,
            attendance_count=attendance_count,
            work_count=work_count,
            report_count=report_count,
            application=application,
            status=status,
            status_class=status_class
        ))

    elif user["role"] == "company":

        return company_dashboard()

    elif user["role"] == "adviser":

        return adviser_dashboard()

    else:

        return admin_dashboard()


# =========================================================
# STUDENT PROFILE
# =========================================================

@app.route("/profile")
@login_required("student")
def profile():

    user = current_user()

    body = """
    <div class="topbar">
        <h1>My Profile</h1>
    </div>

    <div class="section">

        <div class="profile">

            <div class="avatar">
                {{ user['name'][0] }}
            </div>

            <div>
                <h2>{{ user['name'] }}</h2>
                <p>{{ user['email'] }}</p>
                <span class="badge badge-blue">
                    Student
                </span>
            </div>

        </div>

        <hr style="border:none;border-top:1px solid #eee;margin:25px 0;">

        <div class="form-grid">

            <div>
                <b>Student ID</b>
                <p>{{ user['student_id'] }}</p>
            </div>

            <div>
                <b>Company</b>
                <p>{{ user['company'] }}</p>
            </div>

        </div>

    </div>
    """

    return page("Profile", render_template_string(body, user=user))


# =========================================================
# OJT APPLICATION
# =========================================================

@app.route("/application", methods=["GET", "POST"])
@login_required("student")
def application():

    user = current_user()

    if request.method == "POST":

        conn = get_db()

        conn.execute("""
            INSERT INTO applications
            (student_id, company, position, required_hours,
             start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            user["id"],
            request.form["company"],
            request.form["position"],
            request.form["required_hours"],
            request.form["start_date"],
            request.form["end_date"]
        ))

        conn.commit()
        conn.close()

        flash("OJT application submitted.", "success")

        return redirect(url_for("application"))

    conn = get_db()

    apps = conn.execute("""
        SELECT * FROM applications
        WHERE student_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>OJT Application</h1>
    </div>

    <div class="section">

        <h2>Submit OJT Application</h2>

        <form method="POST">

            <div class="form-grid">

                <div>
                    <label>Company</label>
                    <input name="company" required>
                </div>

                <div>
                    <label>Position</label>
                    <input
                        name="position"
                        placeholder="Example: IT Intern"
                        required
                    >
                </div>

                <div>
                    <label>Required Hours</label>
                    <input
                        type="number"
                        name="required_hours"
                        value="600"
                        required
                    >
                </div>

                <div>
                    <label>Start Date</label>
                    <input type="date" name="start_date" required>
                </div>

                <div>
                    <label>End Date</label>
                    <input type="date" name="end_date" required>
                </div>

            </div>

            <button class="btn">
                Submit Application
            </button>

        </form>

    </div>

    <div class="section">

        <h2>Application History</h2>

        <table>

        <tr>
            <th>Company</th>
            <th>Position</th>
            <th>Hours</th>
            <th>Status</th>
        </tr>

        {% for a in apps %}

        <tr>
            <td>{{ a['company'] }}</td>
            <td>{{ a['position'] }}</td>
            <td>{{ a['required_hours'] }}</td>
            <td>
                <span class="badge badge-blue">
                    {{ a['status'] }}
                </span>
            </td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Application",
        render_template_string(body, apps=apps)
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance", methods=["GET", "POST"])
@login_required("student")
def attendance():

    user = current_user()

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    conn = get_db()

    record = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        AND date = ?
    """, (user["id"], today)).fetchone()

    if request.method == "POST":

        action = request.form["action"]
        location = request.form.get("location", "Location not provided")

        if action == "checkin":

            if record:
                flash("You already checked in today.", "error")
            else:

                conn.execute("""
                    INSERT INTO attendance
                    (student_id, date, check_in, location, status)
                    VALUES (?, ?, ?, ?, 'Present')
                """, (
                    user["id"],
                    today,
                    now,
                    location
                ))

                conn.commit()

                add_notification(
                    user["id"],
                    "Your attendance check-in was recorded."
                )

                flash("Check-in recorded successfully.", "success")

        elif action == "checkout":

            if not record:
                flash("You need to check in first.", "error")

            elif record["check_out"]:
                flash("You already checked out today.", "error")

            else:

                conn.execute("""
                    UPDATE attendance
                    SET check_out = ?
                    WHERE id = ?
                """, (
                    now,
                    record["id"]
                ))

                conn.commit()

                add_notification(
                    user["id"],
                    "Your attendance check-out was recorded."
                )

                flash("Check-out recorded successfully.", "success")

        conn.close()

        return redirect(url_for("attendance"))

    records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY id DESC
        LIMIT 30
    """, (user["id"],)).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Attendance / DTR</h1>
    </div>

    <div class="section">

        <h2>Today's Attendance</h2>

        {% if not record %}

        <form method="POST">

            <input
                type="hidden"
                name="action"
                value="checkin"
            >

            <label>Current Work Location</label>

            <input
                name="location"
                placeholder="Example: ABC Technology Solutions"
                required
            >

            <p style="font-size:12px;color:#64748b;">
                📍 Location verification is recorded together
                with your check-in.
            </p>

            <button class="btn">
                📍 Check In
            </button>

        </form>

        {% else %}

        <p>
            <b>Check-in:</b>
            {{ record['check_in'] }}
        </p>

        <p>
            <b>Location:</b>
            {{ record['location'] }}
        </p>

        {% if not record['check_out'] %}

        <form method="POST">

            <input
                type="hidden"
                name="action"
                value="checkout"
            >

            <button class="btn btn-red">
                ⏱️ Check Out
            </button>

        </form>

        {% else %}

        <p>
            <b>Check-out:</b>
            {{ record['check_out'] }}
        </p>

        <span class="badge badge-green">
            Complete
        </span>

        {% endif %}

        {% endif %}

    </div>

    <div class="section">

        <h2>Attendance History</h2>

        <table>

        <tr>
            <th>Date</th>
            <th>Check-in</th>
            <th>Check-out</th>
            <th>Location</th>
            <th>Status</th>
        </tr>

        {% for r in records %}

        <tr>
            <td>{{ r['date'] }}</td>
            <td>{{ r['check_in'] }}</td>
            <td>{{ r['check_out'] or '-' }}</td>
            <td>{{ r['location'] }}</td>
            <td>
                <span class="badge badge-green">
                    {{ r['status'] }}
                </span>
            </td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Attendance",
        render_template_string(
            body,
            record=record,
            records=records
        )
    )


# =========================================================
# DAILY WORK LOG
# =========================================================

@app.route("/work-logs", methods=["GET", "POST"])
@login_required("student")
def work_logs():

    user = current_user()

    if request.method == "POST":

        conn = get_db()

        conn.execute("""
            INSERT INTO work_logs
            (student_id, date, task, evidence, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (
            user["id"],
            datetime.now().strftime("%Y-%m-%d"),
            request.form["task"],
            request.form.get("evidence", "")
        ))

        conn.commit()
        conn.close()

        add_notification(
            user["id"],
            "Your daily work log was submitted for verification."
        )

        flash("Work log submitted successfully.", "success")

        return redirect(url_for("work_logs"))

    conn = get_db()

    logs = conn.execute("""
        SELECT * FROM work_logs
        WHERE student_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Daily Work Logs</h1>
    </div>

    <div class="section">

        <h2>Submit Today's Work</h2>

        <form method="POST">

            <label>Today's Task</label>

            <textarea
                name="task"
                placeholder="Describe what you worked on today..."
                required
            ></textarea>

            <label>Evidence / Reference</label>

            <input
                name="evidence"
                placeholder="Example: Computer troubleshooting, software installation"
            >

            <button class="btn">
                Submit Work Log
            </button>

        </form>

    </div>

    <div class="section">

        <h2>Work Log History</h2>

        <table>

        <tr>
            <th>Date</th>
            <th>Task</th>
            <th>Evidence</th>
            <th>Status</th>
            <th>Supervisor Comment</th>
        </tr>

        {% for log in logs %}

        <tr>
            <td>{{ log['date'] }}</td>
            <td>{{ log['task'] }}</td>
            <td>{{ log['evidence'] or '-' }}</td>

            <td>
                {% if log['status'] == 'Verified' %}
                    <span class="badge badge-green">
                        Verified
                    </span>
                {% elif log['status'] == 'Rejected' %}
                    <span class="badge badge-red">
                        Rejected
                    </span>
                {% else %}
                    <span class="badge badge-yellow">
                        Pending
                    </span>
                {% endif %}
            </td>

            <td>{{ log['supervisor_comment'] or '-' }}</td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Work Logs",
        render_template_string(body, logs=logs)
    )


# =========================================================
# WEEKLY REPORTS
# =========================================================

@app.route("/weekly-reports", methods=["GET", "POST"])
@login_required("student")
def weekly_reports():

    user = current_user()

    if request.method == "POST":

        conn = get_db()

        conn.execute("""
            INSERT INTO weekly_reports
            (student_id, week, summary, hours, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (
            user["id"],
            request.form["week"],
            request.form["summary"],
            request.form["hours"]
        ))

        conn.commit()
        conn.close()

        flash("Weekly report submitted.", "success")

        return redirect(url_for("weekly_reports"))

    conn = get_db()

    reports = conn.execute("""
        SELECT * FROM weekly_reports
        WHERE student_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Weekly Reports</h1>
    </div>

    <div class="section">

        <h2>Submit Weekly Report</h2>

        <form method="POST">

            <label>Week</label>

            <input
                type="text"
                name="week"
                placeholder="Example: Week 4"
                required
            >

            <label>Total Hours</label>

            <input
                type="number"
                name="hours"
                required
            >

            <label>Weekly Summary</label>

            <textarea
                name="summary"
                placeholder="Describe your activities, lessons learned, and accomplishments..."
                required
            ></textarea>

            <button class="btn">
                Submit Report
            </button>

        </form>

    </div>

    <div class="section">

        <h2>Report History</h2>

        <table>

        <tr>
            <th>Week</th>
            <th>Hours</th>
            <th>Summary</th>
            <th>Status</th>
            <th>Adviser Comment</th>
        </tr>

        {% for r in reports %}

        <tr>
            <td>{{ r['week'] }}</td>
            <td>{{ r['hours'] }}</td>
            <td>{{ r['summary'] }}</td>

            <td>
                {% if r['status'] == 'Approved' %}
                    <span class="badge badge-green">
                        Approved
                    </span>
                {% else %}
                    <span class="badge badge-yellow">
                        {{ r['status'] }}
                    </span>
                {% endif %}
            </td>

            <td>{{ r['adviser_comment'] or '-' }}</td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Weekly Reports",
        render_template_string(body, reports=reports)
    )


# =========================================================
# STUDENT EVALUATION VIEW
# =========================================================

@app.route("/student-evaluation")
@login_required("student")
def student_evaluation():

    user = current_user()

    conn = get_db()

    evaluation = conn.execute("""
        SELECT e.*, u.name AS supervisor_name
        FROM evaluations e
        LEFT JOIN users u ON e.supervisor_id = u.id
        WHERE e.student_id = ?
        ORDER BY e.id DESC
        LIMIT 1
    """, (user["id"],)).fetchone()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Evaluation</h1>
    </div>

    <div class="section">

    {% if evaluation %}

        <h2>Supervisor Evaluation</h2>

        <div class="card-grid">

            <div class="card">
                <div class="card-title">Attendance</div>
                <div class="card-value">
                    {{ evaluation['attendance_score'] }}/10
                </div>
            </div>

            <div class="card">
                <div class="card-title">Performance</div>
                <div class="card-value">
                    {{ evaluation['performance_score'] }}/10
                </div>
            </div>

            <div class="card">
                <div class="card-title">Attitude</div>
                <div class="card-value">
                    {{ evaluation['attitude_score'] }}/10
                </div>
            </div>

            <div class="card">
                <div class="card-title">Skills</div>
                <div class="card-value">
                    {{ evaluation['skills_score'] }}/10
                </div>
            </div>

        </div>

        <p>
            <b>Supervisor:</b>
            {{ evaluation['supervisor_name'] }}
        </p>

        <p>
            <b>Comments:</b>
            {{ evaluation['comments'] or 'No comments.' }}
        </p>

    {% else %}

        <p>No evaluation has been submitted yet.</p>

    {% endif %}

    </div>
    """

    return page(
        "Evaluation",
        render_template_string(
            body,
            evaluation=evaluation
        )
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
@login_required()
def notifications():

    conn = get_db()

    items = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    body = """
    <div class="topbar">
        <h1>Notifications</h1>
    </div>

    <div class="section">

    {% if items %}

        {% for n in items %}

        <div style="
            padding:15px;
            border-bottom:1px solid #eee;
        ">

            <b>{{ n['message'] }}</b>

            <div style="
                color:#64748b;
                font-size:11px;
                margin-top:5px;
            ">
                {{ n['created_at'] }}
            </div>

        </div>

        {% endfor %}

    {% else %}

        <p>No notifications.</p>

    {% endif %}

    </div>
    """

    return page(
        "Notifications",
        render_template_string(body, items=items)
    )


# =========================================================
# COMPANY DASHBOARD
# =========================================================

def company_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student'
        AND company = ?
    """, (current_user()["company"],)).fetchall()

    pending = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE status = 'Pending'
    """).fetchone()["total"]

    conn.close()

    body = """
    <div class="topbar">

        <div>
            <h1>Company Dashboard</h1>
            <p>Supervisor monitoring panel</p>
        </div>

        <div class="user-box">
            👨‍💼 Company
        </div>

    </div>

    <div class="card-grid">

        <div class="card">
            <div class="card-title">Assigned Students</div>
            <div class="card-value blue">
                {{ students|length }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Pending Work Logs</div>
            <div class="card-value orange">
                {{ pending }}
            </div>
        </div>

    </div>

    <div class="section">

        <h2>Students</h2>

        <table>

        <tr>
            <th>Student</th>
            <th>Student ID</th>
            <th>Company</th>
        </tr>

        {% for s in students %}

        <tr>
            <td>{{ s['name'] }}</td>
            <td>{{ s['student_id'] }}</td>
            <td>{{ s['company'] }}</td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Company Dashboard",
        render_template_string(
            body,
            students=students,
            pending=pending
        )
    )


@app.route("/company/students")
@login_required("company")
def company_students():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student'
        AND company = ?
    """, (current_user()["company"],)).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Assigned Students</h1>
    </div>

    <div class="section">

        <table>

        <tr>
            <th>Name</th>
            <th>Student ID</th>
            <th>Company</th>
        </tr>

        {% for s in students %}

        <tr>
            <td>{{ s['name'] }}</td>
            <td>{{ s['student_id'] }}</td>
            <td>{{ s['company'] }}</td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Students",
        render_template_string(body, students=students)
    )


# =========================================================
# VERIFY WORK LOGS
# =========================================================

@app.route("/company/logs")
@login_required("company")
def verify_logs():

    conn = get_db()

    logs = conn.execute("""
        SELECT
            work_logs.*,
            users.name AS student_name
        FROM work_logs
        JOIN users
        ON work_logs.student_id = users.id
        ORDER BY work_logs.id DESC
    """).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Work Log Verification</h1>
    </div>

    <div class="section">

        <table>

        <tr>
            <th>Student</th>
            <th>Date</th>
            <th>Task</th>
            <th>Evidence</th>
            <th>Status</th>
            <th>Action</th>
        </tr>

        {% for log in logs %}

        <tr>

            <td>{{ log['student_name'] }}</td>
            <td>{{ log['date'] }}</td>
            <td>{{ log['task'] }}</td>
            <td>{{ log['evidence'] or '-' }}</td>

            <td>
                {{ log['status'] }}
            </td>

            <td>

                {% if log['status'] == 'Pending' %}

                <form
                    method="POST"
                    action="{{ url_for('verify_log', log_id=log['id']) }}"
                >

                    <button
                        class="btn btn-green"
                        name="action"
                        value="verify"
                    >
                        Verify
                    </button>

                    <button
                        class="btn btn-red"
                        name="action"
                        value="reject"
                    >
                        Reject
                    </button>

                </form>

                {% else %}

                    <span class="badge badge-blue">
                        {{ log['status'] }}
                    </span>

                {% endif %}

            </td>

        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Verify Logs",
        render_template_string(body, logs=logs)
    )


@app.route("/company/verify-log/<int:log_id>", methods=["POST"])
@login_required("company")
def verify_log(log_id):

    action = request.form["action"]

    status = "Verified" if action == "verify" else "Rejected"

    conn = get_db()

    log = conn.execute("""
        SELECT * FROM work_logs
        WHERE id = ?
    """, (log_id,)).fetchone()

    if log:

        conn.execute("""
            UPDATE work_logs
            SET status = ?
            WHERE id = ?
        """, (
            status,
            log_id
        ))

        conn.commit()

        add_notification(
            log["student_id"],
            f"Your work log dated {log['date']} was {status.lower()} by your supervisor."
        )

    conn.close()

    flash(f"Work log {status.lower()}.", "success")

    return redirect(url_for("verify_logs"))


# =========================================================
# COMPANY EVALUATION
# =========================================================

@app.route("/company/evaluation", methods=["GET", "POST"])
@login_required("company")
def company_evaluation():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student'
    """).fetchall()

    if request.method == "POST":

        student_id = request.form["student_id"]

        conn.execute("""
            INSERT INTO evaluations
            (
                student_id,
                supervisor_id,
                attendance_score,
                performance_score,
                attitude_score,
                skills_score,
                comments,
                date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            session["user_id"],
            request.form["attendance"],
            request.form["performance"],
            request.form["attitude"],
            request.form["skills"],
            request.form["comments"],
            datetime.now().strftime("%Y-%m-%d")
        ))

        conn.commit()

        add_notification(
            student_id,
            "Your supervisor submitted a new OJT evaluation."
        )

        flash("Evaluation submitted.", "success")

    conn.close()

    body = """
    <div class="topbar">
        <h1>Student Evaluation</h1>
    </div>

    <div class="section">

        <form method="POST">

            <label>Student</label>

            <select name="student_id" required>

                {% for s in students %}

                <option value="{{ s['id'] }}">
                    {{ s['name'] }}
                </option>

                {% endfor %}

            </select>

            <div class="form-grid">

                <div>
                    <label>Attendance Score (1-10)</label>
                    <input
                        type="number"
                        name="attendance"
                        min="1"
                        max="10"
                        required
                    >
                </div>

                <div>
                    <label>Performance Score (1-10)</label>
                    <input
                        type="number"
                        name="performance"
                        min="1"
                        max="10"
                        required
                    >
                </div>

                <div>
                    <label>Attitude Score (1-10)</label>
                    <input
                        type="number"
                        name="attitude"
                        min="1"
                        max="10"
                        required
                    >
                </div>

                <div>
                    <label>Skills Score (1-10)</label>
                    <input
                        type="number"
                        name="skills"
                        min="1"
                        max="10"
                        required
                    >
                </div>

            </div>

            <label>Comments</label>

            <textarea
                name="comments"
                placeholder="Supervisor comments..."
            ></textarea>

            <button class="btn">
                Submit Evaluation
            </button>

        </form>

    </div>
    """

    return page(
        "Evaluation",
        render_template_string(
            body,
            students=students
        )
    )


# =========================================================
# ADVISER DASHBOARD
# =========================================================

def adviser_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student'
    """).fetchall()

    conn.close()

    body = """
    <div class="topbar">

        <div>
            <h1>Adviser Dashboard</h1>
            <p>Monitor OJT student progress</p>
        </div>

        <div class="user-box">
            👨‍🏫 Adviser
        </div>

    </div>

    <div class="card-grid">

        <div class="card">
            <div class="card-title">Total Students</div>
            <div class="card-value blue">
                {{ students|length }}
            </div>
        </div>

    </div>

    <div class="section">

        <h2>Student Monitoring</h2>

        <table>

        <tr>
            <th>Student</th>
            <th>Progress</th>
            <th>Status</th>
        </tr>

        {% for s in students %}

        {% set progress = progress_map[s['id']] %}

        <tr>

            <td>{{ s['name'] }}</td>

            <td>
                {{ progress }}%

                <div class="progress">
                    <div
                        class="progress-bar"
                        style="width:{{ progress }}%"
                    ></div>
                </div>
            </td>

            <td>

                {% if progress >= 80 %}

                    <span class="badge badge-green">
                        Good Standing
                    </span>

                {% elif progress >= 60 %}

                    <span class="badge badge-yellow">
                        Monitor
                    </span>

                {% else %}

                    <span class="badge badge-red">
                        At Risk
                    </span>

                {% endif %}

            </td>

        </tr>

        {% endfor %}

        </table>

    </div>
    """

    progress_map = {}

    for s in students:
        progress_map[s["id"]] = calculate_progress(s["id"])

    return page(
        "Adviser Dashboard",
        render_template_string(
            body,
            students=students,
            progress_map=progress_map
        )
    )


@app.route("/adviser/students")
@login_required("adviser")
def monitor_students():

    return adviser_dashboard()


# =========================================================
# ADVISER REPORTS
# =========================================================

@app.route("/adviser/reports")
@login_required("adviser")
def adviser_reports():

    conn = get_db()

    reports = conn.execute("""
        SELECT
            weekly_reports.*,
            users.name AS student_name
        FROM weekly_reports
        JOIN users
        ON weekly_reports.student_id = users.id
        ORDER BY weekly_reports.id DESC
    """).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Weekly Report Monitoring</h1>
    </div>

    <div class="section">

        <table>

        <tr>
            <th>Student</th>
            <th>Week</th>
            <th>Hours</th>
            <th>Summary</th>
            <th>Status</th>
        </tr>

        {% for r in reports %}

        <tr>

            <td>{{ r['student_name'] }}</td>
            <td>{{ r['week'] }}</td>
            <td>{{ r['hours'] }}</td>
            <td>{{ r['summary'] }}</td>

            <td>

                {% if r['status'] == 'Approved' %}

                    <span class="badge badge-green">
                        Approved
                    </span>

                {% else %}

                    <span class="badge badge-yellow">
                        Pending
                    </span>

                {% endif %}

            </td>

        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Reports",
        render_template_string(body, reports=reports)
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'student'
    """).fetchone()["total"]

    companies = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'company'
    """).fetchone()["total"]

    advisers = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'adviser'
    """).fetchone()["total"]

    logs = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE status = 'Pending'
    """).fetchone()["total"]

    conn.close()

    body = """
    <div class="topbar">

        <div>
            <h1>Admin Dashboard</h1>
            <p>System administration</p>
        </div>

        <div class="user-box">
            🔐 Administrator
        </div>

    </div>

    <div class="card-grid">

        <div class="card">
            <div class="card-title">Students</div>
            <div class="card-value blue">
                {{ students }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Companies</div>
            <div class="card-value">
                {{ companies }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Advisers</div>
            <div class="card-value">
                {{ advisers }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Pending Work Logs</div>
            <div class="card-value orange">
                {{ logs }}
            </div>
        </div>

    </div>

    <div class="section">

        <h2>System Overview</h2>

        <p>
            The system monitors OJT attendance, work logs,
            weekly reports, supervisor verification,
            and student progress.
        </p>

    </div>
    """

    return page(
        "Admin Dashboard",
        render_template_string(
            body,
            students=students,
            companies=companies,
            advisers=advisers,
            logs=logs
        )
    )


@app.route("/admin/students")
@login_required("admin")
def admin_students():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student'
    """).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>Student Management</h1>
    </div>

    <div class="section">

        <table>

        <tr>
            <th>Name</th>
            <th>Student ID</th>
            <th>Email</th>
            <th>Company</th>
            <th>Progress</th>
        </tr>

        {% for s in students %}

        <tr>

            <td>{{ s['name'] }}</td>
            <td>{{ s['student_id'] }}</td>
            <td>{{ s['email'] }}</td>
            <td>{{ s['company'] }}</td>

            <td>
                {{ progress_map[s['id']] }}%
            </td>

        </tr>

        {% endfor %}

        </table>

    </div>
    """

    progress_map = {}

    for s in students:
        progress_map[s["id"]] = calculate_progress(s["id"])

    return page(
        "Students",
        render_template_string(
            body,
            students=students,
            progress_map=progress_map
        )
    )


@app.route("/admin/users")
@login_required("admin")
def admin_users():

    conn = get_db()

    users = conn.execute("""
        SELECT * FROM users
        ORDER BY role, name
    """).fetchall()

    conn.close()

    body = """
    <div class="topbar">
        <h1>User Management</h1>
    </div>

    <div class="section">

        <table>

        <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Company</th>
        </tr>

        {% for u in users %}

        <tr>
            <td>{{ u['name'] }}</td>
            <td>{{ u['email'] }}</td>
            <td>{{ u['role'] }}</td>
            <td>{{ u['company'] or '-' }}</td>
        </tr>

        {% endfor %}

        </table>

    </div>
    """

    return page(
        "Users",
        render_template_string(body, users=users)
    )


@app.route("/admin/reports")
@login_required("admin")
def admin_reports():

    conn = get_db()

    total_attendance = conn.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
    """).fetchone()["total"]

    total_logs = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
    """).fetchone()["total"]

    verified_logs = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE status = 'Verified'
    """).fetchone()["total"]

    total_reports = conn.execute("""
        SELECT COUNT(*) AS total
        FROM weekly_reports
    """).fetchone()["total"]

    conn.close()

    body = """
    <div class="topbar">
        <h1>System Reports</h1>
    </div>

    <div class="card-grid">

        <div class="card">
            <div class="card-title">Attendance Records</div>
            <div class="card-value">
                {{ attendance }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Work Logs</div>
            <div class="card-value">
                {{ logs }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Verified Logs</div>
            <div class="card-value green">
                {{ verified }}
            </div>
        </div>

        <div class="card">
            <div class="card-title">Weekly Reports</div>
            <div class="card-value">
                {{ reports }}
            </div>
        </div>

    </div>

    <div class="section">

        <h2>Verification Chain</h2>

        <p>
            Student Check-in
            →
            Location
            →
            Work Log
            →
            Supervisor Verification
            →
            Weekly Report
            →
            Evaluation
        </p>

    </div>
    """

    return page(
        "System Reports",
        render_template_string(
            body,
            attendance=total_attendance,
            logs=total_logs,
            verified=verified_logs,
            reports=total_reports
        )
    )


# =========================================================
# CREATE DATABASE AND RUN
# =========================================================

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )