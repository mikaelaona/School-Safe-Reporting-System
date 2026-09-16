from flask import Flask, render_template_string, request, redirect, session, url_for
import sqlite3
import datetime
import random
import string
import os
import html

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
            time_reported TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            date_posted TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_report_id():
    conn = get_db()

    while True:
        code = "SS-" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        existing = conn.execute(
            "SELECT id FROM reports WHERE report_id = ?",
            (code,)
        ).fetchone()

        if not existing:
            conn.close()
            return code


def safe(value):
    return html.escape(str(value or ""))


def admin_required():
    return session.get("admin_logged_in") is True


# ============================================================
# DESIGN
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
    padding: 16px 7%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 3px 15px rgba(0,0,0,.12);
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
    gap: 10px;
    align-items: center;
}

.nav-links a {
    color: white;
    padding: 9px 14px;
    border-radius: 8px;
    font-weight: bold;
}

.nav-links a:hover {
    background: rgba(255,255,255,.18);
}

.container {
    width: 90%;
    max-width: 1200px;
    margin: 35px auto;
}

.hero {
    background: linear-gradient(135deg, #0757c9, #1284ff);
    color: white;
    padding: 55px 30px;
    border-radius: 22px;
    text-align: center;
    box-shadow: 0 12px 30px rgba(0,80,190,.2);
}

.hero h1 {
    font-size: 42px;
    margin: 0 0 12px;
}

.hero p {
    font-size: 18px;
    margin-bottom: 25px;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 20px;
    margin-top: 28px;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 28px;
    box-shadow: 0 7px 25px rgba(0,0,0,.07);
    border: 1px solid #e3ecfa;
}

.card:hover {
    transform: translateY(-3px);
    transition: .2s;
}

.role-card {
    text-align: center;
    cursor: pointer;
}

.icon {
    font-size: 45px;
    margin-bottom: 12px;
}

h1, h2, h3 {
    color: #12345b;
}

.hero h1 {
    color: white;
}

.btn {
    display: inline-block;
    border: none;
    cursor: pointer;
    padding: 12px 19px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 14px;
    margin: 5px;
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
    max-width: 750px;
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
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.stat {
    background: white;
    padding: 22px;
    border-radius: 15px;
    box-shadow: 0 5px 18px rgba(0,0,0,.06);
}

.stat-number {
    font-size: 30px;
    font-weight: bold;
    color: #0757c9;
}

.stat-title {
    color: #667085;
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
    min-width: 950px;
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

@media(max-width: 700px) {

    .navbar {
        flex-direction: column;
        gap: 12px;
    }

    .nav-links {
        flex-wrap: wrap;
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
                <div class="logo">🛡️ School<span>Safe</span></div>

                <div class="nav-links">
                    <a href="/admin/dashboard">Dashboard</a>
                    <a href="/admin/reports">Reports</a>
                    <a href="/admin/announcements">Announcements</a>
                    <a href="/admin/logout">Logout</a>
                </div>
            </div>
            """
        else:
            navbar = """
            <div class="navbar">
                <div class="logo">🛡️ School<span>Safe</span></div>

                <div class="nav-links">
                    <a href="/student">Student Portal</a>
                    <a href="/">Home</a>
                </div>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{safe(title)} | SchoolSafe</title>
        {CSS}
    </head>

    <body>

        {navbar}

        <div class="container">
            {content}
        </div>

        <div class="footer">
            <b>SchoolSafe</b> — School Safety Reporting System<br>
            Keeping our school safer, one report at a time.
        </div>

    </body>
    </html>
    """


# ============================================================
# HOME / ROLE SELECTION
# ============================================================

@app.route("/")
def home():

    content = """
    <div class="hero">
        <div style="font-size:55px;">🛡️</div>

        <h1>Welcome to SchoolSafe</h1>

        <p>
            A simple and secure way to report school safety
            and facility problems.
        </p>

        <h3 style="color:white;">
            Are you a Student or an Admin?
        </h3>
    </div>

    <div class="card-grid">

        <a href="/student">
            <div class="card role-card">
                <div class="icon">🎓</div>

                <h2>Student</h2>

                <p>
                    Report school issues and track the status
                    of your submitted reports.
                </p>

                <span class="btn btn-primary">
                    Continue as Student
                </span>
            </div>
        </a>

        <a href="/admin/login">
            <div class="card role-card">
                <div class="icon">👨‍💼</div>

                <h2>Admin</h2>

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
    """

    return page("Home", content, nav=False)


# ============================================================
# STUDENT PORTAL
# ============================================================

@app.route("/student")
def student():

    conn = get_db()

    announcements = conn.execute("""
        SELECT * FROM announcements
        ORDER BY id DESC
        LIMIT 3
    """).fetchall()

    conn.close()

    announcement_html = ""

    if announcements:

        for a in announcements:
            announcement_html += f"""
            <div class="tip">
                <b>📢 {safe(a["title"])}</b><br>
                {safe(a["message"])}
                <br>
                <small>{safe(a["date_posted"])}</small>
            </div>
            """

    else:

        announcement_html = """
        <div class="tip">
            <b>📢 No announcements yet.</b><br>
            Check back later for school safety announcements.
        </div>
        """

    content = f"""
    <div class="hero">

        <div style="font-size:50px;">🎓</div>

        <h1>Student Portal</h1>

        <p>
            Report a problem or check the status of your report.
        </p>

        <a class="btn btn-light" href="/student/report">
            📝 Report an Issue
        </a>

        <a class="btn btn-light" href="/student/track">
            🔎 Track Report
        </a>

        <a class="btn btn-light" href="/student/my-reports">
            📋 My Reports
        </a>

    </div>

    <div class="card-grid">

        <div class="card">
            <div class="icon">📝</div>
            <h2>Report an Issue</h2>
            <p>
                Report broken equipment, damaged facilities,
                electrical problems, or other school safety concerns.
            </p>
        </div>

        <div class="card">
            <div class="icon">🔎</div>
            <h2>Track Report</h2>
            <p>
                Enter your Report ID to see whether your report
                is submitted, under review, in progress, or resolved.
            </p>
        </div>

        <div class="card">
            <div class="icon">📋</div>
            <h2>My Reports</h2>
            <p>
                View reports using the name you entered when
                submitting your reports.
            </p>
        </div>

    </div>

    <div class="card" style="margin-top:25px;">

        <h2>📢 School Announcements</h2>

        {announcement_html}

    </div>

    <div class="card" style="margin-top:25px;">

        <h2>💡 Safety Tips</h2>

        <div class="tip">
            <b>⚡ Electrical Safety</b><br>
            Do not touch exposed wires or damaged electrical equipment.
            Report them immediately.
        </div>

        <div class="tip">
            <b>🚪 Damaged Facilities</b><br>
            Avoid using broken doors, windows, chairs, or tables
            until they are repaired.
        </div>

        <div class="tip">
            <b>🧹 Slippery Floors</b><br>
            Report wet or slippery areas to help prevent accidents.
        </div>

        <div class="tip">
            <b>🚨 Emergency Problems</b><br>
            For serious and immediate danger, inform a teacher or
            school personnel immediately.
        </div>

    </div>
    """

    return page("Student Portal", content)


# ============================================================
# REPORT ISSUE
# ============================================================

@app.route("/student/report", methods=["GET", "POST"])
def report_issue():

    if request.method == "POST":

        reporter = request.form.get("reporter", "").strip()
        issue_type = request.form.get("issue_type", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        urgency = request.form.get("urgency", "").strip()

        if not reporter or not issue_type or not location or not description:

            content = """
            <div class="alert alert-danger">
                Please complete all required fields.
            </div>

            <a class="btn btn-secondary" href="/student/report">
                ← Back
            </a>
            """

            return page("Error", content)

        report_id = generate_report_id()

        now = datetime.datetime.now()

        date_reported = now.strftime("%Y-%m-%d")
        time_reported = now.strftime("%I:%M %p")

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
                time_reported
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            time_reported
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "report_success",
                report_id=report_id
            )
        )

    content = """
    <div class="form-card">

        <h1>📝 Report an Issue</h1>

        <p>
            Please provide accurate information about the
            school safety or facility problem.
        </p>

        <div class="alert alert-info">
            🔒 Your information will be used only for handling
            the reported school issue.
        </div>

        <form method="POST"
              onsubmit="return confirm('Are you sure you want to submit this report?');">

            <div class="form-group">

                <label>Your Name</label>

                <input
                    type="text"
                    name="reporter"
                    placeholder="Enter your name"
                    required
                >

            </div>

            <div class="form-group">

                <label>Issue Type</label>

                <select name="issue_type" required>

                    <option value="">-- Select Issue --</option>

                    <option>Broken Chair</option>
                    <option>Broken Table</option>
                    <option>Broken Electric Fan</option>
                    <option>Broken Light</option>
                    <option>Damaged Door</option>
                    <option>Broken Window</option>
                    <option>Electrical Problem</option>
                    <option>Comfort Room Problem</option>
                    <option>Roof Damage</option>
                    <option>Slippery Floor</option>
                    <option>Garbage / Cleanliness Problem</option>
                    <option>Other</option>

                </select>

            </div>

            <div class="form-group">

                <label>Location</label>

                <input
                    type="text"
                    name="location"
                    placeholder="Example: Room 204"
                    required
                >

            </div>

            <div class="form-group">

                <label>Urgency</label>

                <select name="urgency" required>

                    <option value="">-- Select Urgency --</option>

                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                    <option>Emergency</option>

                </select>

            </div>

            <div class="form-group">

                <label>Description</label>

                <textarea
                    name="description"
                    placeholder="Describe the problem..."
                    required
                ></textarea>

            </div>

            <button class="btn btn-primary" type="submit">
                🚀 Submit Report
            </button>

            <a class="btn btn-secondary" href="/student">
                Cancel
            </a>

        </form>

    </div>
    """

    return page("Report an Issue", content)


# ============================================================
# REPORT SUCCESS
# ============================================================

@app.route("/student/report-success/<report_id>")
def report_success(report_id):

    content = f"""
    <div class="form-card" style="text-align:center;">

        <div style="font-size:70px;">🎉</div>

        <h1>Report Submitted Successfully!</h1>

        <p>
            Thank you for helping make our school safer.
        </p>

        <p>
            Please save your Report ID.
        </p>

        <div class="report-id">
            {safe(report_id)}
        </div>

        <a class="btn btn-primary"
           href="/student/track?report_id={safe(report_id)}">
            🔎 Track This Report
        </a>

        <a class="btn btn-secondary" href="/student">
            Back to Student Portal
        </a>

    </div>
    """

    return page("Report Submitted", content)


# ============================================================
# STUDENT TRACK REPORT
# ============================================================

@app.route("/student/track")
def track_report():

    report_id = request.args.get("report_id", "").strip()

    report = None

    if report_id:

        conn = get_db()

        report = conn.execute("""
            SELECT * FROM reports
            WHERE report_id = ?
        """, (report_id,)).fetchone()

        conn.close()

    if not report:

        content = """
        <div class="form-card">

            <h1>🔎 Track Your Report</h1>

            <form method="GET">

                <div class="form-group">

                    <label>Report ID</label>

                    <input
                        type="text"
                        name="report_id"
                        placeholder="Example: SS-A1B2C3"
                        required
                    >

                </div>

                <button class="btn btn-primary" type="submit">
                    Track Report
                </button>

            </form>

        </div>
        """

        return page("Track Report", content)

    statuses = [
        "Submitted",
        "Under Review",
        "In Progress",
        "Resolved"
    ]

    current_status = report["status"]

    current_index = (
        statuses.index(current_status)
        if current_status in statuses
        else 0
    )

    steps = ""

    for i, status in enumerate(statuses):

        active = "active" if i <= current_index else ""

        steps += f"""
        <div class="step {active}">
            {i + 1}.<br>
            {safe(status)}
        </div>
        """

    content = f"""
    <div class="card">

        <h1>🔎 Report Status</h1>

        <div class="report-id">
            {safe(report["report_id"])}
        </div>

        <div class="steps">
            {steps}
        </div>

        <div class="card">

            <h2>Report Information</h2>

            <p>
                <b>Reporter:</b>
                {safe(report["reporter"])}
            </p>

            <p>
                <b>Issue:</b>
                {safe(report["issue_type"])}
            </p>

            <p>
                <b>Location:</b>
                {safe(report["location"])}
            </p>

            <p>
                <b>Urgency:</b>
                {safe(report["urgency"])}
            </p>

            <p>
                <b>Description:</b><br>
                {safe(report["description"])}
            </p>

            <p>
                <b>Date Reported:</b>
                {safe(report["date_reported"])}
            </p>

            <p>
                <b>Time Reported:</b>
                {safe(report["time_reported"])}
            </p>

            <p>
                <b>Current Status:</b>
                <span class="badge {status_class(current_status)}">
                    {safe(current_status)}
                </span>
            </p>

            <div class="alert alert-info">

                <b>📝 Admin Remarks:</b><br>

                {
                    safe(report["remarks"])
                    if report["remarks"]
                    else "No remarks yet. Please check again later."
                }

            </div>

        </div>

    </div>
    """

    return page("Track Report", content)


def status_class(status):

    mapping = {
        "Submitted": "submitted",
        "Under Review": "review",
        "In Progress": "progress",
        "Resolved": "resolved"
    }

    return mapping.get(status, "submitted")


# ============================================================
# MY REPORTS
# ============================================================

@app.route("/student/my-reports")
def my_reports():

    name = request.args.get("name", "").strip()

    reports = []

    if name:

        conn = get_db()

        reports = conn.execute("""
            SELECT * FROM reports
            WHERE LOWER(reporter) = LOWER(?)
            ORDER BY id DESC
        """, (name,)).fetchall()

        conn.close()

    rows = ""

    if reports:

        for report in reports:

            rows += f"""
            <tr>

                <td>
                    <b>{safe(report["report_id"])}</b>
                </td>

                <td>{safe(report["issue_type"])}</td>

                <td>{safe(report["location"])}</td>

                <td>
                    <span class="badge {status_class(report["status"])}">
                        {safe(report["status"])}
                    </span>
                </td>

                <td>
                    <a class="btn btn-primary"
                       href="/student/track?report_id={safe(report["report_id"])}">
                       View
                    </a>
                </td>

            </tr>
            """

    elif name:

        rows = """
        <tr>
            <td colspan="5" class="empty">
                No reports found for this name.
            </td>
        </tr>
        """

    content = f"""
    <div class="card">

        <h1>📋 My Reports</h1>

        <form method="GET">

            <div class="form-group">

                <label>Enter Your Name</label>

                <input
                    type="text"
                    name="name"
                    value="{safe(name)}"
                    placeholder="Enter the same name used when reporting"
                    required
                >

            </div>

            <button class="btn btn-primary">
                Search My Reports
            </button>

        </form>

    </div>

    {
        f'''
        <div class="table-container" style="margin-top:25px;">

            <table>

                <tr>
                    <th>Report ID</th>
                    <th>Issue</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>

                {rows}

            </table>

        </div>
        '''
        if name
        else ""
    }
    """

    return page("My Reports", content)


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    error = ""

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect("/admin/dashboard")

        error = """
        <div class="alert alert-danger">
            ❌ Invalid username or password.
        </div>
        """

    content = f"""
    <div class="form-card">

        <div style="text-align:center;font-size:55px;">
            👨‍💼
        </div>

        <h1 style="text-align:center;">
            Admin Login
        </h1>

        {error}

        <form method="POST">

            <div class="form-group">

                <label>Username</label>

                <input
                    type="text"
                    name="username"
                    placeholder="Enter admin username"
                    required
                >

            </div>

            <div class="form-group">

                <label>Password</label>

                <input
                    type="password"
                    name="password"
                    placeholder="Enter admin password"
                    required
                >

            </div>

            <button class="btn btn-primary" style="width:100%;">
                🔐 Login
            </button>

        </form>

        <div class="alert alert-info" style="margin-top:20px;">

            <b>Demo Login</b><br>
            Username: admin<br>
            Password: admin123

        </div>

        <a href="/" class="btn btn-secondary">
            ← Back
        </a>

    </div>
    """

    return page("Admin Login", content, nav=False)


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():
        return redirect("/admin/login")

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM reports"
    ).fetchone()[0]

    submitted = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Submitted'"
    ).fetchone()[0]

    review = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Under Review'"
    ).fetchone()[0]

    progress = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE status='In Progress'"
    ).fetchone()[0]

    resolved = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Resolved'"
    ).fetchone()[0]

    emergency = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE urgency='Emergency'"
    ).fetchone()[0]

    recent_reports = conn.execute("""
        SELECT * FROM reports
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    rows = ""

    for report in recent_reports:

        rows += f"""
        <tr>

            <td>
                <b>{safe(report["report_id"])}</b>
            </td>

            <td>{safe(report["issue_type"])}</td>

            <td>{safe(report["reporter"])}</td>

            <td>
                <span class="badge {status_class(report["status"])}">
                    {safe(report["status"])}
                </span>
            </td>

            <td>
                <a class="btn btn-primary"
                   href="/admin/reports">
                   Manage
                </a>
            </td>

        </tr>
        """

    content = f"""
    <h1>📊 Admin Dashboard</h1>

    <p>
        Welcome, Administrator. Manage and monitor school
        safety reports here.
    </p>

    <div class="stats">

        <div class="stat">
            <div class="stat-number">{total}</div>
            <div class="stat-title">Total Reports</div>
        </div>

        <div class="stat">
            <div class="stat-number">{submitted}</div>
            <div class="stat-title">Submitted</div>
        </div>

        <div class="stat">
            <div class="stat-number">{review}</div>
            <div class="stat-title">Under Review</div>
        </div>

        <div class="stat">
            <div class="stat-number">{progress}</div>
            <div class="stat-title">In Progress</div>
        </div>

        <div class="stat">
            <div class="stat-number">{resolved}</div>
            <div class="stat-title">Resolved</div>
        </div>

        <div class="stat">
            <div class="stat-number">{emergency}</div>
            <div class="stat-title">Emergency</div>
        </div>

    </div>

    <div class="card-grid">

        <div class="card">

            <div class="icon">📋</div>

            <h2>Manage Reports</h2>

            <p>
                View reports, search for specific reports,
                update status, and add admin remarks.
            </p>

            <a class="btn btn-primary" href="/admin/reports">
                Open Reports
            </a>

        </div>

        <div class="card">

            <div class="icon">📢</div>

            <h2>Announcements</h2>

            <p>
                Create safety announcements that students
                can see on the Student Portal.
            </p>

            <a class="btn btn-primary"
               href="/admin/announcements">
                Manage Announcements
            </a>

        </div>

    </div>

    <div class="table-container" style="margin-top:25px;">

        <h2>Recent Reports</h2>

        <table>

            <tr>
                <th>Report ID</th>
                <th>Issue</th>
                <th>Reporter</th>
                <th>Status</th>
                <th>Action</th>
            </tr>

            {
                rows
                if rows
                else '''
                <tr>
                    <td colspan="5" class="empty">
                        No reports yet.
                    </td>
                </tr>
                '''
            }

        </table>

    </div>
    """

    return page("Admin Dashboard", content)


# ============================================================
# ADMIN REPORTS
# ============================================================

@app.route("/admin/reports")
def admin_reports():

    if not admin_required():
        return redirect("/admin/login")

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db()

    query = "SELECT * FROM reports WHERE 1=1"
    params = []

    if search:

        query += """
        AND (
            report_id LIKE ?
            OR reporter LIKE ?
            OR issue_type LIKE ?
            OR location LIKE ?
        )
        """

        term = f"%{search}%"

        params.extend([
            term,
            term,
            term,
            term
        ])

    if status_filter:

        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"

    reports = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    rows = ""

    for report in reports:

        rows += f"""
        <tr>

            <td>
                <b>{safe(report["report_id"])}</b><br>
                <small>
                    {safe(report["date_reported"])}
                    {safe(report["time_reported"])}
                </small>
            </td>

            <td>
                {safe(report["reporter"])}
            </td>

            <td>
                {safe(report["issue_type"])}
            </td>

            <td>
                {safe(report["location"])}
            </td>

            <td>

                <span class="badge {status_class(report["status"])}">
                    {safe(report["status"])}
                </span>

                <br><br>

                <span class="badge {safe(report["urgency"]).lower()}">
                    {safe(report["urgency"])}
                </span>

            </td>

            <td>

                <form method="POST"
                      action="/admin/update-report/{safe(report["id"])}">

                    <select name="status">

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

                    <br>

                    <textarea
                        name="remarks"
                        placeholder="Admin remarks..."
                        style="min-height:80px;margin-top:8px;"
                    >{safe(report["remarks"])}</textarea>

                    <button class="btn btn-success">
                        💾 Save
                    </button>

                </form>

            </td>

        </tr>
        """

    content = f"""
    <h1>📋 Manage Reports</h1>

    <div class="search-box">

        <form method="GET">

            <div class="card-grid">

                <div>

                    <label>Search</label>

                    <input
                        type="text"
                        name="search"
                        value="{safe(search)}"
                        placeholder="Report ID, name, issue, location..."
                    >

                </div>

                <div>

                    <label>Status</label>

                    <select name="status">

                        <option value="">All Statuses</option>

                        <option
                            value="Submitted"
                            {"selected" if status_filter == "Submitted" else ""}
                        >
                            Submitted
                        </option>

                        <option
                            value="Under Review"
                            {"selected" if status_filter == "Under Review" else ""}
                        >
                            Under Review
                        </option>

                        <option
                            value="In Progress"
                            {"selected" if status_filter == "In Progress" else ""}
                        >
                            In Progress
                        </option>

                        <option
                            value="Resolved"
                            {"selected" if status_filter == "Resolved" else ""}
                        >
                            Resolved
                        </option>

                    </select>

                </div>

            </div>

            <button class="btn btn-primary">
                🔍 Search
            </button>

            <a class="btn btn-secondary"
               href="/admin/reports">
                Clear
            </a>

        </form>

    </div>

    <div class="table-container">

        <table>

            <tr>

                <th>Report</th>
                <th>Reporter</th>
                <th>Issue</th>
                <th>Location</th>
                <th>Status / Urgency</th>
                <th>Manage</th>

            </tr>

            {
                rows
                if rows
                else '''
                <tr>
                    <td colspan="6" class="empty">
                        No reports found.
                    </td>
                </tr>
                '''
            }

        </table>

    </div>
    """

    return page("Manage Reports", content)


# ============================================================
# UPDATE REPORT
# ============================================================

@app.route("/admin/update-report/<int:report_db_id>", methods=["POST"])
def update_report(report_db_id):

    if not admin_required():
        return redirect("/admin/login")

    status = request.form.get("status", "Submitted")
    remarks = request.form.get("remarks", "").strip()

    allowed_statuses = [
        "Submitted",
        "Under Review",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        status = "Submitted"

    conn = get_db()

    conn.execute("""
        UPDATE reports
        SET status = ?, remarks = ?
        WHERE id = ?
    """, (
        status,
        remarks,
        report_db_id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin/reports")


# ============================================================
# ADMIN ANNOUNCEMENTS
# ============================================================

@app.route("/admin/announcements", methods=["GET", "POST"])
def admin_announcements():

    if not admin_required():
        return redirect("/admin/login")

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()

        if title and message:

            now = datetime.datetime.now()

            date_posted = now.strftime("%Y-%m-%d %I:%M %p")

            conn = get_db()

            conn.execute("""
                INSERT INTO announcements
                (title, message, date_posted)
                VALUES (?, ?, ?)
            """, (
                title,
                message,
                date_posted
            ))

            conn.commit()
            conn.close()

        return redirect("/admin/announcements")

    conn = get_db()

    announcements = conn.execute("""
        SELECT * FROM announcements
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    announcement_rows = ""

    for a in announcements:

        announcement_rows += f"""
        <div class="card" style="margin-bottom:15px;">

            <h2>📢 {safe(a["title"])}</h2>

            <p>
                {safe(a["message"])}
            </p>

            <small>
                Posted: {safe(a["date_posted"])}
            </small>

            <form method="POST"
                  action="/admin/delete-announcement/{safe(a["id"])}"
                  style="margin-top:10px;">

                <button
                    class="btn btn-danger"
                    onclick="return confirm('Delete this announcement?');"
                >
                    Delete
                </button>

            </form>

        </div>
        """

    content = f"""
    <h1>📢 Announcements</h1>

    <div class="form-card">

        <h2>Create Announcement</h2>

        <form method="POST">

            <div class="form-group">

                <label>Announcement Title</label>

                <input
                    type="text"
                    name="title"
                    placeholder="Example: School Clean-up Drive"
                    required
                >

            </div>

            <div class="form-group">

                <label>Message</label>

                <textarea
                    name="message"
                    placeholder="Write your announcement..."
                    required
                ></textarea>

            </div>

            <button class="btn btn-primary">
                📢 Post Announcement
            </button>

        </form>

    </div>

    <div style="margin-top:30px;">

        <h2>Posted Announcements</h2>

        {
            announcement_rows
            if announcement_rows
            else '''
            <div class="card empty">
                No announcements yet.
            </div>
            '''
        }

    </div>
    """

    return page("Announcements", content)


# ============================================================
# DELETE ANNOUNCEMENT
# ============================================================

@app.route(
    "/admin/delete-announcement/<int:announcement_id>",
    methods=["POST"]
)
def delete_announcement(announcement_id):

    if not admin_required():
        return redirect("/admin/login")

    conn = get_db()

    conn.execute("""
        DELETE FROM announcements
        WHERE id = ?
    """, (announcement_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/announcements")


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    # IMPORTANT:
    # This only removes the ADMIN LOGIN SESSION.
    # It does NOT delete reports.
    # Reports remain permanently stored in schoolsafe.db.

    session.clear()

    return redirect("/")


# ============================================================
# START APPLICATION
# ============================================================

init_db()

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )