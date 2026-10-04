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
        return f(*args,