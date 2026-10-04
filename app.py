from flask import Flask, request, redirect, url_for, session, render_template_string, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "ojt-system-secret-key-change-this"

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
            course TEXT,
            company TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            company TEXT,
            position TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            time_in TEXT,
            time_out TEXT,
            location TEXT,
            status TEXT DEFAULT 'Present'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            task TEXT,
            description TEXT,
            evidence TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            week TEXT,
            summary TEXT,
            challenges TEXT,
            learnings TEXT,
            status TEXT DEFAULT 'Submitted'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            evaluator TEXT,
            attendance_score INTEGER,
            performance_score INTEGER,
            attitude_score INTEGER,
            overall_score INTEGER,
            comments TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            date TEXT,
            is_read INTEGER DEFAULT 0
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
            "Student",
            "BS Information Technology",
            "Tech Solutions Inc."
        ),
        (
            "Maria Santos",
            "adviser@ojt.com",
            "adviser123",
            "Adviser",
            "BS Information Technology",
            ""
        ),
        (
            "John Reyes",
            "company@ojt.com",
            "company123",
            "Company",
            "",
            "Tech Solutions Inc."
        ),
        (
            "System Administrator",
            "admin@ojt.com",
            "admin123",
            "Admin",
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
                (name, email, password, role, course, company)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user[0],
                user[1],
                generate_password_hash(user[2]),
                user[3],
                user[4],
                user[5]
            ))

    # -----------------------------------------------------
    # SAMPLE APPLICATION
    # -----------------------------------------------------

    student = cur.execute(
        "SELECT id FROM users WHERE email = ?",
        ("student@ojt.com",)
    ).fetchone()

    if student:
        application = cur.execute(
            "SELECT id FROM applications WHERE student_id = ?",
            (student["id"],)
        ).fetchone()

        if not application:
            cur.execute("""
                INSERT INTO applications
                (student_id, company, position, start_date, end_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                student["id"],
                "Tech Solutions Inc.",
                "IT Intern",
                "2026-09-01",
                "2026-12-15",
                "Approved"
            ))

    conn.commit()
    conn.close()


# =========================================================
# AUTHENTICATION
# =========================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    allowed_roles = {str(role).strip().lower() for role in roles}

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            current_role = str(session.get("role", "")).strip().lower()

            if current_role not in allowed_roles:
                return redirect(url_for("dashboard"))

            return f(*args, **kwargs)

        return decorated

    return decorator


# =========================================================
# BASE STYLE
# =========================================================

BASE_STYLE = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f7fb;
    color: #1f2937;
}

a {
    text-decoration: none;
    color: inherit;
}

button,
input,
textarea,
select {
    font-family: inherit;
}

/* ================================
   NAVBAR
================================ */

.navbar {
    height: 70px;
    background: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 6%;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    position: relative;
    z-index: 10;
}

.logo {
    font-size: 22px;
    font-weight: 800;
    color: #1769e0;
}

.logo span {
    color: #111827;
}

.nav-links {
    display: flex;
    gap: 25px;
    align-items: center;
}

.nav-links a {
    color: #64748b;
    font-size: 14px;
    font-weight: 600;
}

.nav-links a:hover {
    color: #1769e0;
}

.login-btn {
    background: #1769e0;
    color: white !important;
    padding: 11px 20px;
    border-radius: 10px;
}

/* ================================
   LANDING PAGE
================================ */

.hero {
    min-height: 590px;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 10% 20%, rgba(255,255,255,.30), transparent 25%),
        radial-gradient(circle at 90% 70%, rgba(255,255,255,.22), transparent 25%),
        linear-gradient(135deg, #0d47a1, #1976d2 55%, #42a5f5);
    color: white;
}

.hero::before {
    content: "";
    width: 330px;
    height: 330px;
    border: 50px solid rgba(255,255,255,.08);
    border-radius: 50%;
    position: absolute;
    top: -130px;
    right: -70px;
}

.hero::after {
    content: "";
    width: 260px;
    height: 260px;
    background: rgba(255,255,255,.06);
    border-radius: 50%;
    position: absolute;
    bottom: -100px;
    left: -70px;
}

.hero-content {
    max-width: 1180px;
    margin: auto;
    min-height: 520px;
    display: grid;
    grid-template-columns: 1.05fr .95fr;
    gap: 50px;
    align-items: center;
    padding: 60px 25px;
    position: relative;
    z-index: 2;
}

.hero-text h1 {
    font-size: 55px;
    line-height: 1.05;
    margin: 0 0 20px;
    letter-spacing: -2px;
}

.hero-text h1 span {
    color: #dff1ff;
}

.hero-text p {
    font-size: 18px;
    line-height: 1.7;
    color: #e8f4ff;
    max-width: 550px;
}

.hero-buttons {
    display: flex;
    gap: 12px;
    margin-top: 30px;
}

.primary-btn {
    display: inline-block;
    background: white;
    color: #1261c9;
    padding: 14px 24px;
    border-radius: 12px;
    font-weight: 700;
    box-shadow: 0 8px 25px rgba(0,0,0,.12);
}

.secondary-btn {
    display: inline-block;
    border: 1px solid rgba(255,255,255,.5);
    color: white;
    padding: 14px 24px;
    border-radius: 12px;
    font-weight: 700;
}

/* ================================
   DASHBOARD PREVIEW
================================ */

.preview-wrapper {
    position: relative;
}

.preview-card {
    background: rgba(255,255,255,.96);
    border-radius: 24px;
    padding: 22px;
    color: #172033;
    box-shadow: 0 25px 60px rgba(0,0,0,.20);
    transform: rotate(1deg);
}

.preview-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.preview-title {
    font-size: 16px;
    font-weight: 800;
}

.preview-user {
    width: 38px;
    height: 38px;
    background: #e5f1ff;
    color: #1769e0;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.preview-welcome {
    background: linear-gradient(135deg,#eaf4ff,#f7fbff);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 15px;
}

.preview-welcome h3 {
    margin: 0 0 6px;
}

.preview-welcome p {
    margin: 0;
    color: #64748b;
    font-size: 13px;
}

.preview-stats {
    display: grid;
    grid-template-columns: repeat(2,1fr);
    gap: 12px;
}

.preview-stat {
    background: #f8fafc;
    padding: 15px;
    border-radius: 14px;
}

.preview-stat strong {
    display: block;
    font-size: 22px;
    color: #1769e0;
}

.preview-stat small {
    color: #64748b;
}

.progress-box {
    margin-top: 15px;
    padding: 16px;
    background: #f8fafc;
    border-radius: 14px;
}

.progress-bar {
    height: 10px;
    background: #e5e7eb;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 10px;
}

.progress-fill {
    width: 80%;
    height: 100%;
    background: linear-gradient(90deg,#1976d2,#42a5f5);
    border-radius: 20px;
}

/* ================================
   FEATURES
================================ */

.features {
    background: white;
    padding: 55px 6%;
}

.features-title {
    text-align: center;
    margin-bottom: 35px;
}

.features-title h2 {
    margin: 0;
    font-size: 30px;
}

.features-title p {
    color: #64748b;
}

.feature-grid {
    max-width: 1050px;
    margin: auto;
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 20px;
}

.feature-card {
    padding: 25px;
    border: 1px solid #e8edf5;
    border-radius: 18px;
    background: white;
    transition: .25s;
}

.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 35px rgba(0,0,0,.08);
}

.feature-icon {
    width: 50px;
    height: 50px;
    background: #e9f3ff;
    color: #1769e0;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 23px;
    margin-bottom: 15px;
}

.feature-card h3 {
    margin: 0 0 8px;
}

.feature-card p {
    color: #64748b;
    line-height: 1.6;
    font-size: 14px;
}

/* ================================
   LOGIN
================================ */

.login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 30px;
    background:
        radial-gradient(circle at 10% 10%, #dbeeff, transparent 30%),
        radial-gradient(circle at 90% 90%, #d9ecff, transparent 30%),
        #f4f8fd;
}

.login-card {
    width: 420px;
    max-width: 100%;
    background: white;
    border-radius: 22px;
    padding: 35px;
    box-shadow: 0 20px 60px rgba(25,80,140,.12);
}

.login-logo {
    text-align: center;
    margin-bottom: 25px;
}

.login-logo .circle {
    width: 60px;
    height: 60px;
    margin: auto;
    background: #e7f2ff;
    color: #1769e0;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
}

.login-logo h2 {
    margin: 12px 0 5px;
}

.login-logo p {
    margin: 0;
    color: #64748b;
    font-size: 14px;
}

.form-group {
    margin-bottom: 17px;
}

.form-group label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 7px;
}

.form-control {
    width: 100%;
    padding: 13px 14px;
    border: 1px solid #dbe3ee;
    border-radius: 10px;
    outline: none;
    background: #fbfdff;
}

.form-control:focus {
    border-color: #1976d2;
    box-shadow: 0 0 0 3px rgba(25,118,210,.08);
}

.full-btn {
    width: 100%;
    border: none;
    background: #1769e0;
    color: white;
    padding: 14px;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
}

.full-btn:hover {
    background: #0d57c5;
}

.back-link {
    text-align: center;
    display: block;
    margin-top: 18px;
    color: #1769e0;
    font-size: 14px;
}

/* ================================
   APP LAYOUT
================================ */

.app-layout {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 245px;
    background: white;
    border-right: 1px solid #e6ebf2;
    padding: 22px 15px;
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
}

.sidebar-logo {
    font-size: 20px;
    font-weight: 800;
    color: #1769e0;
    padding: 8px 12px 25px;
}

.sidebar-logo span {
    color: #111827;
}

.user-mini {
    background: #f2f7fd;
    padding: 13px;
    border-radius: 12px;
    margin-bottom: 20px;
}

.user-mini strong {
    display: block;
    font-size: 14px;
}

.user-mini small {
    color: #64748b;
}

.menu-title {
    font-size: 10px;
    font-weight: 800;
    color: #94a3b8;
    padding: 0 12px;
    margin: 20px 0 8px;
    text-transform: uppercase;
}

.menu-link {
    display: block;
    padding: 11px 12px;
    border-radius: 9px;
    margin-bottom: 4px;
    color: #64748b;
    font-size: 14px;
    font-weight: 600;
}

.menu-link:hover,
.menu-link.active {
    background: #eaf3ff;
    color: #1769e0;
}

.logout {
    position: absolute;
    bottom: 20px;
    left: 15px;
    right: 15px;
}

.main {
    margin-left: 245px;
    width: calc(100% - 245px);
}

.topbar {
    height: 70px;
    background: white;
    border-bottom: 1px solid #e6ebf2;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 30px;
}

.topbar h3 {
    margin: 0;
}

.content {
    padding: 30px;
    max-width: 1250px;
}

.page-title {
    margin-bottom: 25px;
}

.page-title h2 {
    margin: 0 0 5px;
}

.page-title p {
    color: #64748b;
    margin: 0;
}

/* ================================
   CARDS
================================ */

.cards {
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 18px;
    margin-bottom: 25px;
}

.card {
    background: white;
    border: 1px solid #e7edf4;
    border-radius: 15px;
    padding: 20px;
}

.stat-card {
    position: relative;
    overflow: hidden;
}

.stat-card small {
    color: #64748b;
}

.stat-card h2 {
    margin: 9px 0 0;
    font-size: 28px;
}

.stat-icon {
    position: absolute;
    right: 18px;
    top: 18px;
    font-size: 24px;
    opacity: .7;
}

.section {
    background: white;
    border: 1px solid #e7edf4;
    border-radius: 15px;
    padding: 22px;
    margin-bottom: 22px;
}

.section h3 {
    margin-top: 0;
}

/* ================================
   TABLE
================================ */

.table-wrapper {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    text-align: left;
    padding: 13px;
    border-bottom: 1px solid #edf1f5;
    font-size: 14px;
}

th {
    color: #64748b;
    font-size: 12px;
    text-transform: uppercase;
}

.status {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    background: #eaf3ff;
    color: #1769e0;
}

.status.good {
    background: #eaf8ef;
    color: #16803c;
}

.status.warning {
    background: #fff6df;
    color: #a66b00;
}

/* ================================
   ALERTS
================================ */

.flash {
    max-width: 500px;
    margin: 20px auto 0;
    background: #eaf3ff;
    border: 1px solid #cce2ff;
    color: #1769e0;
    padding: 12px 15px;
    border-radius: 10px;
}

/* ================================
   PROGRESS
================================ */

.big-progress {
    background: #edf1f5;
    height: 16px;
    border-radius: 20px;
    overflow: hidden;
}

.big-progress div {
    height: 100%;
    background: linear-gradient(90deg,#1769e0,#42a5f5);
    border-radius: 20px;
}

/* ================================
   FOOTER
================================ */

.footer {
    text-align: center;
    padding: 25px;
    color: #94a3b8;
    font-size: 13px;
}

/* ================================
   MOBILE
================================ */

@media(max-width: 900px) {

    .hero-content {
        grid-template-columns: 1fr;
        text-align: center;
    }

    .hero-text p {
        margin-left: auto;
        margin-right: auto;
    }

    .hero-buttons {
        justify-content: center;
    }

    .preview-wrapper {
        max-width: 520px;
        margin: auto;
        width: 100%;
    }

    .feature-grid {
        grid-template-columns: 1fr;
    }

    .cards {
        grid-template-columns: repeat(2,1fr);
    }
}

@media(max-width: 700px) {

    .navbar {
        padding: 0 20px;
    }

    .nav-links a:not(.login-btn) {
        display: none;
    }

    .hero-text h1 {
        font-size: 40px;
    }

    .sidebar {
        width: 70px;
        padding: 15px 8px;
    }

    .sidebar-logo {
        font-size: 0;
        text-align: center;
    }

    .sidebar-logo:first-letter {
        font-size: 24px;
    }

    .user-mini,
    .menu-title,
    .menu-link span {
        display: none;
    }

    .menu-link {
        text-align: center;
        font-size: 20px;
        padding: 13px 5px;
    }

    .logout {
        left: 8px;
        right: 8px;
    }

    .main {
        margin-left: 70px;
        width: calc(100% - 70px);
    }

    .topbar {
        padding: 0 15px;
    }

    .content {
        padding: 18px;
    }

    .cards {
        grid-template-columns: 1fr;
    }
}

/* ================================
   QUICK ACTIONS
================================ */

.quick-actions {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 18px;
}

.quick-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 13px;
    background: #f8fbff;
    border: 1px solid #e1eaf5;
    border-radius: 12px;
    color: #1769e0;
    transition: .2s;
}

.quick-btn:hover {
    transform: translateY(-2px);
    border-color: #bcd7f8;
    box-shadow: 0 8px 20px rgba(0,0,0,.06);
}

.quick-btn > span {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.quick-btn strong {
    color: #1f2937;
    font-size: 13px;
}

.quick-btn small {
    color: #64748b;
    font-size: 11px;
}

@media(max-width: 900px) {
    .quick-actions {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media(max-width: 700px) {
    .quick-actions {
        grid-template-columns: 1fr;
    }
}


</style>
"""


# =========================================================
# LANDING PAGE
# =========================================================

LANDING_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>OJT Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
""" + BASE_STYLE + """
</head>

<body>

<nav class="navbar">
    <div class="logo">🎓 OJT<span>Tracker</span></div>

    <div class="nav-links">
        <a href="#features">Features</a>
        <a href="{{ url_for('login') }}" class="login-btn">Login</a>
    </div>
</nav>

<section class="hero">

    <div class="hero-content">

        <div class="hero-text">

            <div style="
                display:inline-block;
                padding:7px 13px;
                border-radius:20px;
                background:rgba(255,255,255,.14);
                font-size:12px;
                font-weight:bold;
                margin-bottom:18px;">
                ✨ SMART OJT MANAGEMENT
            </div>

            <h1>
                Build Your Experience.<br>
                <span>Track Your Progress.</span>
            </h1>

            <p>
                A simple and organized way to manage your
                On-the-Job Training. Track attendance, record
                your work, submit reports, and monitor your progress
                in one place.
            </p>

            <div class="hero-buttons">
                <a href="{{ url_for('login') }}" class="primary-btn">
                    Get Started →
                </a>

                <a href="#features" class="secondary-btn">
                    Explore Features
                </a>
            </div>

        </div>


        <div class="preview-wrapper">

            <div class="preview-card">

                <div class="preview-top">
                    <div class="preview-title">
                        OJT Dashboard
                    </div>

                    <div class="preview-user">
                        👤
                    </div>
                </div>

                <div class="preview-welcome">
                    <h3>Good morning! 👋</h3>
                    <p>Here is your OJT progress today.</p>
                </div>

                <div class="preview-stats">

                    <div class="preview-stat">
                        <strong>120</strong>
                        <small>Hours Completed</small>
                    </div>

                    <div class="preview-stat">
                        <strong>85%</strong>
                        <small>Overall Progress</small>
                    </div>

                    <div class="preview-stat">
                        <strong>18</strong>
                        <small>Work Logs</small>
                    </div>

                    <div class="preview-stat">
                        <strong>12</strong>
                        <small>Attendance Days</small>
                    </div>

                </div>

                <div class="progress-box">

                    <strong>OJT Progress</strong>

                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        margin-top:8px;
                        font-size:12px;
                        color:#64748b;">
                        <span>120 / 150 Hours</span>
                        <strong style="color:#1769e0;">80%</strong>
                    </div>

                </div>

            </div>

        </div>

    </div>

</section>


<section class="features" id="features">

    <div class="features-title">

        <h2>Everything You Need for OJT</h2>

        <p>
            Simple tools to help students and supervisors stay organized.
        </p>

    </div>


    <div class="feature-grid">

        <div class="feature-card">

            <div class="feature-icon">🕒</div>

            <h3>Attendance</h3>

            <p>
                Record your daily time-in and time-out
                and keep your OJT attendance organized.
            </p>

        </div>


        <div class="feature-card">

            <div class="feature-icon">📝</div>

            <h3>Work Logs</h3>

            <p>
                Record the tasks you completed every day
                and submit work evidence for verification.
            </p>

        </div>


        <div class="feature-card">

            <div class="feature-icon">📊</div>

            <h3>Progress</h3>

            <p>
                Easily see your completed hours, verified
                work logs, reports, and overall OJT progress.
            </p>

        </div>

    </div>

</section>


<div class="footer">
    © 2026 OJT Tracker · Smart OJT Management System
</div>

</body>
</html>
"""


# =========================================================
# LOGIN PAGE
# =========================================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - OJT Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
""" + BASE_STYLE + """
</head>

<body>

<div class="login-page">

    <div class="login-card">

        <div class="login-logo">

            <div class="circle">🎓</div>

            <h2>Welcome Back</h2>

            <p>Login to your OJT Tracker account</p>

        </div>

        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="flash">{{ message }}</div>
            {% endfor %}
        {% endwith %}

        <form method="POST">

            <div class="form-group">
                <label>Email Address</label>

                <input
                    type="email"
                    name="email"
                    class="form-control"
                    autocomplete="email"
                    placeholder="Enter your email"
                    required>
            </div>

            <div class="form-group">
                <label>Password</label>

                <input
                    type="password"
                    name="password"
                    class="form-control"
                    autocomplete="current-password"
                    placeholder="Enter your password"
                    required>
            </div>

            <button class="full-btn" type="submit">
                Login
            </button>

        </form>

        <a href="{{ url_for('home') }}" class="back-link">
            ← Back to Home
        </a>

        <div style="
            margin-top:25px;
            padding:15px;
            background:#f7f9fc;
            border-radius:12px;
            font-size:12px;
            color:#64748b;">

            <strong>Demo Accounts</strong><br><br>

            Student: student@ojt.com<br>
            Adviser: adviser@ojt.com<br>
            Company: company@ojt.com<br>
            Admin: admin@ojt.com<br><br>

            Passwords:
            student123 / adviser123 /
            company123 / admin123

        </div>

    </div>

</div>

</body>
</html>
"""


# =========================================================
# APP TEMPLATE
# =========================================================

def app_template(content, active="Dashboard"):

    return """
<!DOCTYPE html>
<html>

<head>

<title>OJT Tracker</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

""" + BASE_STYLE + """

</head>

<body>

<div class="app-layout">

<aside class="sidebar">

    <div class="sidebar-logo">
        🎓 OJT<span>Tracker</span>
    </div>

    <div class="user-mini">
        <strong>{{ session.get('name') }}</strong>
        <small>{{ session.get('role') }}</small>
    </div>

    <div class="menu-title">Main Menu</div>

    <a class="menu-link {{ 'active' if active == 'Dashboard' else '' }}"
       href="{{ url_for('dashboard') }}">
       🏠 <span>Dashboard</span>
    </a>

    {% if session.get('role') == 'Student' %}

    <a class="menu-link {{ 'active' if active == 'Attendance' else '' }}"
       href="{{ url_for('attendance') }}">
       🕒 <span>Attendance</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Work Log' else '' }}"
       href="{{ url_for('work_logs') }}">
       📝 <span>Work Log</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Reports' else '' }}"
       href="{{ url_for('weekly_reports') }}">
       📄 <span>Weekly Reports</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Progress' else '' }}"
       href="{{ url_for('progress') }}">
       📊 <span>Progress</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Notifications' else '' }}"
       href="{{ url_for('notifications') }}">
       🔔 <span>Notifications</span>
    </a>

    {% elif session.get('role') == 'Company' %}

    <a class="menu-link {{ 'active' if active == 'Students' else '' }}"
       href="{{ url_for('company_students') }}">
       👨‍🎓 <span>OJT Students</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Verify' else '' }}"
       href="{{ url_for('verify_logs') }}">
       ✔️ <span>Verify Work Logs</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Evaluation' else '' }}"
       href="{{ url_for('company_evaluation') }}">
       ⭐ <span>Evaluation</span>
    </a>

    {% elif session.get('role') == 'Adviser' %}

    <a class="menu-link {{ 'active' if active == 'Students' else '' }}"
       href="{{ url_for('adviser_students') }}">
       👨‍🎓 <span>Students</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Reports' else '' }}"
       href="{{ url_for('adviser_reports') }}">
       📄 <span>Weekly Reports</span>
    </a>

    {% elif session.get('role') == 'Admin' %}

    <a class="menu-link {{ 'active' if active == 'Users' else '' }}"
       href="{{ url_for('admin_users') }}">
       👥 <span>Users</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Students' else '' }}"
       href="{{ url_for('admin_students') }}">
       🎓 <span>Students</span>
    </a>

    <a class="menu-link {{ 'active' if active == 'Reports' else '' }}"
       href="{{ url_for('admin_reports') }}">
       📊 <span>System Reports</span>
    </a>

    {% endif %}

    <a class="menu-link logout"
       href="{{ url_for('logout') }}">
       🚪 <span>Logout</span>
    </a>

</aside>


<main class="main">

    <div class="topbar">

        <h3>{{ active }}</h3>

        <div style="
            font-size:13px;
            color:#64748b;">
            {{ session.get('name') }}
        </div>

    </div>

    <div class="content">

        {{ content|safe }}

    </div>

</main>

</div>

</body>
</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template_string(LANDING_PAGE)


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            role = str(user["role"] or "").strip().lower()
            role_map = {
                "student": "Student",
                "company": "Company",
                "adviser": "Adviser",
                "admin": "Admin"
            }

            if role not in role_map:
                flash("Your account role is not configured correctly. Please contact the administrator.")
                return render_template_string(LOGIN_PAGE)

            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = role_map[role]
            session["company"] = user["company"]

            # Automatically open the correct dashboard after login.
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template_string(LOGIN_PAGE)


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# PROGRESS CALCULATION
# =========================================================

def calculate_progress(student_id):

    conn = get_db()

    attendance_count = conn.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id = ?
    """, (student_id,)).fetchone()["total"]

    verified_logs = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE student_id = ? AND status = 'Verified'
    """, (student_id,)).fetchone()["total"]

    reports = conn.execute("""
        SELECT COUNT(*) AS total
        FROM weekly_reports
        WHERE student_id = ?
    """, (student_id,)).fetchone()["total"]

    evaluation = conn.execute("""
        SELECT AVG(overall_score) AS score
        FROM evaluations
        WHERE student_id = ?
    """, (student_id,)).fetchone()["score"]

    conn.close()

    attendance_score = min(attendance_count / 30 * 100, 100)
    logs_score = min(verified_logs / 20 * 100, 100)
    reports_score = min(reports / 12 * 100, 100)
    evaluation_score = evaluation if evaluation else 0

    overall = (
        attendance_score * .30 +
        logs_score * .25 +
        reports_score * .20 +
        evaluation_score * .25
    )

    return round(overall), attendance_count, verified_logs, reports, evaluation_score


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    # Normalize the stored role so the correct dashboard always opens.
    role = str(session.get("role", "")).strip().lower()

    if role == "student":
        return student_dashboard()

    if role == "company":
        return company_dashboard()

    if role == "adviser":
        return adviser_dashboard()

    if role == "admin":
        return admin_dashboard()

    session.clear()
    flash("Your account role could not be recognized. Please log in again.")
    return redirect(url_for("login"))


# =========================================================
# STUDENT DASHBOARD
# =========================================================

def student_dashboard():

    student_id = session["user_id"]

    progress_data = calculate_progress(student_id)

    progress_value = progress_data[0]
    attendance_count = progress_data[1]
    verified_logs = progress_data[2]
    reports = progress_data[3]

    conn = get_db()

    application = conn.execute("""
        SELECT * FROM applications
        WHERE student_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (student_id,)).fetchone()

    recent_logs = conn.execute("""
        SELECT * FROM work_logs
        WHERE student_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (student_id,)).fetchall()

    conn.close()

    content = f"""

    <div class="page-title">
        <h2>Good day, {session['name']}! 👋</h2>
        <p>Here is your OJT progress overview.</p>
    </div>


    <div class="cards">

        <div class="card stat-card">
            <span class="stat-icon">🕒</span>
            <small>Attendance Days</small>
            <h2>{attendance_count}</h2>
        </div>

        <div class="card stat-card">
            <span class="stat-icon">📝</span>
            <small>Verified Work Logs</small>
            <h2>{verified_logs}</h2>
        </div>

        <div class="card stat-card">
            <span class="stat-icon">📄</span>
            <small>Weekly Reports</small>
            <h2>{reports}</h2>
        </div>

        <div class="card stat-card">
            <span class="stat-icon">📊</span>
            <small>Overall Progress</small>
            <h2>{progress_value}%</h2>
        </div>

    </div>


    <div class="section">

        <h3>OJT Progress</h3>

        <div style="
            display:flex;
            justify-content:space-between;
            margin-bottom:10px;">

            <span>Overall completion</span>

            <strong>{progress_value}%</strong>

        </div>

        <div class="big-progress">
            <div style="width:{progress_value}%"></div>
        </div>

    </div>


    <div class="section">

        <h3>Quick Actions</h3>
        <p style="color:#64748b;margin-top:-5px;">Use these buttons to quickly record your OJT activities.</p>

        <div class="quick-actions">
            <a class="quick-btn" href="{{ url_for('attendance') }}">🕒 <span><strong>Attendance</strong><small>Time in or out</small></span></a>
            <a class="quick-btn" href="{{ url_for('work_logs') }}">📝 <span><strong>Work Log</strong><small>Record your tasks</small></span></a>
            <a class="quick-btn" href="{{ url_for('weekly_reports') }}">📄 <span><strong>Weekly Report</strong><small>Submit your report</small></span></a>
            <a class="quick-btn" href="{{ url_for('progress') }}">📊 <span><strong>Progress</strong><small>View your progress</small></span></a>
        </div>

    </div>


    <div class="section">

        <h3>OJT Information</h3>

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Company</th>
                <td>{application['company'] if application else 'Not yet assigned'}</td>
            </tr>

            <tr>
                <th>Position</th>
                <td>{application['position'] if application else '—'}</td>
            </tr>

            <tr>
                <th>Start Date</th>
                <td>{application['start_date'] if application else '—'}</td>
            </tr>

            <tr>
                <th>End Date</th>
                <td>{application['end_date'] if application else '—'}</td>
            </tr>

            <tr>
                <th>Status</th>
                <td>
                    <span class="status good">
                    {application['status'] if application else 'Pending'}
                    </span>
                </td>
            </tr>

        </table>

        </div>

    </div>


    <div class="section">

        <h3>Recent Work Logs</h3>

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Date</th>
                <th>Task</th>
                <th>Status</th>
            </tr>

            {''.join([
                f"<tr><td>{x['date']}</td>"
                f"<td>{x['task']}</td>"
                f"<td><span class='status {'good' if x['status']=='Verified' else ''}'>{x['status']}</span></td></tr>"
                for x in recent_logs
            ]) if recent_logs else
            "<tr><td colspan='3'>No work logs yet.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Dashboard")
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance", methods=["GET", "POST"])
@role_required("Student")
def attendance():

    student_id = session["user_id"]

    conn = get_db()

    if request.method == "POST":

        action = request.form.get("action")

        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        location = request.form.get("location", "OJT Workplace")

        existing = conn.execute("""
            SELECT * FROM attendance
            WHERE student_id = ? AND date = ?
        """, (student_id, today)).fetchone()

        if action == "time_in":

            if existing:
                flash("You already timed in today.")
            else:

                conn.execute("""
                    INSERT INTO attendance
                    (student_id, date, time_in, location)
                    VALUES (?, ?, ?, ?)
                """, (
                    student_id,
                    today,
                    current_time,
                    location
                ))

                conn.commit()

                flash("Time-in recorded successfully.")

        elif action == "time_out":

            if not existing:
                flash("Please time in first.")

            elif existing["time_out"]:
                flash("You already timed out today.")

            else:

                conn.execute("""
                    UPDATE attendance
                    SET time_out = ?
                    WHERE id = ?
                """, (
                    current_time,
                    existing["id"]
                ))

                conn.commit()

                flash("Time-out recorded successfully.")

    records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (student_id,)).fetchall()

    conn.close()

    rows = ""

    for row in records:

        rows += f"""
        <tr>
            <td>{row['date']}</td>
            <td>{row['time_in'] or '—'}</td>
            <td>{row['time_out'] or '—'}</td>
            <td>{row['location'] or '—'}</td>
            <td>
                <span class="status good">
                    {row['status']}
                </span>
            </td>
        </tr>
        """

    content = f"""

    <div class="page-title">
        <h2>Attendance</h2>
        <p>Record your daily OJT attendance.</p>
    </div>

    <div class="section">

        <h3>Today's Attendance</h3>

        <form method="POST">

            <div class="form-group">
                <label>Workplace / Location</label>

                <input
                    class="form-control"
                    name="location"
                    placeholder="Example: Tech Solutions Office"
                    required>
            </div>

            <div style="display:flex;gap:10px;">

                <button
                    class="full-btn"
                    name="action"
                    value="time_in"
                    type="submit">
                    🟢 Time In
                </button>

                <button
                    class="full-btn"
                    name="action"
                    value="time_out"
                    type="submit">
                    🔴 Time Out
                </button>

            </div>

        </form>

    </div>


    <div class="section">

        <h3>Attendance History</h3>

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Date</th>
                <th>Time In</th>
                <th>Time Out</th>
                <th>Location</th>
                <th>Status</th>
            </tr>

            {rows}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Attendance")
    )


# =========================================================
# WORK LOGS
# =========================================================

@app.route("/work-logs", methods=["GET", "POST"])
@role_required("Student")
def work_logs():

    student_id = session["user_id"]

    conn = get_db()

    if request.method == "POST":

        date = request.form.get("date")
        task = request.form.get("task")
        description = request.form.get("description")
        evidence = request.form.get("evidence")

        conn.execute("""
            INSERT INTO work_logs
            (student_id, date, task, description, evidence)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            date,
            task,
            description,
            evidence
        ))

        conn.commit()

        flash("Work log submitted successfully.")

    logs = conn.execute("""
        SELECT * FROM work_logs
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,)).fetchall()

    conn.close()

    rows = ""

    for log in logs:

        rows += f"""
        <tr>
            <td>{log['date']}</td>
            <td>{log['task']}</td>
            <td>{log['description']}</td>
            <td>{log['evidence'] or '—'}</td>
            <td>
                <span class="status {'good' if log['status']=='Verified' else ''}">
                    {log['status']}
                </span>
            </td>
        </tr>
        """

    content = f"""

    <div class="page-title">
        <h2>Work Log</h2>
        <p>Record the tasks you completed during OJT.</p>
    </div>


    <div class="section">

        <h3>Add Today's Work</h3>

        <form method="POST">

            <div class="form-group">
                <label>Date</label>
                <input
                    type="date"
                    name="date"
                    class="form-control"
                    value="{datetime.now().strftime('%Y-%m-%d')}"
                    required>
            </div>

            <div class="form-group">
                <label>Task</label>
                <input
                    type="text"
                    name="task"
                    class="form-control"
                    placeholder="Example: Computer troubleshooting"
                    required>
            </div>

            <div class="form-group">
                <label>Description</label>
                <textarea
                    name="description"
                    class="form-control"
                    rows="4"
                    placeholder="Describe what you did..."
                    required></textarea>
            </div>

            <div class="form-group">
                <label>Work Evidence</label>
                <input
                    type="text"
                    name="evidence"
                    class="form-control"
                    placeholder="Example: Screenshot, document, task output">
            </div>

            <button class="full-btn" type="submit">
                Submit Work Log
            </button>

        </form>

    </div>


    <div class="section">

        <h3>My Work Logs</h3>

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Date</th>
                <th>Task</th>
                <th>Description</th>
                <th>Evidence</th>
                <th>Status</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='5'>No work logs submitted yet.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Work Log")
    )


# =========================================================
# WEEKLY REPORTS
# =========================================================

@app.route("/weekly-reports", methods=["GET", "POST"])
@role_required("Student")
def weekly_reports():

    student_id = session["user_id"]

    conn = get_db()

    if request.method == "POST":

        week = request.form.get("week")
        summary = request.form.get("summary")
        challenges = request.form.get("challenges")
        learnings = request.form.get("learnings")

        conn.execute("""
            INSERT INTO weekly_reports
            (student_id, week, summary, challenges, learnings)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            week,
            summary,
            challenges,
            learnings
        ))

        conn.commit()

        flash("Weekly report submitted.")

    reports = conn.execute("""
        SELECT * FROM weekly_reports
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,)).fetchall()

    conn.close()

    rows = ""

    for report in reports:

        rows += f"""
        <tr>
            <td>{report['week']}</td>
            <td>{report['summary']}</td>
            <td>
                <span class="status good">
                    {report['status']}
                </span>
            </td>
        </tr>
        """

    content = f"""

    <div class="page-title">
        <h2>Weekly Reports</h2>
        <p>Submit a summary of your OJT activities each week.</p>
    </div>


    <div class="section">

        <h3>Submit Weekly Report</h3>

        <form method="POST">

            <div class="form-group">
                <label>Week</label>

                <input
                    type="text"
                    name="week"
                    class="form-control"
                    placeholder="Example: Week 4"
                    required>
            </div>

            <div class="form-group">
                <label>Summary of Activities</label>

                <textarea
                    name="summary"
                    class="form-control"
                    rows="4"
                    required></textarea>
            </div>

            <div class="form-group">
                <label>Challenges</label>

                <textarea
                    name="challenges"
                    class="form-control"
                    rows="3"></textarea>
            </div>

            <div class="form-group">
                <label>What I Learned</label>

                <textarea
                    name="learnings"
                    class="form-control"
                    rows="3"></textarea>
            </div>

            <button class="full-btn">
                Submit Report
            </button>

        </form>

    </div>


    <div class="section">

        <h3>Submitted Reports</h3>

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Week</th>
                <th>Summary</th>
                <th>Status</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='3'>No reports submitted yet.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Reports")
    )


# =========================================================
# PROGRESS
# =========================================================

@app.route("/progress")
@role_required("Student")
def progress():

    data = calculate_progress(session["user_id"])

    overall = data[0]
    attendance_count = data[1]
    verified_logs = data[2]
    reports = data[3]
    evaluation = round(data[4])

    content = f"""

    <div class="page-title">

        <h2>My Progress</h2>

        <p>
            Your OJT progress based on attendance,
            work logs, reports, and evaluation.
        </p>

    </div>


    <div class="section">

        <h3>Overall Progress</h3>

        <div style="
            text-align:center;
            padding:25px;">

            <div style="
                font-size:55px;
                font-weight:800;
                color:#1769e0;">
                {overall}%
            </div>

            <p style="color:#64748b;">
                OJT Completion Score
            </p>

        </div>

        <div class="big-progress">
            <div style="width:{overall}%"></div>
        </div>

    </div>


    <div class="cards">

        <div class="card">

            <small>Attendance</small>

            <h2>{attendance_count}</h2>

            <p style="color:#64748b;font-size:13px;">
                30% of progress
            </p>

        </div>


        <div class="card">

            <small>Verified Work Logs</small>

            <h2>{verified_logs}</h2>

            <p style="color:#64748b;font-size:13px;">
                25% of progress
            </p>

        </div>


        <div class="card">

            <small>Weekly Reports</small>

            <h2>{reports}</h2>

            <p style="color:#64748b;font-size:13px;">
                20% of progress
            </p>

        </div>


        <div class="card">

            <small>Evaluation</small>

            <h2>{evaluation}%</h2>

            <p style="color:#64748b;font-size:13px;">
                25% of progress
            </p>

        </div>

    </div>


    <div class="section">

        <h3>Status</h3>

        <p>

            {"🟢 Good Standing — Keep up the good work!" if overall >= 70
            else "🟡 Monitor — You need to improve your OJT progress." if overall >= 40
            else "🔴 At Risk — Please complete your OJT requirements."}

        </p>

    </div>
    """

    return render_template_string(
        app_template(content, "Progress")
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
@role_required("Student")
def notifications():

    conn = get_db()

    notes = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    rows = ""

    for note in notes:

        rows += f"""
        <div class="card" style="margin-bottom:10px;">
            <strong>🔔 Notification</strong>

            <p style="color:#64748b;">
                {note['message']}
            </p>

            <small>{note['date']}</small>
        </div>
        """

    if not rows:
        rows = """
        <div class="section" style="text-align:center;">
            <div style="font-size:40px;">🔔</div>
            <h3>No Notifications</h3>
            <p style="color:#64748b;">
                You don't have any notifications yet.
            </p>
        </div>
        """

    content = f"""

    <div class="page-title">

        <h2>Notifications</h2>

        <p>
            Important updates about your OJT.
        </p>

    </div>

    {rows}

    """

    return render_template_string(
        app_template(content, "Notifications")
    )


# =========================================================
# COMPANY DASHBOARD
# =========================================================

def company_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
        AND company = ?
    """, (session.get("company"),)).fetchall()

    pending = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs w
        JOIN users u ON w.student_id = u.id
        WHERE u.company = ?
        AND w.status = 'Pending'
    """, (session.get("company"),)).fetchone()["total"]

    conn.close()

    content = f"""

    <div class="page-title">

        <h2>Company Dashboard</h2>

        <p>
            Monitor your OJT students and verify their work.
        </p>

    </div>


    <div class="cards">

        <div class="card stat-card">
            <small>OJT Students</small>
            <h2>{len(students)}</h2>
            <span class="stat-icon">👨‍🎓</span>
        </div>

        <div class="card stat-card">
            <small>Pending Verification</small>
            <h2>{pending}</h2>
            <span class="stat-icon">✔️</span>
        </div>

    </div>


    <div class="section">

        <h3>Quick Actions</h3>

        <div style="display:flex;gap:12px;flex-wrap:wrap;">

            <a href="{{ url_for('company_students') }}"
               class="primary-btn"
               style="background:#1769e0;color:white;">
                👨‍🎓 View Students
            </a>

            <a href="{{ url_for('verify_logs') }}"
               class="primary-btn"
               style="background:#1769e0;color:white;">
                ✔️ Verify Work Logs
            </a>

            <a href="{{ url_for('company_evaluation') }}"
               class="primary-btn"
               style="background:#1769e0;color:white;">
                ⭐ Evaluation
            </a>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Dashboard")
    )


# =========================================================
# COMPANY STUDENTS
# =========================================================

@app.route("/company/students")
@role_required("Company")
def company_students():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
        AND company = ?
    """, (session.get("company"),)).fetchall()

    conn.close()

    rows = ""

    for student in students:

        p = calculate_progress(student["id"])[0]

        rows += f"""
        <tr>
            <td>{student['name']}</td>
            <td>{student['email']}</td>
            <td>{student['course']}</td>
            <td>{p}%</td>
            <td>
                <span class="status good">
                    Active
                </span>
            </td>
        </tr>
        """

    content = f"""

    <div class="page-title">

        <h2>OJT Students</h2>

        <p>
            Students assigned to your company.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Course</th>
                <th>Progress</th>
                <th>Status</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='5'>No students assigned.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Students")
    )


# =========================================================
# VERIFY WORK LOGS
# =========================================================

@app.route("/company/verify", methods=["GET", "POST"])
@role_required("Company")
def verify_logs():

    conn = get_db()

    if request.method == "POST":

        log_id = request.form.get("log_id")

        conn.execute("""
            UPDATE work_logs
            SET status = 'Verified'
            WHERE id = ?
        """, (log_id,))

        conn.commit()

        flash("Work log verified.")

    logs = conn.execute("""
        SELECT
            work_logs.*,
            users.name
        FROM work_logs
        JOIN users
        ON work_logs.student_id = users.id
        WHERE users.company = ?
        ORDER BY work_logs.id DESC
    """, (session.get("company"),)).fetchall()

    conn.close()

    rows = ""

    for log in logs:

        action = ""

        if log["status"] == "Pending":

            action = f"""
            <form method="POST">

                <input
                    type="hidden"
                    name="log_id"
                    value="{log['id']}">

                <button
                    class="full-btn"
                    style="padding:8px;"
                    type="submit">
                    Verify
                </button>

            </form>
            """

        else:

            action = """
            <span class="status good">
                Verified
            </span>
            """

        rows += f"""
        <tr>

            <td>{log['name']}</td>

            <td>{log['date']}</td>

            <td>{log['task']}</td>

            <td>{log['description']}</td>

            <td>{log['evidence'] or '—'}</td>

            <td>{action}</td>

        </tr>
        """

    content = f"""

    <div class="page-title">

        <h2>Verify Work Logs</h2>

        <p>
            Check and verify the work completed by your OJT students.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Student</th>
                <th>Date</th>
                <th>Task</th>
                <th>Description</th>
                <th>Evidence</th>
                <th>Action</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='6'>No work logs found.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Verify")
    )


# =========================================================
# COMPANY EVALUATION
# =========================================================

@app.route("/company/evaluation", methods=["GET", "POST"])
@role_required("Company")
def company_evaluation():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
        AND company = ?
    """, (session.get("company"),)).fetchall()

    if request.method == "POST":

        student_id = request.form.get("student_id")

        attendance_score = int(
            request.form.get("attendance_score", 0)
        )

        performance_score = int(
            request.form.get("performance_score", 0)
        )

        attitude_score = int(
            request.form.get("attitude_score", 0)
        )

        comments = request.form.get("comments")

        overall = round(
            (attendance_score +
             performance_score +
             attitude_score) / 3
        )

        conn.execute("""
            INSERT INTO evaluations
            (
                student_id,
                evaluator,
                attendance_score,
                performance_score,
                attitude_score,
                overall_score,
                comments
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            session["name"],
            attendance_score,
            performance_score,
            attitude_score,
            overall,
            comments
        ))

        conn.commit()

        flash("Evaluation submitted.")

    conn.close()

    student_options = ""

    for student in students:

        student_options += f"""
        <option value="{student['id']}">
            {student['name']}
        </option>
        """

    content = f"""

    <div class="page-title">

        <h2>Student Evaluation</h2>

        <p>
            Evaluate the student's OJT performance.
        </p>

    </div>


    <div class="section">

        <form method="POST">

            <div class="form-group">

                <label>Student</label>

                <select
                    name="student_id"
                    class="form-control"
                    required>

                    {student_options}

                </select>

            </div>


            <div class="form-group">

                <label>Attendance Score (0-100)</label>

                <input
                    type="number"
                    name="attendance_score"
                    class="form-control"
                    min="0"
                    max="100"
                    required>

            </div>


            <div class="form-group">

                <label>Performance Score (0-100)</label>

                <input
                    type="number"
                    name="performance_score"
                    class="form-control"
                    min="0"
                    max="100"
                    required>

            </div>


            <div class="form-group">

                <label>Attitude Score (0-100)</label>

                <input
                    type="number"
                    name="attitude_score"
                    class="form-control"
                    min="0"
                    max="100"
                    required>

            </div>


            <div class="form-group">

                <label>Comments</label>

                <textarea
                    name="comments"
                    class="form-control"
                    rows="4"></textarea>

            </div>


            <button class="full-btn">
                Submit Evaluation
            </button>

        </form>

    </div>
    """

    return render_template_string(
        app_template(content, "Evaluation")
    )


# =========================================================
# ADVISER DASHBOARD
# =========================================================

def adviser_dashboard():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
    """).fetchall()

    reports = conn.execute("""
        SELECT COUNT(*) AS total
        FROM weekly_reports
    """).fetchone()["total"]

    conn.close()

    content = f"""

    <div class="page-title">

        <h2>Adviser Dashboard</h2>

        <p>
            Monitor student OJT progress.
        </p>

    </div>


    <div class="cards">

        <div class="card stat-card">

            <small>Total Students</small>

            <h2>{len(students)}</h2>

            <span class="stat-icon">👨‍🎓</span>

        </div>


        <div class="card stat-card">

            <small>Weekly Reports</small>

            <h2>{reports}</h2>

            <span class="stat-icon">📄</span>

        </div>

    </div>


    <div class="section">

        <h3>Monitoring</h3>

        <p style="color:#64748b;">
            Check student attendance, work logs,
            reports, and progress from the Students page.
        </p>

        <a href="{{ url_for('adviser_students') }}"
           class="primary-btn"
           style="background:#1769e0;color:white;">
            View Students
        </a>

    </div>
    """

    return render_template_string(
        app_template(content, "Dashboard")
    )


# =========================================================
# ADVISER STUDENTS
# =========================================================

@app.route("/adviser/students")
@role_required("Adviser")
def adviser_students():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
    """).fetchall()

    conn.close()

    rows = ""

    for student in students:

        data = calculate_progress(student["id"])

        status = (
            "Good Standing"
            if data[0] >= 70
            else "Monitor"
            if data[0] >= 40
            else "At Risk"
        )

        status_class = (
            "good"
            if data[0] >= 70
            else "warning"
        )

        rows += f"""

        <tr>

            <td>{student['name']}</td>

            <td>{student['course']}</td>

            <td>{student['company']}</td>

            <td>{data[0]}%</td>

            <td>
                <span class="status {status_class}">
                    {status}
                </span>
            </td>

        </tr>

        """

    content = f"""

    <div class="page-title">

        <h2>Student Monitoring</h2>

        <p>
            Monitor the progress of all OJT students.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Student</th>
                <th>Course</th>
                <th>Company</th>
                <th>Progress</th>
                <th>Status</th>
            </tr>

            {rows}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Students")
    )


# =========================================================
# ADVISER REPORTS
# =========================================================

@app.route("/adviser/reports")
@role_required("Adviser")
def adviser_reports():

    conn = get_db()

    reports = conn.execute("""
        SELECT
            weekly_reports.*,
            users.name
        FROM weekly_reports
        JOIN users
        ON weekly_reports.student_id = users.id
        ORDER BY weekly_reports.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for report in reports:

        rows += f"""

        <tr>

            <td>{report['name']}</td>

            <td>{report['week']}</td>

            <td>{report['summary']}</td>

            <td>
                <span class="status good">
                    {report['status']}
                </span>
            </td>

        </tr>

        """

    content = f"""

    <div class="page-title">

        <h2>Weekly Reports</h2>

        <p>
            Review submitted student reports.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Student</th>
                <th>Week</th>
                <th>Summary</th>
                <th>Status</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='4'>No reports available.</td></tr>"}

        </table>

        </div>

    </div>
    """

    return render_template_string(
        app_template(content, "Reports")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard():

    conn = get_db()

    users = conn.execute(
        "SELECT COUNT(*) AS total FROM users"
    ).fetchone()["total"]

    students = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'Student'
    """).fetchone()["total"]

    companies = conn.execute("""
        SELECT COUNT(*) AS total
        FROM users
        WHERE role = 'Company'
    """).fetchone()["total"]

    reports = conn.execute(
        "SELECT COUNT(*) AS total FROM weekly_reports"
    ).fetchone()["total"]

    conn.close()

    content = f"""

    <div class="page-title">

        <h2>Admin Dashboard</h2>

        <p>
            Manage the OJT monitoring system.
        </p>

    </div>


    <div class="cards">

        <div class="card stat-card">

            <small>Total Users</small>

            <h2>{users}</h2>

            <span class="stat-icon">👥</span>

        </div>


        <div class="card stat-card">

            <small>Students</small>

            <h2>{students}</h2>

            <span class="stat-icon">🎓</span>

        </div>


        <div class="card stat-card">

            <small>Companies</small>

            <h2>{companies}</h2>

            <span class="stat-icon">🏢</span>

        </div>


        <div class="card stat-card">

            <small>Reports</small>

            <h2>{reports}</h2>

            <span class="stat-icon">📄</span>

        </div>

    </div>


    <div class="section">

        <h3>System Management</h3>

        <p style="color:#64748b;">
            Use the sidebar to manage users, students,
            and system reports.
        </p>

    </div>

    """

    return render_template_string(
        app_template(content, "Dashboard")
    )


# =========================================================
# ADMIN USERS
# =========================================================

@app.route("/admin/users")
@role_required("Admin")
def admin_users():

    conn = get_db()

    users = conn.execute("""
        SELECT id, name, email, role, course, company
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for user in users:

        rows += f"""

        <tr>

            <td>{user['name']}</td>

            <td>{user['email']}</td>

            <td>{user['role']}</td>

            <td>{user['course'] or '—'}</td>

            <td>{user['company'] or '—'}</td>

        </tr>

        """

    content = f"""

    <div class="page-title">

        <h2>Users</h2>

        <p>
            View all registered system accounts.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Course</th>
                <th>Company</th>
            </tr>

            {rows}

        </table>

        </div>

    </div>

    """

    return render_template_string(
        app_template(content, "Users")
    )


# =========================================================
# ADMIN STUDENTS
# =========================================================

@app.route("/admin/students")
@role_required("Admin")
def admin_students():

    conn = get_db()

    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Student'
    """).fetchall()

    conn.close()

    rows = ""

    for student in students:

        data = calculate_progress(student["id"])

        rows += f"""

        <tr>

            <td>{student['name']}</td>

            <td>{student['email']}</td>

            <td>{student['course']}</td>

            <td>{student['company']}</td>

            <td>{data[0]}%</td>

        </tr>

        """

    content = f"""

    <div class="page-title">

        <h2>Students</h2>

        <p>
            View OJT student information and progress.
        </p>

    </div>


    <div class="section">

        <div class="table-wrapper">

        <table>

            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Course</th>
                <th>Company</th>
                <th>Progress</th>
            </tr>

            {rows if rows else
            "<tr><td colspan='5'>No students found.</td></tr>"}

        </table>

        </div>

    </div>

    """

    return render_template_string(
        app_template(content, "Students")
    )


# =========================================================
# ADMIN REPORTS
# =========================================================

@app.route("/admin/reports")
@role_required("Admin")
def admin_reports():

    conn = get_db()

    attendance = conn.execute(
        "SELECT COUNT(*) AS total FROM attendance"
    ).fetchone()["total"]

    work_logs = conn.execute(
        "SELECT COUNT(*) AS total FROM work_logs"
    ).fetchone()["total"]

    verified = conn.execute("""
        SELECT COUNT(*) AS total
        FROM work_logs
        WHERE status = 'Verified'
    """).fetchone()["total"]

    weekly = conn.execute(
        "SELECT COUNT(*) AS total FROM weekly_reports"
    ).fetchone()["total"]

    evaluations = conn.execute(
        "SELECT COUNT(*) AS total FROM evaluations"
    ).fetchone()["total"]

    conn.close()

    content = f"""

    <div class="page-title">

        <h2>System Reports</h2>

        <p>
            Overall activity in the OJT monitoring system.
        </p>

    </div>


    <div class="cards">

        <div class="card">
            <small>Attendance Records</small>
            <h2>{attendance}</h2>
        </div>

        <div class="card">
            <small>Total Work Logs</small>
            <h2>{work_logs}</h2>
        </div>

        <div class="card">
            <small>Verified Work Logs</small>
            <h2>{verified}</h2>
        </div>

        <div class="card">
            <small>Weekly Reports</small>
            <h2>{weekly}</h2>
        </div>

    </div>


    <div class="section">

        <h3>Evaluations</h3>

        <p>
            Total submitted evaluations:
            <strong>{evaluations}</strong>
        </p>

    </div>

    """

    return render_template_string(
        app_template(content, "Reports")
    )


# =========================================================
# START APPLICATION
# =========================================================

# Initialize the database when the application module is loaded.
init_db()

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )