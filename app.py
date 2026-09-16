from flask import Flask, request, redirect, session, url_for, render_template_string
import sqlite3
import datetime
import random
import string
import os
import html
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ============================================================
# SETTINGS
# ============================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "schoolsafe-demo-secret-change-this"
)

DB_FILE = "schoolsafe.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # REPORTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            reporter TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            urgency TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            remarks TEXT DEFAULT '',
            date_reported TEXT NOT NULL,
            time_reported TEXT NOT NULL,
            photo TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)

    # ANNOUNCEMENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            date_posted TEXT NOT NULL
        )
    """)

    # REPORT TIMELINE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT NOT NULL,
            status TEXT NOT NULL,
            remarks TEXT DEFAULT '',
            date_updated TEXT NOT NULL,
            time_updated TEXT NOT NULL
        )
    """)

    # SETTINGS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            admin_username TEXT NOT NULL,
            admin_password TEXT NOT NULL
        )
    """)

    # Create default settings
    existing = cursor.execute(
        "SELECT id FROM settings WHERE id = 1"
    ).fetchone()

    if not existing:
        cursor.execute("""
            INSERT INTO settings
            (id, admin_username, admin_password)
            VALUES (1, ?, ?)
        """, (
            ADMIN_USERNAME,
            ADMIN_PASSWORD
        ))

    # --------------------------------------------------------
    # DATABASE MIGRATION FOR OLDER VERSIONS
    # --------------------------------------------------------

    columns = [
        ("photo", "TEXT DEFAULT ''"),
        ("updated_at", "TEXT DEFAULT ''")
    ]

    existing_columns = [
        row["name"]
        for row in cursor.execute("PRAGMA table_info(reports)").fetchall()
    ]

    for column_name, column_type in columns:

        if column_name not in existing_columns:

            cursor.execute(
                f"ALTER TABLE reports ADD COLUMN {column_name} {column_type}"
            )

    conn.commit()
    conn.close()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe(value):
    return html.escape(str(value or ""))


def admin_required():

    return session.get("admin_logged_in") is True


def get_admin_credentials():

    conn = get_db()

    row = conn.execute("""
        SELECT admin_username, admin_password
        FROM settings
        WHERE id = 1
    """).fetchone()

    conn.close()

    if row:
        return row["admin_username"], row["admin_password"]

    return ADMIN_USERNAME, ADMIN_PASSWORD


def generate_report_id():

    conn = get_db()

    while True:

        code = "SS-" + "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        existing = conn.execute(
            "SELECT id FROM reports WHERE report_id = ?",
            (code,)
        ).fetchone()

        if not existing:

            conn.close()
            return code


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def urgency_class(urgency):

    return str(urgency or "").lower()


def status_class(status):

    value = str(status or "").lower()

    if value == "under review":
        return "review"

    if value == "in progress":
        return "progress"

    if value == "resolved":
        return "resolved"

    return "submitted"


def add_history(report_id, status, remarks=""):

    now = datetime.datetime.now()

    date_updated = now.strftime("%Y-%m-%d")
    time_updated = now.strftime("%I:%M %p")

    conn = get_db()

    conn.execute("""
        INSERT INTO report_history
        (
            report_id,
            status,
            remarks,
            date_updated,
            time_updated
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        report_id,
        status,
        remarks,
        date_updated,
        time_updated
    ))

    conn.commit()
    conn.close()


# ============================================================
# CSS
# ============================================================

CSS = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f8ff;
    color: #172033;
}

a {
    text-decoration: none;
}

.navbar {
    background: linear-gradient(135deg, #0757c9, #0b76ff);
    color: white;
    padding: 16px 6%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 3px 15px rgba(0,0,0,.12);
    position: sticky;
    top: 0;
    z-index: 100;
}

.logo {
    font-size: 24px;
    font-weight: bold;
}

.logo span {
    color: #dff0ff;
}

.nav-links {
    display: flex;
    gap: 7px;
    align-items: center;
    flex-wrap: wrap;
}

.nav-links a {
    color: white;
    padding: 9px 13px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
}

.nav-links a:hover {
    background: rgba(255,255,255,.18);
}

.container {
    width: 92%;
    max-width: 1250px;
    margin: 30px auto;
}

.hero {
    background: linear-gradient(135deg, #0757c9, #1284ff);
    color: white;
    padding: 50px 25px;
    border-radius: 22px;
    text-align: center;
    box-shadow: 0 12px 30px rgba(0,80,190,.2);
}

.hero h1 {
    font-size: 42px;
    margin: 0 0 12px;
    color: white;
}

.hero p {
    font-size: 18px;
    margin-bottom: 25px;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 20px;
    margin-top: 25px;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 25px;
    box-shadow: 0 7px 25px rgba(0,0,0,.07);
    border: 1px solid #e3ecfa;
}

.card:hover {
    transform: translateY(-2px);
    transition: .2s;
}

.role-card {
    text-align: center;
    cursor: pointer;
}

.icon {
    font-size: 45px;
    margin-bottom: 10px;
}

h1, h2, h3 {
    color: #12345b;
}

.btn {
    display: inline-block;
    border: none;
    cursor: pointer;
    padding: 11px 18px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 14px;
    margin: 4px;
}

.btn-primary {
    background: #0866e8;
    color: white;
}

.btn-primary:hover {
    background: #034fae;
}

.btn-light {
    background: white;
    color: #0757c9;
}

.btn-danger {
    background: #dc3545;
    color: white;
}

.btn-success {
    background: #198754;
    color: white;
}

.btn-warning {
    background: #ffb000;
    color: #222;
}

.btn-secondary {
    background: #64748b;
    color: white;
}

.form-card {
    background: white;
    max-width: 780px;
    margin: auto;
    padding: 35px;
    border-radius: 18px;
    box-shadow: 0 8px 28px rgba(0,0,0,.08);
}

.form-group {
    margin-bottom: 18px;
}

label {
    display: block;
    font-weight: bold;
    margin-bottom: 7px;
}

input,
select,
textarea {
    width: 100%;
    padding: 13px;
    border: 1px solid #cdd9e8;
    border-radius: 9px;
    font-size: 15px;
    outline: none;
}

input:focus,
select:focus,
textarea:focus {
    border-color: #0875ed;
    box-shadow: 0 0 0 3px rgba(8,117,237,.1);
}

textarea {
    min-height: 130px;
    resize: vertical;
}

.alert {
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 20px;
}

.alert-success {
    background: #d1e7dd;
    color: #0f5132;
}

.alert-danger {
    background: #f8d7da;
    color: #842029;
}

.alert-info {
    background: #cff4fc;
    color: #055160;
}

.report-id {
    font-size: 30px;
    font-weight: bold;
    color: #0757c9;
    background: #eef6ff;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    margin: 20px 0;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.stat {
    background: white;
    padding: 22px;
    border-radius: 15px;
    box-shadow: 0 5px 18px rgba(0,0,0,.06);
    border-left: 5px solid #0875ed;
}

.stat-number {
    font-size: 30px;
    font-weight: bold;
    color: #0757c9;
}

.stat-title {
    color: #667085;
    margin-top: 5px;
}

.table-container {
    background: white;
    padding: 20px;
    border-radius: 18px;
    overflow-x: auto;
    box-shadow: 0 7px 25px rgba(0,0,0,.07);
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 1050px;
}

th {
    background: #0757c9;
    color: white;
    padding: 13px;
    text-align: left;
}

td {
    padding: 13px;
    border-bottom: 1px solid #e8edf5;
    vertical-align: top;
}

tr:hover {
    background: #f7fbff;
}

.badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}

.submitted {
    background: #e2e3e5;
    color: #333;
}

.review {
    background: #cff4fc;
    color: #055160;
}

.progress {
    background: #fff3cd;
    color: #664d03;
}

.resolved {
    background: #d1e7dd;
    color: #0f5132;
}

.low {
    background: #d1e7dd;
    color: #0f5132;
}

.medium {
    background: #fff3cd;
    color: #664d03;
}

.high {
    background: #f8d7da;
    color: #842029;
}

.emergency {
    background: #b02a37;
    color: white;
}

.emergency-row {
    border-left: 6px solid #b02a37;
    background: #fff5f5;
}

.description-box {
    background: #f7faff;
    border-left: 4px solid #0875ed;
    padding: 15px;
    border-radius: 8px;
    white-space: pre-wrap;
    line-height: 1.6;
}

.photo-preview {
    max-width: 300px;
    max-height: 250px;
    border-radius: 12px;
    border: 1px solid #dce5f2;
    margin-top: 10px;
}

.steps {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin: 30px 0;
}

.step {
    flex: 1;
    text-align: center;
    padding: 15px 5px;
    border-radius: 10px;
    background: #e9eef7;
    color: #68758a;
    font-size: 13px;
    font-weight: bold;
}

.step.active {
    background: #0875ed;
    color: white;
}

.tip {
    background: #eef6ff;
    border-left: 5px solid #0875ed;
    padding: 15px;
    margin: 12px 0;
    border-radius: 8px;
}

.footer {
    text-align: center;
    padding: 30px;
    color: #718096;
    margin-top: 50px;
}

.empty {
    text-align: center;
    padding: 40px;
    color: #718096;
}

.search-box {
    background: white;
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 20px;
    box-shadow: 0 5px 18px rgba(0,0,0,.05);
}

.timeline {
    border-left: 4px solid #0875ed;
    margin: 25px 10px;
    padding-left: 25px;
}

.timeline-item {
    position: relative;
    background: white;
    padding: 18px;
    margin-bottom: 18px;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,.06);
}

.timeline-item::before {
    content: "";
    position: absolute;
    left: -34px;
    top: 22px;
    width: 14px;
    height: 14px;
    background: #0875ed;
    border-radius: 50%;
}

.big-status {
    text-align: center;
    padding: 20px;
    background: #eef6ff;
    border-radius: 15px;
    margin: 20px 0;
}

.big-status .badge {
    font-size: 16px;
    padding: 10px 18px;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 15px;
}

.detail-item {
    background: #f7faff;
    padding: 15px;
    border-radius: 10px;
}

.detail-label {
    font-size: 12px;
    color: #667085;
    font-weight: bold;
    text-transform: uppercase;
}

.detail-value {
    margin-top: 5px;
    font-weight: bold;
}

.progress-bar {
    height: 12px;
    background: #e5eaf2;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 10px;
}

.progress-fill {
    height: 100%;
    background: #0875ed;
}

@media(max-width: 700px) {

    .navbar {
        flex-direction: column;
        gap: 12px;
    }

    .nav-links {
        justify-content: center;
    }

    .hero h1 {
        font-size: 30px;
    }

    .steps {
        flex-direction: column;
    }

    .form-card {
        padding: 22px;
    }

    .container {
        width: 95%;
    }
}

</style>
"""


# ============================================================
# PAGE TEMPLATE
# ============================================================

def page(title, content, nav=True):

    navbar = ""

    if nav:

        if admin_required():

            navbar = """
            <div class="navbar">

                <div class="logo">
                    🛡️ School<span>Safe</span>
                </div>

                <div class="nav-links">

                    <a href="/admin/dashboard">
                        📊 Dashboard
                    </a>

                    <a href="/admin/reports">
                        📋 Reports
                    </a>

                    <a href="/admin/announcements">
                        📢 Announcements
                    </a>

                    <a href="/admin/analytics">
                        📈 Analytics
                    </a>

                    <a href="/admin/settings">
                        ⚙️ Settings
                    </a>

                    <a href="/admin/logout">
                        🚪 Logout
                    </a>

                </div>

            </div>
            """

        else:

            navbar = """
            <div class="navbar">

                <div class="logo">
                    🛡️ School<span>Safe</span>
                </div>

                <div class="nav-links">

                    <a href="/student">
                        🎓 Student Portal
                    </a>

                    <a href="/">
                        🏠 Home
                    </a>

                </div>

            </div>
            """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>{safe(title)} | SchoolSafe</title>

        {CSS}

    </head>

    <body>

        {navbar}

        <div class="container">

            {content}

        </div>

        <div class="footer">

            <b>SchoolSafe</b> — School Safety Reporting System

            <br>

            Keeping our school safer, one report at a time.

        </div>

    </body>

    </html>
    """


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    content = """

    <div class="hero">

        <div style="font-size:55px;">
            🛡️
        </div>

        <h1>
            Welcome to SchoolSafe
        </h1>

        <p>
            A simple and secure way to report
            school safety and facility problems.
        </p>

        <h3 style="color:white;">
            Are you a Student or an Admin?
        </h3>

    </div>


    <div class="card-grid">

        <a href="/student">

            <div class="card role-card">

                <div class="icon">
                    🎓
                </div>

                <h2>
                    Student
                </h2>

                <p>
                    Report school issues and track
                    the status of your submitted reports.
                </p>

                <span class="btn btn-primary">
                    Continue as Student
                </span>

            </div>

        </a>


        <a href="/admin/login">

            <div class="card role-card">

                <div class="icon">
                    👨‍💼
                </div>

                <h2>
                    Admin
                </h2>

                <p>
                    Manage reports, update their status,
                    add remarks, and post announcements.
                </p>

                <span class="btn btn-primary">
                    Continue as Admin
                </span>

            </div>

        </a>

    </div>


    <div class="card" style="margin-top:25px;">

        <h2>
            🛡️ How SchoolSafe Works
        </h2>

        <div class="card-grid">

            <div>
                <h3>1️⃣ Report</h3>
                <p>
                    Students submit information about
                    a school safety or facility problem.
                </p>
            </div>

            <div>
                <h3>2️⃣ Review</h3>
                <p>
                    Administrators review the report
                    and determine the appropriate action.
                </p>
            </div>

            <div>
                <h3>3️⃣ Resolve</h3>
                <p>
                    The report status is updated until
                    the issue has been resolved.
                </p>
            </div>

        </div>

    </div>

    """

    return page(
        "Home",
        content,
        nav=False
    )


# ============================================================
# STUDENT PORTAL
# ============================================================

@app.route("/student")
def student():

    conn = get_db()

    announcements = conn.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    announcement_html = ""

    if announcements:

        for a in announcements:

            announcement_html += f"""

            <div class="tip">

                <b>
                    📢 {safe(a["title"])}
                </b>

                <br>

                {safe(a["message"])}

                <br>

                <small>
                    {safe(a["date_posted"])}
                </small>

            </div>

            """

    else:

        announcement_html = """

        <div class="tip">

            <b>
                📢 No announcements yet.
            </b>

            <br>

            Check back later for school safety announcements.

        </div>

        """

    content = f"""

    <div class="hero">

        <div style="font-size:50px;">
            🎓
        </div>

        <h1>
            Student Portal
        </h1>

        <p>
            Report a problem or check the status
            of your report.
        </p>

        <a
            class="btn btn-light"
            href="/student/report"
        >
            📝 Report an Issue
        </a>

        <a
            class="btn btn-light"
            href="/student/track"
        >
            🔎 Track Report
        </a>

        <a
            class="btn btn-light"
            href="/student/my-reports"
        >
            📋 My Reports
        </a>

    </div>


    <div class="card-grid">

        <div class="card">

            <div class="icon">
                📝
            </div>

            <h2>
                Report an Issue
            </h2>

            <p>
                Report broken equipment, damaged facilities,
                electrical problems, or other school safety concerns.
            </p>

        </div>


        <div class="card">

            <div class="icon">
                🔎
            </div>

            <h2>
                Track Report
            </h2>

            <p>
                Enter your Report ID to see your report status,
                remarks, and timeline.
            </p>

        </div>


        <div class="card">

            <div class="icon">
                📋
            </div>

            <h2>
                My Reports
            </h2>

            <p>
                View reports using the name you entered
                when submitting your reports.
            </p>

        </div>

    </div>


    <div class="card" style="margin-top:25px;">

        <h2>
            📢 School Announcements
        </h2>

        {announcement_html}

    </div>


    <div class="card" style="margin-top:25px;">

        <h2>
            💡 Safety Tips
        </h2>

        <div class="tip">

            <b>
                ⚡ Electrical Safety
            </b>

            <br>

            Do not touch exposed wires or damaged
            electrical equipment. Report them immediately.

        </div>


        <div class="tip">

            <b>
                🚪 Damaged Facilities
            </b>

            <br>

            Avoid using broken doors, windows,
            chairs, or tables until they are repaired.

        </div>


        <div class="tip">

            <b>
                🧹 Slippery Floors
            </b>

            <br>

            Report wet or slippery areas
            to help prevent accidents.

        </div>


        <div class="tip">

            <b>
                🚨 Emergency Problems
            </b>

            <br>

            For serious and immediate danger,
            inform a teacher or school personnel immediately.

        </div>

    </div>

    """

    return page(
        "Student Portal",
        content
    )


# ============================================================
# REPORT ISSUE
# ============================================================

@app.route("/student/report", methods=["GET", "POST"])
def report_issue():

    if request.method == "POST":

        reporter = request.form.get(
            "reporter",
            ""
        ).strip()

        issue_type = request.form.get(
            "issue_type",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        urgency = request.form.get(
            "urgency",
            ""
        ).strip()

        if not reporter or not issue_type or not location or not description or not urgency:

            content = """

            <div class="alert alert-danger">

                Please complete all required fields.

            </div>

            <a
                class="btn btn-secondary"
                href="/student/report"
            >
                ← Back
            </a>

            """

            return page(
                "Error",
                content
            )

        report_id = generate_report_id()

        now = datetime.datetime.now()

        date_reported = now.strftime(
            "%Y-%m-%d"
        )

        time_reported = now.strftime(
            "%I:%M %p"
        )

        photo_name = ""

        # ----------------------------------------------------
        # PHOTO UPLOAD
        # ----------------------------------------------------

        file = request.files.get("photo")

        if file and file.filename:

            if allowed_file(file.filename):

                original_name = secure_filename(
                    file.filename
                )

                extension = original_name.rsplit(
                    ".",
                    1
                )[1].lower()

                photo_name = (
                    report_id
                    + "_"
                    + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    + "."
                    + extension
                )

                file.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        photo_name
                    )
                )

        conn = get_db()

        conn.execute("""
            INSERT INTO reports
            (
                report_id,
                reporter,
                issue_type,
                location,
                description,
                urgency,
                status,
                remarks,
                date_reported,
                time_reported,
                photo,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id,
            reporter,
            issue_type,
            location,
            description,
            urgency,
            "Submitted",
            "",
            date_reported,
            time_reported,
            photo_name,
            f"{date_reported} {time_reported}"
        ))

        conn.commit()
        conn.close()

        add_history(
            report_id,
            "Submitted",
            "Report submitted by student."
        )

        return redirect(
            url_for(
                "report_success",
                report_id=report_id
            )
        )

    content = """

    <div class="form-card">

        <h1>
            📝 Report an Issue
        </h1>

        <p>
            Please provide accurate information about
            the school safety or facility problem.
        </p>


        <div class="alert alert-info">

            🔒 Your information will be used only
            for handling the reported school issue.

        </div>


        <form
            method="POST"
            enctype="multipart/form-data"
            onsubmit="return confirm('Are you sure you want to submit this report?');"
        >


            <div class="form-group">

                <label>
                    Your Name *
                </label>

                <input
                    type="text"
                    name="reporter"
                    placeholder="Enter your name"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    Issue Type *
                </label>

                <select
                    name="issue_type"
                    required
                >

                    <option value="">
                        -- Select Issue --
                    </option>

                    <option>
                        Broken Chair
                    </option>

                    <option>
                        Broken Table
                    </option>

                    <option>
                        Broken Electric Fan
                    </option>

                    <option>
                        Broken Light
                    </option>

                    <option>
                        Damaged Door
                    </option>

                    <option>
                        Broken Window
                    </option>

                    <option>
                        Electrical Problem
                    </option>

                    <option>
                        Comfort Room Problem
                    </option>

                    <option>
                        Roof Damage
                    </option>

                    <option>
                        Slippery Floor
                    </option>

                    <option>
                        Garbage / Cleanliness Problem
                    </option>

                    <option>
                        Other
                    </option>

                </select>

            </div>


            <div class="form-group">

                <label>
                    Location *
                </label>

                <input
                    type="text"
                    name="location"
                    placeholder="Example: Room 204"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    Urgency *
                </label>

                <select
                    name="urgency"
                    required
                >

                    <option value="">
                        -- Select Urgency --
                    </option>

                    <option>
                        Low
                    </option>

                    <option>
                        Medium
                    </option>

                    <option>
                        High
                    </option>

                    <option>
                        Emergency
                    </option>

                </select>

            </div>


            <div class="form-group">

                <label>
                    Description *
                </label>

                <textarea
                    name="description"
                    placeholder="Describe the problem in detail..."
                    required
                ></textarea>

                <small>
                    Please describe what happened,
                    where it happened, and any important details.
                </small>

            </div>


            <div class="form-group">

                <label>
                    📸 Photo Evidence (Optional)
                </label>

                <input
                    type="file"
                    name="photo"
                    accept=".jpg,.jpeg,.png,.gif,.webp"
                >

                <small>
                    Maximum file size: 5 MB.
                </small>

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                🚀 Submit Report
            </button>


            <a
                class="btn btn-secondary"
                href="/student"
            >
                Cancel
            </a>

        </form>

    </div>

    """

    return page(
        "Report an Issue",
        content
    )


# ============================================================
# REPORT SUCCESS
# ============================================================

@app.route("/student/report-success/<report_id>")
def report_success(report_id):

    conn = get_db()

    report = conn.execute("""
        SELECT *
        FROM reports
        WHERE report_id = ?
    """, (report_id,)).fetchone()

    conn.close()

    if not report:

        return page(
            "Error",
            """
            <div class="alert alert-danger">
                Report not found.
            </div>
            """
        )

    content = f"""

    <div class="form-card">

        <div style="text-align:center;font-size:60px;">
            ✅
        </div>

        <h1 style="text-align:center;">
            Report Submitted Successfully!
        </h1>

        <p style="text-align:center;">
            Please save your Report ID.
            You can use it to track your report.
        </p>


        <div class="report-id">
            {safe(report["report_id"])}
        </div>


        <div class="alert alert-success">

            <b>
                Your report has been saved successfully.
            </b>

            <br>

            Status:
            <b>
                Submitted
            </b>

        </div>


        <div style="text-align:center;">

            <a
                class="btn btn-primary"
                href="/student/track?report_id={safe(report_id)}"
            >
                🔎 Track This Report
            </a>

            <a
                class="btn btn-secondary"
                href="/student"
            >
                🏠 Student Portal
            </a>

        </div>

    </div>

    """

    return page(
        "Report Submitted",
        content
    )


# ============================================================
# TRACK REPORT
# ============================================================

@app.route("/student/track", methods=["GET", "POST"])
def track_report():

    report = None
    history = []
    error = ""

    report_id = request.args.get(
        "report_id",
        ""
    ).strip()

    if request.method == "POST":

        report_id = request.form.get(
            "report_id",
            ""
        ).strip()

    if report_id:

        conn = get_db()

        report = conn.execute("""
            SELECT *
            FROM reports
            WHERE report_id = ?
        """, (report_id,)).fetchone()

        if report:

            history = conn.execute("""
                SELECT *
                FROM report_history
                WHERE report_id = ?
                ORDER BY id ASC
            """, (report_id,)).fetchall()

        conn.close()

        if not report:

            error = "No report found with that Report ID."

    result_html = ""

    if error:

        result_html = f"""

        <div class="alert alert-danger">
            ❌ {safe(error)}
        </div>

        """

    if report:

        current_status = safe(
            report["status"]
        )

        progress = 25

        if report["status"] == "Under Review":
            progress = 50

        elif report["status"] == "In Progress":
            progress = 75

        elif report["status"] == "Resolved":
            progress = 100

        timeline_html = ""

        for item in history:

            timeline_html += f"""

            <div class="timeline-item">

                <b>
                    {safe(item["status"])}
                </b>

                <br>

                <small>
                    {safe(item["date_updated"])}
                    —
                    {safe(item["time_updated"])}
                </small>

                <p>
                    {safe(item["remarks"])}
                </p>

            </div>

            """

        result_html = f"""

        <div class="card" style="margin-top:25px;">

            <h2>
                📋 Report Information
            </h2>


            <div class="big-status">

                <div>
                    Current Status
                </div>

                <br>

                <span class="badge {status_class(report["status"])}">
                    {current_status}
                </span>


                <div class="progress-bar">

                    <div
                        class="progress-fill"
                        style="width:{progress}%"
                    ></div>

                </div>

            </div>


            <div class="detail-grid">

                <div class="detail-item">

                    <div class="detail-label">
                        Report ID
                    </div>

                    <div class="detail-value">
                        {safe(report["report_id"])}
                    </div>

                </div>


                <div class="detail-item">

                    <div class="detail-label">
                        Issue Type
                    </div>

                    <div class="detail-value">
                        {safe(report["issue_type"])}
                    </div>

                </div>


                <div class="detail-item">

                    <div class="detail-label">
                        Location
                    </div>

                    <div class="detail-value">
                        {safe(report["location"])}
                    </div>

                </div>


                <div class="detail-item">

                    <div class="detail-label">
                        Urgency
                    </div>

                    <div class="detail-value">

                        <span class="badge {urgency_class(report["urgency"])}">
                            {safe(report["urgency"])}
                        </span>

                    </div>

                </div>


                <div class="detail-item">

                    <div class="detail-label">
                        Date Reported
                    </div>

                    <div class="detail-value">
                        {safe(report["date_reported"])}
                    </div>

                </div>


                <div class="detail-item">

                    <div class="detail-label">
                        Time Reported
                    </div>

                    <div class="detail-value">
                        {safe(report["time_reported"])}
                    </div>

                </div>

            </div>


            <h3>
                📝 Description
            </h3>

            <div class="description-box">
                {safe(report["description"])}
            </div>


            <h3>
                💬 Admin Remarks
            </h3>

            <div class="description-box">

                {safe(report["remarks"]) if report["remarks"] else "No remarks yet."}

            </div>


            <h3>
                🕒 Report Timeline
            </h3>

            <div class="timeline">

                {timeline_html if timeline_html else "<p>No timeline available.</p>"}

            </div>

        </div>

        """

    content = f"""

    <div class="form-card">

        <h1>
            🔎 Track Your Report
        </h1>

        <p>
            Enter your Report ID to see the current
            status and history of your report.
        </p>


        <form method="POST">

            <div class="form-group">

                <label>
                    Report ID
                </label>

                <input
                    type="text"
                    name="report_id"
                    value="{safe(report_id)}"
                    placeholder="Example: SS-A7K29P"
                    required
                >

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                🔎 Track Report
            </button>


            <a
                class="btn btn-secondary"
                href="/student"
            >
                Back
            </a>

        </form>

    </div>


    {result_html}

    """

    return page(
        "Track Report",
        content
    )


# ============================================================
# MY REPORTS
# ============================================================

@app.route("/student/my-reports", methods=["GET", "POST"])
def my_reports():

    reports = []
    name = ""

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

    else:

        name = request.args.get(
            "name",
            ""
        ).strip()

    if name:

        conn = get_db()

        reports = conn.execute("""
            SELECT *
            FROM reports
            WHERE LOWER(reporter) = LOWER(?)
            ORDER BY id DESC
        """, (name,)).fetchall()

        conn.close()

    rows = ""

    for r in reports:

        emergency_class = ""

        if r["urgency"] == "Emergency":
            emergency_class = "emergency-row"

        rows += f"""

        <tr class="{emergency_class}">

            <td>
                <b>{safe(r["report_id"])}</b>
            </td>

            <td>
                {safe(r["issue_type"])}
            </td>

            <td>
                {safe(r["location"])}
            </td>

            <td>

                <span class="badge {urgency_class(r["urgency"])}">
                    {safe(r["urgency"])}
                </span>

            </td>

            <td>

                <span class="badge {status_class(r["status"])}">
                    {safe(r["status"])}
                </span>

            </td>

            <td>
                {safe(r["date_reported"])}
            </td>

            <td>

                <a
                    class="btn btn-primary"
                    href="/student/track?report_id={safe(r["report_id"])}"
                >
                    View
                </a>

            </td>

        </tr>

        """

    if not rows and name:

        rows = """

        <tr>

            <td colspan="7" class="empty">

                No reports found for that name.

            </td>

        </tr>

        """

    content = f"""

    <div class="form-card">

        <h1>
            📋 My Reports
        </h1>

        <p>
            Enter the same name you used when
            submitting your report.
        </p>


        <form method="POST">

            <div class="form-group">

                <label>
                    Your Name
                </label>

                <input
                    type="text"
                    name="name"
                    value="{safe(name)}"
                    placeholder="Enter your name"
                    required
                >

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                🔎 Find My Reports
            </button>

        </form>

    </div>


    {"<div class='table-container' style='margin-top:25px;'><table><tr><th>Report ID</th><th>Issue</th><th>Location</th><th>Urgency</th><th>Status</th><th>Date</th><th>Action</th></tr>" + rows + "</table></div>" if name else ""}

    """

    return page(
        "My Reports",
        content
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if admin_required():

        return redirect(
            url_for("admin_dashboard")
        )

    error = ""

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        saved_username, saved_password = get_admin_credentials()

        if (
            username == saved_username
            and password == saved_password
        ):

            session.clear()

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        error = "Invalid username or password."

    content = f"""

    <div class="form-card" style="max-width:500px;">

        <div style="text-align:center;font-size:55px;">
            🔐
        </div>

        <h1 style="text-align:center;">
            Admin Login
        </h1>

        <p style="text-align:center;">
            Authorized administrators only.
        </p>


        {"<div class='alert alert-danger'>❌ " + safe(error) + "</div>" if error else ""}


        <form method="POST">

            <div class="form-group">

                <label>
                    Username
                </label>

                <input
                    type="text"
                    name="username"
                    placeholder="Admin username"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    Password
                </label>

                <input
                    type="password"
                    name="password"
                    placeholder="Admin password"
                    required
                >

            </div>


            <button
                class="btn btn-primary"
                type="submit"
                style="width:100%;"
            >
                🔐 Login
            </button>

        </form>


        <div style="text-align:center;margin-top:20px;">

            <a
                href="/"
                class="btn btn-secondary"
            >
                ← Back to Home
            </a>

        </div>

    </div>

    """

    return page(
        "Admin Login",
        content,
        nav=False
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) AS count FROM reports"
    ).fetchone()["count"]

    submitted = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE status = 'Submitted'
    """).fetchone()["count"]

    review = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE status = 'Under Review'
    """).fetchone()["count"]

    progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE status = 'In Progress'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE status = 'Resolved'
    """).fetchone()["count"]

    emergency = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE urgency = 'Emergency'
        AND status != 'Resolved'
    """).fetchone()["count"]

    recent_reports = conn.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
        LIMIT 8
    """).fetchall()

    conn.close()

    recent_html = ""

    for r in recent_reports:

        row_class = ""

        if r["urgency"] == "Emergency":
            row_class = "emergency-row"

        recent_html += f"""

        <tr class="{row_class}">

            <td>
                <b>{safe(r["report_id"])}</b>
            </td>

            <td>
                {safe(r["reporter"])}
            </td>

            <td>
                {safe(r["issue_type"])}
            </td>

            <td>

                <span class="badge {urgency_class(r["urgency"])}">
                    {safe(r["urgency"])}
                </span>

            </td>

            <td>

                <span class="badge {status_class(r["status"])}">
                    {safe(r["status"])}
                </span>

            </td>

            <td>

                <a
                    class="btn btn-primary"
                    href="/admin/report/{safe(r["report_id"])}"
                >
                    View Details
                </a>

            </td>

        </tr>

        """

    content = f"""

    <div class="hero">

        <div style="font-size:45px;">
            📊
        </div>

        <h1>
            Admin Dashboard
        </h1>

        <p>
            Monitor and manage school safety reports.
        </p>

    </div>


    <div class="stats" style="margin-top:25px;">

        <div class="stat">

            <div class="stat-number">
                {total}
            </div>

            <div class="stat-title">
                Total Reports
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {submitted}
            </div>

            <div class="stat-title">
                Submitted
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {review}
            </div>

            <div class="stat-title">
                Under Review
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {progress}
            </div>

            <div class="stat-title">
                In Progress
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {resolved}
            </div>

            <div class="stat-title">
                Resolved
            </div>

        </div>


        <div class="stat">

            <div
                class="stat-number"
                style="color:#b02a37;"
            >
                {emergency}
            </div>

            <div class="stat-title">
                🚨 Active Emergency
            </div>

        </div>

    </div>


    <div class="card">

        <h2>
            🚨 Emergency Reports
        </h2>

        <p>
            There are currently
            <b>{emergency}</b>
            unresolved emergency report(s).
        </p>

        <a
            href="/admin/reports?urgency=Emergency"
            class="btn btn-danger"
        >
            View Emergency Reports
        </a>

    </div>


    <div class="table-container" style="margin-top:25px;">

        <h2>
            🕒 Recent Reports
        </h2>

        <table>

            <tr>

                <th>
                    Report ID
                </th>

                <th>
                    Student
                </th>

                <th>
                    Issue
                </th>

                <th>
                    Urgency
                </th>

                <th>
                    Status
                </th>

                <th>
                    Action
                </th>

            </tr>

            {recent_html if recent_html else """

            <tr>
                <td colspan="6" class="empty">
                    No reports yet.
                </td>
            </tr>

            """}

        </table>

    </div>

    """

    return page(
        "Admin Dashboard",
        content
    )


# ============================================================
# ADMIN REPORTS
# ============================================================

@app.route("/admin/reports")
def admin_reports():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    search = request.args.get(
        "search",
        ""
    ).strip()

    urgency_filter = request.args.get(
        "urgency",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    query = """
        SELECT *
        FROM reports
        WHERE 1=1
    """

    params = []

    if search:

        query += """
            AND (
                report_id LIKE ?
                OR reporter LIKE ?
                OR issue_type LIKE ?
                OR location LIKE ?
                OR description LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if urgency_filter:

        query += """
            AND urgency = ?
        """

        params.append(
            urgency_filter
        )

    if status_filter:

        query += """
            AND status = ?
        """

        params.append(
            status_filter
        )

    query += """
        ORDER BY
        CASE
            WHEN urgency = 'Emergency'
            AND status != 'Resolved'
            THEN 0
            ELSE 1
        END,
        id DESC
    """

    conn = get_db()

    reports = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    rows = ""

    for r in reports:

        row_class = ""

        if (
            r["urgency"] == "Emergency"
            and r["status"] != "Resolved"
        ):
            row_class = "emergency-row"

        rows += f"""

        <tr class="{row_class}">

            <td>
                <b>{safe(r["report_id"])}</b>
            </td>

            <td>
                {safe(r["reporter"])}
            </td>

            <td>
                {safe(r["issue_type"])}
            </td>

            <td>
                {safe(r["location"])}
            </td>

            <td>

                <span class="badge {urgency_class(r["urgency"])}">
                    {safe(r["urgency"])}
                </span>

            </td>

            <td>

                <span class="badge {status_class(r["status"])}">
                    {safe(r["status"])}
                </span>

            </td>

            <td>
                {safe(r["date_reported"])}
            </td>

            <td>

                <a
                    class="btn btn-primary"
                    href="/admin/report/{safe(r["report_id"])}"
                >
                    👁️ View Details
                </a>

            </td>

        </tr>

        """

    if not rows:

        rows = """

        <tr>

            <td colspan="8" class="empty">

                No reports found.

            </td>

        </tr>

        """

    content = f"""

    <h1>
        📋 Student Reports
    </h1>

    <p>
        View and manage all submitted school safety reports.
    </p>


    <div class="search-box">

        <form method="GET">

            <div class="card-grid">

                <div>

                    <label>
                        Search
                    </label>

                    <input
                        type="text"
                        name="search"
                        value="{safe(search)}"
                        placeholder="ID, student, issue, location..."
                    >

                </div>


                <div>

                    <label>
                        Urgency
                    </label>

                    <select name="urgency">

                        <option value="">
                            All
                        </option>

                        <option
                            {"selected" if urgency_filter == "Low" else ""}
                        >
                            Low
                        </option>

                        <option
                            {"selected" if urgency_filter == "Medium" else ""}
                        >
                            Medium
                        </option>

                        <option
                            {"selected" if urgency_filter == "High" else ""}
                        >
                            High
                        </option>

                        <option
                            {"selected" if urgency_filter == "Emergency" else ""}
                        >
                            Emergency
                        </option>

                    </select>

                </div>


                <div>

                    <label>
                        Status
                    </label>

                    <select name="status">

                        <option value="">
                            All
                        </option>

                        <option
                            {"selected" if status_filter == "Submitted" else ""}
                        >
                            Submitted
                        </option>

                        <option
                            {"selected" if status_filter == "Under Review" else ""}
                        >
                            Under Review
                        </option>

                        <option
                            {"selected" if status_filter == "In Progress" else ""}
                        >
                            In Progress
                        </option>

                        <option
                            {"selected" if status_filter == "Resolved" else ""}
                        >
                            Resolved
                        </option>

                    </select>

                </div>

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                🔎 Search
            </button>


            <a
                href="/admin/reports"
                class="btn btn-secondary"
            >
                Reset
            </a>

        </form>

    </div>


    <div class="table-container">

        <table>

            <tr>

                <th>
                    Report ID
                </th>

                <th>
                    Student
                </th>

                <th>
                    Issue
                </th>

                <th>
                    Location
                </th>

                <th>
                    Urgency
                </th>

                <th>
                    Status
                </th>

                <th>
                    Date
                </th>

                <th>
                    Action
                </th>

            </tr>

            {rows}

        </table>

    </div>

    """

    return page(
        "Student Reports",
        content
    )


# ============================================================
# ADMIN REPORT DETAILS
# ============================================================

@app.route("/admin/report/<report_id>", methods=["GET", "POST"])
def admin_report_details(report_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    report = conn.execute("""
        SELECT *
        FROM reports
        WHERE report_id = ?
    """, (report_id,)).fetchone()

    conn.close()

    if not report:

        return page(
            "Report Not Found",
            """
            <div class="alert alert-danger">
                Report not found.
            </div>

            <a
                class="btn btn-secondary"
                href="/admin/reports"
            >
                ← Back to Reports
            </a>
            """
        )

    message = ""

    if request.method == "POST":

        new_status = request.form.get(
            "status",
            ""
        ).strip()

        remarks = request.form.get(
            "remarks",
            ""
        ).strip()

        allowed_statuses = [
            "Submitted",
            "Under Review",
            "In Progress",
            "Resolved"
        ]

        if new_status not in allowed_statuses:

            message = """
            <div class="alert alert-danger">
                Invalid status selected.
            </div>
            """

        else:

            old_status = report["status"]

            now = datetime.datetime.now()

            updated_at = now.strftime(
                "%Y-%m-%d %I:%M %p"
            )

            conn = get_db()

            conn.execute("""
                UPDATE reports
                SET
                    status = ?,
                    remarks = ?,
                    updated_at = ?
                WHERE report_id = ?
            """, (
                new_status,
                remarks,
                updated_at,
                report_id
            ))

            conn.commit()
            conn.close()

            if (
                old_status != new_status
                or remarks
            ):

                add_history(
                    report_id,
                    new_status,
                    remarks
                )

            message = """

            <div class="alert alert-success">

                ✅ Report updated successfully.

            </div>

            """

            conn = get_db()

            report = conn.execute("""
                SELECT *
                FROM reports
                WHERE report_id = ?
            """, (report_id,)).fetchone()

            conn.close()

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    conn = get_db()

    history = conn.execute("""
        SELECT *
        FROM report_history
        WHERE report_id = ?
        ORDER BY id DESC
    """, (report_id,)).fetchall()

    conn.close()

    timeline_html = ""

    for item in history:

        timeline_html += f"""

        <div class="timeline-item">

            <b>
                {safe(item["status"])}
            </b>

            <br>

            <small>
                {safe(item["date_updated"])}
                —
                {safe(item["time_updated"])}
            </small>

            <p>
                {safe(item["remarks"])}
            </p>

        </div>

        """

    photo_html = ""

    if report["photo"]:

        photo_html = f"""

        <h3>
            📸 Photo Evidence
        </h3>

        <img
            class="photo-preview"
            src="/uploads/{safe(report["photo"])}"
            alt="Report evidence"
        >

        """

    content = f"""

    <h1>
        📋 Report Details
    </h1>

    {message}


    <div class="card">

        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">

            <h2>
                Report {safe(report["report_id"])}
            </h2>

            <span class="badge {urgency_class(report["urgency"])}">
                {safe(report["urgency"])}
            </span>

        </div>


        <div class="detail-grid">

            <div class="detail-item">

                <div class="detail-label">
                    Student Name
                </div>

                <div class="detail-value">
                    {safe(report["reporter"])}
                </div>

            </div>


            <div class="detail-item">

                <div class="detail-label">
                    Issue Type
                </div>

                <div class="detail-value">
                    {safe(report["issue_type"])}
                </div>

            </div>


            <div class="detail-item">

                <div class="detail-label">
                    Location
                </div>

                <div class="detail-value">
                    {safe(report["location"])}
                </div>

            </div>


            <div class="detail-item">

                <div class="detail-label">
                    Date Reported
                </div>

                <div class="detail-value">
                    {safe(report["date_reported"])}
                </div>

            </div>


            <div class="detail-item">

                <div class="detail-label">
                    Time Reported
                </div>

                <div class="detail-value">
                    {safe(report["time_reported"])}
                </div>

            </div>


            <div class="detail-item">

                <div class="detail-label">
                    Last Updated
                </div>

                <div class="detail-value">
                    {safe(report["updated_at"]) if report["updated_at"] else "Not updated yet"}
                </div>

            </div>

        </div>


        <h2 style="margin-top:30px;">
            📝 Student's Full Description
        </h2>


        <div class="description-box">

            {safe(report["description"])}

        </div>


        {photo_html}


        <h2 style="margin-top:30px;">
            📌 Current Status
        </h2>


        <div class="big-status">

            <span class="badge {status_class(report["status"])}">
                {safe(report["status"])}
            </span>

        </div>


        <h2>
            🛠️ Update Report
        </h2>


        <form method="POST">

            <div class="form-group">

                <label>
                    Report Status
                </label>

                <select name="status" required>

                    <option
                        {"selected" if report["status"] == "Submitted" else ""}
                    >
                        Submitted
                    </option>

                    <option
                        {"selected" if report["status"] == "Under Review" else ""}
                    >
                        Under Review
                    </option>

                    <option
                        {"selected" if report["status"] == "In Progress" else ""}
                    >
                        In Progress
                    </option>

                    <option
                        {"selected" if report["status"] == "Resolved" else ""}
                    >
                        Resolved
                    </option>

                </select>

            </div>


            <div class="form-group">

                <label>
                    Admin Remarks
                </label>

                <textarea
                    name="remarks"
                    placeholder="Enter an update or remark for the student..."
                >{safe(report["remarks"])}</textarea>

            </div>


            <button
                class="btn btn-success"
                type="submit"
            >
                💾 Save Update
            </button>

        </form>

    </div>


    <div class="card" style="margin-top:25px;">

        <h2>
            🕒 Report Timeline
        </h2>

        <div class="timeline">

            {timeline_html if timeline_html else "No history available."}

        </div>

    </div>


    <div style="margin-top:20px;">

        <a
            class="btn btn-secondary"
            href="/admin/reports"
        >
            ← Back to Reports
        </a>

    </div>

    """

    return page(
        "Report Details",
        content
    )


# ============================================================
# UPLOADED FILES
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    from flask import send_from_directory

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# ADMIN ANNOUNCEMENTS
# ============================================================

@app.route("/admin/announcements", methods=["GET", "POST"])
def admin_announcements():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    message = ""

    if request.method == "POST":

        action = request.form.get(
            "action",
            ""
        )

        if action == "add":

            title = request.form.get(
                "title",
                ""
            ).strip()

            announcement_message = request.form.get(
                "message",
                ""
            ).strip()

            if title and announcement_message:

                now = datetime.datetime.now()

                date_posted = now.strftime(
                    "%Y-%m-%d %I:%M %p"
                )

                conn = get_db()

                conn.execute("""
                    INSERT INTO announcements
                    (
                        title,
                        message,
                        date_posted
                    )
                    VALUES (?, ?, ?)
                """, (
                    title,
                    announcement_message,
                    date_posted
                ))

                conn.commit()
                conn.close()

                message = """

                <div class="alert alert-success">
                    📢 Announcement posted successfully.
                </div>

                """

        elif action == "delete":

            announcement_id = request.form.get(
                "announcement_id"
            )

            conn = get_db()

            conn.execute("""
                DELETE FROM announcements
                WHERE id = ?
            """, (announcement_id,))

            conn.commit()
            conn.close()

            message = """

            <div class="alert alert-success">
                Announcement deleted.
            </div>

            """

    conn = get_db()

    announcements = conn.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for a in announcements:

        rows += f"""

        <tr>

            <td>
                <b>{safe(a["title"])}</b>
            </td>

            <td>
                {safe(a["message"])}
            </td>

            <td>
                {safe(a["date_posted"])}
            </td>

            <td>

                <form
                    method="POST"
                    onsubmit="return confirm('Delete this announcement?');"
                >

                    <input
                        type="hidden"
                        name="action"
                        value="delete"
                    >

                    <input
                        type="hidden"
                        name="announcement_id"
                        value="{a["id"]}"
                    >

                    <button
                        class="btn btn-danger"
                        type="submit"
                    >
                        Delete
                    </button>

                </form>

            </td>

        </tr>

        """

    content = f"""

    <h1>
        📢 Announcements
    </h1>

    {message}


    <div class="form-card" style="max-width:800px;">

        <h2>
            ➕ Create Announcement
        </h2>

        <form method="POST">

            <input
                type="hidden"
                name="action"
                value="add"
            >


            <div class="form-group">

                <label>
                    Title
                </label>

                <input
                    type="text"
                    name="title"
                    placeholder="Announcement title"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    Message
                </label>

                <textarea
                    name="message"
                    placeholder="Write announcement..."
                    required
                ></textarea>

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                📢 Post Announcement
            </button>

        </form>

    </div>


    <div class="table-container" style="margin-top:25px;">

        <h2>
            📋 Posted Announcements
        </h2>

        <table>

            <tr>

                <th>
                    Title
                </th>

                <th>
                    Message
                </th>

                <th>
                    Date
                </th>

                <th>
                    Action
                </th>

            </tr>

            {rows if rows else """

            <tr>

                <td
                    colspan="4"
                    class="empty"
                >
                    No announcements yet.
                </td>

            </tr>

            """}

        </table>

    </div>

    """

    return page(
        "Announcements",
        content
    )


# ============================================================
# ADMIN ANALYTICS
# ============================================================

@app.route("/admin/analytics")
def admin_analytics():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) AS count FROM reports"
    ).fetchone()["count"]

    low = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE urgency = 'Low'
    """).fetchone()["count"]

    medium = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE urgency = 'Medium'
    """).fetchone()["count"]

    high = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE urgency = 'High'
    """).fetchone()["count"]

    emergency = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE urgency = 'Emergency'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM reports
        WHERE status = 'Resolved'
    """).fetchone()["count"]

    common_issue = conn.execute("""
        SELECT issue_type, COUNT(*) AS count
        FROM reports
        GROUP BY issue_type
        ORDER BY count DESC
        LIMIT 1
    """).fetchone()

    common_location = conn.execute("""
        SELECT location, COUNT(*) AS count
        FROM reports
        GROUP BY location
        ORDER BY count DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if total > 0:

        resolved_percentage = round(
            (resolved / total) * 100
        )

    else:

        resolved_percentage = 0

    issue_text = (
        f"{common_issue['issue_type']} "
        f"({common_issue['count']} reports)"
        if common_issue
        else "No data yet"
    )

    location_text = (
        f"{common_location['location']} "
        f"({common_location['count']} reports)"
        if common_location
        else "No data yet"
    )

    content = f"""

    <h1>
        📈 SchoolSafe Analytics
    </h1>

    <p>
        Overview of submitted school safety reports.
    </p>


    <div class="stats">

        <div class="stat">

            <div class="stat-number">
                {total}
            </div>

            <div class="stat-title">
                Total Reports
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {resolved}
            </div>

            <div class="stat-title">
                Resolved
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {emergency}
            </div>

            <div class="stat-title">
                Emergency
            </div>

        </div>

    </div>


    <div class="card-grid">

        <div class="card">

            <h2>
                ⚠️ Reports by Urgency
            </h2>

            <p>
                🟢 Low:
                <b>{low}</b>
            </p>

            <p>
                🟡 Medium:
                <b>{medium}</b>
            </p>

            <p>
                🔴 High:
                <b>{high}</b>
            </p>

            <p>
                🚨 Emergency:
                <b>{emergency}</b>
            </p>

        </div>


        <div class="card">

            <h2>
                🏆 Most Reported Issue
            </h2>

            <p>
                {safe(issue_text)}
            </p>

        </div>


        <div class="card">

            <h2>
                📍 Most Reported Location
            </h2>

            <p>
                {safe(location_text)}
            </p>

        </div>


        <div class="card">

            <h2>
                ✅ Resolution Progress
            </h2>

            <p>
                {resolved_percentage}% of all reports
                are currently resolved.
            </p>

            <div class="progress-bar">

                <div
                    class="progress-fill"
                    style="width:{resolved_percentage}%"
                ></div>

            </div>

        </div>

    </div>


    <div class="card" style="margin-top:25px;">

        <h2>
            📊 Report Management
        </h2>

        <a
            href="/admin/reports"
            class="btn btn-primary"
        >
            📋 View All Reports
        </a>

        <a
            href="/admin/reports?urgency=Emergency"
            class="btn btn-danger"
        >
            🚨 View Emergency Reports
        </a>

    </div>

    """

    return page(
        "Analytics",
        content
    )


# ============================================================
# ADMIN SETTINGS
# ============================================================

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    message = ""

    current_username, _ = get_admin_credentials()

    if request.method == "POST":

        new_username = request.form.get(
            "username",
            ""
        ).strip()

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        _, saved_password = get_admin_credentials()

        if current_password != saved_password:

            message = """

            <div class="alert alert-danger">
                ❌ Current password is incorrect.
            </div>

            """

        elif not new_username:

            message = """

            <div class="alert alert-danger">
                Username cannot be empty.
            </div>

            """

        elif new_password != confirm_password:

            message = """

            <div class="alert alert-danger">
                ❌ New passwords do not match.
            </div>

            """

        elif new_password and len(new_password) < 6:

            message = """

            <div class="alert alert-danger">
                ❌ New password must be at least 6 characters.
            </div>

            """

        else:

            password_to_save = (
                new_password
                if new_password
                else saved_password
            )

            conn = get_db()

            conn.execute("""
                UPDATE settings
                SET
                    admin_username = ?,
                    admin_password = ?
                WHERE id = 1
            """, (
                new_username,
                password_to_save
            ))

            conn.commit()
            conn.close()

            message = """

            <div class="alert alert-success">
                ✅ Admin settings updated successfully.
            </div>

            """

            current_username = new_username

    content = f"""

    <div class="form-card">

        <h1>
            ⚙️ Admin Settings
        </h1>

        {message}


        <form method="POST">

            <div class="form-group">

                <label>
                    Admin Username
                </label>

                <input
                    type="text"
                    name="username"
                    value="{safe(current_username)}"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    Current Password
                </label>

                <input
                    type="password"
                    name="current_password"
                    placeholder="Enter current password"
                    required
                >

            </div>


            <div class="form-group">

                <label>
                    New Password
                </label>

                <input
                    type="password"
                    name="new_password"
                    placeholder="Leave blank to keep current password"
                >

            </div>


            <div class="form-group">

                <label>
                    Confirm New Password
                </label>

                <input
                    type="password"
                    name="confirm_password"
                    placeholder="Confirm new password"
                >

            </div>


            <button
                class="btn btn-primary"
                type="submit"
            >
                💾 Save Settings
            </button>

        </form>


        <div class="tip" style="margin-top:20px;">

            <b>
                🔐 Security Tip
            </b>

            <br>

            Use a strong password and do not share
            your administrator login information.

        </div>

    </div>

    """

    return page(
        "Admin Settings",
        content
    )


# ============================================================
# ERROR HANDLING
# ============================================================

@app.errorhandler(413)
def too_large(error):

    return page(
        "File Too Large",
        """
        <div class="alert alert-danger">

            ❌ The uploaded photo is too large.

            <br>

            Maximum allowed size is 5 MB.

        </div>

        <a
            href="/student/report"
            class="btn btn-secondary"
        >
            ← Back
        </a>
        """
    ), 413


@app.errorhandler(404)
def not_found(error):

    return page(
        "Page Not Found",
        """
        <div class="form-card" style="text-align:center;">

            <div style="font-size:60px;">
                🔍
            </div>

            <h1>
                Page Not Found
            </h1>

            <p>
                The page you are looking for does not exist.
            </p>

            <a
                href="/"
                class="btn btn-primary"
            >
                🏠 Go Home
            </a>

        </div>
        """,
        nav=False
    ), 404


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
