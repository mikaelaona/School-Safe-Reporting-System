from flask import Flask, render_template_string, request, redirect, session
import sqlite3
import datetime
import random
import string
import os
import html

app = Flask(__name__)

# Secret key for login session
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "schoolsafe-secret-key"
)

DB_FILE = "schoolsafe.db"


# =========================================================
# DATABASE SETUP
# =========================================================

def init_db():

    conn = sqlite3.connect(DB_FILE)

    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            reporter TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            urgency TEXT NOT NULL,
            status TEXT NOT NULL,
            date_reported TEXT NOT NULL,
            time_reported TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# GENERATE REPORT ID
# =========================================================

def generate_report_id():

    while True:

        code = ''.join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        report_id = "SS-" + code

        conn = sqlite3.connect(DB_FILE)

        c = conn.cursor()

        c.execute(
            "SELECT id FROM reports WHERE report_id = ?",
            (report_id,)
        )

        existing = c.fetchone()

        conn.close()

        if not existing:
            return report_id


# =========================================================
# DESIGN
# =========================================================

STYLE = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #eef6ff;
    color: #222;
}

header {
    background: #1261a0;
    color: white;
    padding: 25px;
    text-align: center;
}

header h1 {
    margin: 0;
    font-size: 32px;
}

header p {
    margin: 8px 0 0;
}

.container {
    width: 92%;
    max-width: 850px;
    margin: 40px auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.10);
}

h2 {
    color: #1261a0;
}

p {
    line-height: 1.6;
}

.role-container {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 30px;
}

.role-card {
    width: 280px;
    background: #f4f9ff;
    border: 1px solid #d5e8fa;
    padding: 30px;
    border-radius: 15px;
    text-align: center;
}

.role-card h3 {
    color: #1261a0;
    font-size: 22px;
}

.role-card p {
    color: #555;
}

.btn {
    display: inline-block;
    background: #1261a0;
    color: white;
    padding: 13px 20px;
    margin: 8px 5px 8px 0;
    border-radius: 8px;
    text-decoration: none;
    border: none;
    cursor: pointer;
    font-size: 15px;
}

.btn:hover {
    background: #0b4778;
}

.btn-danger {
    background: #b52b2b;
}

.btn-danger:hover {
    background: #8d2020;
}

.btn-role {
    width: 100%;
    font-size: 17px;
    padding: 15px;
}

form {
    margin-top: 20px;
}

label {
    display: block;
    margin-top: 15px;
    font-weight: bold;
}

input,
select,
textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    border: 1px solid #ccc;
    border-radius: 7px;
    font-size: 15px;
}

textarea {
    height: 140px;
    resize: vertical;
}

.report-id {
    background: #e4f1ff;
    color: #1261a0;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    font-size: 30px;
    font-weight: bold;
    margin: 20px 0;
}

.success {
    color: green;
    font-weight: bold;
}

.error {
    color: red;
    font-weight: bold;
}

.info {
    background: #eef7ff;
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
}

.status {
    font-weight: bold;
}

.menu-container {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-top: 25px;
}

.menu-card {
    flex: 1;
    min-width: 250px;
    background: #f4f9ff;
    border: 1px solid #d5e8fa;
    padding: 25px;
    border-radius: 12px;
}

.menu-card h3 {
    color: #1261a0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    font-size: 14px;
}

th {
    background: #1261a0;
    color: white;
}

th,
td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}

footer {
    text-align: center;
    margin: 30px;
    color: #666;
}

@media(max-width: 600px) {

    .container {
        width: 95%;
        padding: 20px;
    }

    header h1 {
        font-size: 26px;
    }

    table {
        font-size: 12px;
    }

    th,
    td {
        padding: 7px;
    }

}

</style>
"""


# =========================================================
# FIRST PAGE - CHOOSE ROLE
# =========================================================

@app.route('/')
def index():

    return render_template_string(
        STYLE + """

<!DOCTYPE html>

<html>

<head>

    <title>SchoolSafe</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>🏫 SchoolSafe</h1>

    <p>School Issue Reporting System</p>

</header>


<div class="container">

    <h2 style="text-align:center;">
        Welcome to SchoolSafe
    </h2>


    <p style="text-align:center;">
        Please select your role to continue.
    </p>


    <div class="role-container">


        <!-- STUDENT -->

        <div class="role-card">

            <h3>👨‍🎓 Student</h3>

            <p>
                Report a school issue or
                track your submitted report.
            </p>

            <a
                href="/student"
                class="btn btn-role"
            >
                I am a Student
            </a>

        </div>


        <!-- ADMIN -->

        <div class="role-card">

            <h3>👨‍💼 Admin</h3>

            <p>
                Login to manage and monitor
                student reports.
            </p>

            <a
                href="/admin-login"
                class="btn btn-role"
            >
                I am an Admin
            </a>

        </div>


    </div>

</div>


<footer>

    SchoolSafe © 2026

</footer>


</body>

</html>

"""
    )


# =========================================================
# STUDENT PAGE
# =========================================================

@app.route('/student')
def student():

    return render_template_string(
        STYLE + """

<!DOCTYPE html>

<html>

<head>

    <title>Student - SchoolSafe</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>👨‍🎓 Student</h1>

    <p>SchoolSafe</p>

</header>


<div class="container">

    <h2>What would you like to do?</h2>


    <div class="menu-container">


        <!-- REPORT -->

        <div class="menu-card">

            <h3>🚨 Report an Issue</h3>

            <p>
                Report a damaged, unsafe, or
                problematic school facility.
            </p>

            <a
                href="/report"
                class="btn"
            >
                Report an Issue
            </a>

        </div>


        <!-- TRACK -->

        <div class="menu-card">

            <h3>🔎 Track Report</h3>

            <p>
                Check the current status of
                your submitted report.
            </p>

            <a
                href="/status"
                class="btn"
            >
                Track Report
            </a>

        </div>


    </div>


    <br>


    <a href="/" class="btn">
        ← Back
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# REPORT AN ISSUE
# =========================================================

@app.route('/report', methods=['GET', 'POST'])
def report():

    if request.method == 'POST':

        reporter = request.form.get(
            'reporter',
            ''
        ).strip()

        issue_type = request.form.get(
            'issue_type',
            ''
        ).strip()

        location = request.form.get(
            'location',
            ''
        ).strip()

        description = request.form.get(
            'description',
            ''
        ).strip()

        urgency = request.form.get(
            'urgency',
            ''
        ).strip()


        if (
            not reporter
            or not issue_type
            or not location
            or not description
            or not urgency
        ):

            return render_template_string(
                STYLE + """

                <div class="container">

                    <h2>❌ Incomplete Report</h2>

                    <p class="error">
                        Please fill in all required fields.
                    </p>

                    <a
                        href="/report"
                        class="btn"
                    >
                        ← Go Back
                    </a>

                </div>

                """
            )


        report_id = generate_report_id()

        today = datetime.date.today().isoformat()

        now = datetime.datetime.now().strftime(
            "%H:%M"
        )


        conn = sqlite3.connect(DB_FILE)

        c = conn.cursor()


        c.execute("""
            INSERT INTO reports
            (
                report_id,
                reporter,
                issue_type,
                location,
                description,
                urgency,
                status,
                date_reported,
                time_reported
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            report_id,
            reporter,
            issue_type,
            location,
            description,
            urgency,
            "Submitted",
            today,
            now

        ))


        conn.commit()

        conn.close()


        return render_template_string(
            STYLE + f"""

            <div class="container">

                <h2>✅ Report Submitted!</h2>

                <p class="success">
                    Your issue has been successfully
                    submitted.
                </p>


                <p>
                    Your Report ID is:
                </p>


                <div class="report-id">

                    {html.escape(report_id)}

                </div>


                <p>
                    Please save your Report ID.
                    You can use it to track your report.
                </p>


                <a
                    href="/status"
                    class="btn"
                >
                    🔎 Track Report
                </a>


                <a
                    href="/student"
                    class="btn"
                >
                    🏠 Student Page
                </a>

            </div>

            """
        )


    return render_template_string(
        STYLE + """

<!DOCTYPE html>

<html>

<head>

    <title>Report an Issue</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>🚨 Report an Issue</h1>

    <p>SchoolSafe</p>

</header>


<div class="container">

    <h2>Submit Your Report</h2>


    <form method="POST">


        <label>
            Your Name
        </label>

        <input
            type="text"
            name="reporter"
            placeholder="Enter your name"
            required
        >


        <label>
            Type of Issue
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
                Other
            </option>

        </select>


        <label>
            Location
        </label>

        <input
            type="text"
            name="location"
            placeholder="Example: Room 204"
            required
        >


        <label>
            Description
        </label>

        <textarea
            name="description"
            placeholder="Describe the problem..."
            required
        ></textarea>


        <label>
            Urgency
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


        <button
            type="submit"
            class="btn"
        >

            🚨 Submit Report

        </button>


    </form>


    <br>


    <a href="/student">
        ← Back to Student Page
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# TRACK REPORT
# =========================================================

@app.route('/status', methods=['GET', 'POST'])
def status():

    result = ""


    if request.method == 'POST':

        report_id = request.form.get(
            'report_id',
            ''
        ).strip()


        conn = sqlite3.connect(DB_FILE)

        c = conn.cursor()


        c.execute("""
            SELECT *
            FROM reports
            WHERE report_id = ?
        """, (report_id,))


        report_data = c.fetchone()

        conn.close()


        if report_data:

            result = f"""

            <div class="info">

                <h2>Report Found ✅</h2>


                <p>
                    <strong>Report ID:</strong>
                    {html.escape(report_data[1])}
                </p>


                <p>
                    <strong>Issue:</strong>
                    {html.escape(report_data[3])}
                </p>


                <p>
                    <strong>Location:</strong>
                    {html.escape(report_data[4])}
                </p>


                <p>
                    <strong>Description:</strong>
                    {html.escape(report_data[5])}
                </p>


                <p>
                    <strong>Urgency:</strong>
                    {html.escape(report_data[6])}
                </p>


                <p>
                    <strong>Status:</strong>

                    <span class="status">
                        {html.escape(report_data[7])}
                    </span>

                </p>


                <p>
                    <strong>Date Reported:</strong>
                    {html.escape(report_data[8])}
                </p>


                <p>
                    <strong>Time Reported:</strong>
                    {html.escape(report_data[9])}
                </p>

            </div>

            """


        else:

            result = """

            <p class="error">

                ❌ Report ID not found.

            </p>

            """


    return render_template_string(
        STYLE + f"""

<!DOCTYPE html>

<html>

<head>

    <title>Track Report</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>🔎 Track Report</h1>

    <p>SchoolSafe</p>

</header>


<div class="container">

    <h2>Track Your Report</h2>


    <p>
        Enter your Report ID to check
        the current status.
    </p>


    <form method="POST">


        <label>
            Report ID
        </label>


        <input
            type="text"
            name="report_id"
            placeholder="Example: SS-A1B2C3"
            required
        >


        <button
            type="submit"
            class="btn"
        >

            🔎 Track Report

        </button>


    </form>


    {result}


    <br>


    <a href="/student">
        ← Back to Student Page
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    message = ""


    if request.method == 'POST':

        username = request.form.get(
            'username',
            ''
        ).strip()

        password = request.form.get(
            'password',
            ''
        ).strip()


        # =================================================
        # ADMIN ACCOUNT
        # =================================================

        if (
            username == "admin"
            and password == "admin123"
        ):

            session['admin_logged_in'] = True

            return redirect('/admin')


        else:

            message = """

            <p class="error">

                ❌ Incorrect username or password.

            </p>

            """


    return render_template_string(
        STYLE + f"""

<!DOCTYPE html>

<html>

<head>

    <title>Admin Login</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>👨‍💼 Admin Login</h1>

    <p>SchoolSafe</p>

</header>


<div class="container">

    <h2>Administrator Login</h2>


    {message}


    <form method="POST">


        <label>
            Username
        </label>


        <input
            type="text"
            name="username"
            placeholder="Enter admin username"
            required
        >


        <label>
            Password
        </label>


        <input
            type="password"
            name="password"
            placeholder="Enter admin password"
            required
        >


        <button
            type="submit"
            class="btn"
        >

            🔐 Login

        </button>


    </form>


    <br>


    <a href="/">
        ← Back to Role Selection
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# ADMIN MENU
# =========================================================

@app.route('/admin')
def admin():

    if not session.get('admin_logged_in'):

        return redirect('/admin-login')


    return render_template_string(
        STYLE + """

<!DOCTYPE html>

<html>

<head>

    <title>Admin Panel</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>👨‍💼 SchoolSafe Admin</h1>

    <p>Administrator Panel</p>

</header>


<div class="container">

    <h2>Admin Menu</h2>


    <div class="menu-container">


        <!-- TRACK REPORT -->

        <div class="menu-card">

            <h3>🔎 Track Report</h3>

            <p>
                Search for a specific report
                using its Report ID.
            </p>


            <a
                href="/status"
                class="btn"
            >

                Track Report

            </a>

        </div>


        <!-- ADMIN DASHBOARD -->

        <div class="menu-card">

            <h3>📋 Admin Dashboard</h3>

            <p>
                View ALL student reports and
                update their status.
            </p>


            <a
                href="/admin-dashboard"
                class="btn"
            >

                Admin Dashboard

            </a>

        </div>


    </div>


    <br>


    <a
        href="/logout"
        class="btn btn-danger"
    >

        🚪 Logout

    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route('/admin-dashboard')
def admin_dashboard():

    if not session.get('admin_logged_in'):

        return redirect('/admin-login')


    conn = sqlite3.connect(DB_FILE)

    c = conn.cursor()


    # IMPORTANT:
    # Get ALL reports.
    # Nothing is deleted when a new report is submitted.

    c.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
    """)


    reports = c.fetchall()

    conn.close()


    rows = ""


    if not reports:

        rows = """

        <tr>

            <td
                colspan="8"
                style="text-align:center;"
            >

                No reports submitted yet.

            </td>

        </tr>

        """


    for report_data in reports:

        current_status = report_data[7]


        rows += f"""

        <tr>

            <td>
                {html.escape(report_data[1])}
            </td>


            <td>
                {html.escape(report_data[2])}
            </td>


            <td>
                {html.escape(report_data[3])}
            </td>


            <td>
                {html.escape(report_data[4])}
            </td>


            <td>
                {html.escape(report_data[5])}
            </td>


            <td>
                {html.escape(report_data[6])}
            </td>


            <td>
                {html.escape(current_status)}
            </td>


            <td>

                <form
                    method="POST"
                    action="/update/{report_data[0]}"
                >


                    <select name="status">


                        <option
                            value="Submitted"
                            {"selected" if current_status == "Submitted" else ""}
                        >
                            Submitted
                        </option>


                        <option
                            value="Under Review"
                            {"selected" if current_status == "Under Review" else ""}
                        >
                            Under Review
                        </option>


                        <option
                            value="In Progress"
                            {"selected" if current_status == "In Progress" else ""}
                        >
                            In Progress
                        </option>


                        <option
                            value="Resolved"
                            {"selected" if current_status == "Resolved" else ""}
                        >
                            Resolved
                        </option>


                    </select>


                    <button
                        type="submit"
                        class="btn"
                    >

                        Update

                    </button>


                </form>

            </td>

        </tr>

        """


    return render_template_string(
        STYLE + f"""

<!DOCTYPE html>

<html>

<head>

    <title>Admin Dashboard</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>📋 Admin Dashboard</h1>

    <p>All Student Reports</p>

</header>


<div
    class="container"
    style="max-width:1250px;"
>


    <h2>Submitted Reports</h2>


    <p>
        All student reports are displayed here.
        New reports are added to the list and
        existing reports remain saved.
    </p>


    <table>

        <tr>

            <th>Report ID</th>

            <th>Student</th>

            <th>Issue</th>

            <th>Location</th>

            <th>Description</th>

            <th>Urgency</th>

            <th>Status</th>

            <th>Action</th>

        </tr>


        {rows}


    </table>


    <br>


    <a
        href="/admin"
        class="btn"
    >

        ← Admin Menu

    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# UPDATE REPORT STATUS
# =========================================================

@app.route('/update/<int:id>', methods=['POST'])
def update(id):

    if not session.get('admin_logged_in'):

        return redirect('/admin-login')


    status_value = request.form.get(
        'status'
    )


    allowed_statuses = [
        "Submitted",
        "Under Review",
        "In Progress",
        "Resolved"
    ]


    if status_value not in allowed_statuses:

        return redirect('/admin-dashboard')


    conn = sqlite3.connect(DB_FILE)

    c = conn.cursor()


    c.execute("""
        UPDATE reports
        SET status = ?
        WHERE id = ?
    """, (
        status_value,
        id
    ))


    conn.commit()

    conn.close()


    return redirect('/admin-dashboard')


# =========================================================
# LOGOUT
# =========================================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == '__main__':

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )