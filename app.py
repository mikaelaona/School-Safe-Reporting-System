from flask import Flask, render_template_string, request, jsonify
import sqlite3
import datetime
import random
import string

app = Flask(__name__)
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

    code = ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=6
        )
    )

    return "SS-" + code


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

/* HEADER */

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

/* CONTAINER */

.container {
    width: 92%;
    max-width: 850px;
    margin: 35px auto;
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

/* BUTTONS */

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

/* FORM */

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

/* REPORT ID */

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

/* MESSAGES */

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

/* HOME CARDS */

.card-container {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    margin-top: 25px;
}

.card {
    flex: 1;
    min-width: 220px;
    background: #f4f9ff;
    border: 1px solid #d5e8fa;
    padding: 20px;
    border-radius: 12px;
}

.card h3 {
    color: #1261a0;
}

/* TABLE */

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

.status {
    font-weight: bold;
}

/* FOOTER */

footer {
    text-align: center;
    margin: 30px;
    color: #666;
}

/* MOBILE */

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
# HOME PAGE
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

    <p>School Safety & Facility Reporting System</p>

</header>


<div class="container">

    <h2>Keep Our School Safe</h2>

    <p>
        Found a damaged, unsafe, or problematic
        school facility? Report it through
        SchoolSafe so the school administration
        can take action.
    </p>


    <div class="card-container">

        <div class="card">

            <h3>🚨 Report an Issue</h3>

            <p>
                Report broken or unsafe facilities
                around the school.
            </p>

            <a href="/report" class="btn">
                Report Problem
            </a>

        </div>


        <div class="card">

            <h3>🔎 Track Report</h3>

            <p>
                Check the current status of your
                submitted report.
            </p>

            <a href="/status" class="btn">
                Check Status
            </a>

        </div>


        <div class="card">

            <h3>👨‍💼 Admin</h3>

            <p>
                View reports and update their status.
            </p>

            <a href="/admin" class="btn">
                Admin Dashboard
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
# REPORT PAGE
# =========================================================

@app.route('/report', methods=['GET', 'POST'])
def report():

    if request.method == 'POST':

        reporter = request.form.get('reporter', '').strip()
        issue_type = request.form.get('issue_type', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        urgency = request.form.get('urgency', '').strip()

        if not reporter or not issue_type or not location or not description or not urgency:

            return render_template_string(
                STYLE + """

                <div class="container">

                    <h2>❌ Incomplete Report</h2>

                    <p class="error">
                        Please fill in all required fields.
                    </p>

                    <a href="/report" class="btn">
                        ← Go Back
                    </a>

                </div>

                """
            )

        report_id = generate_report_id()

        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().strftime("%H:%M")

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

<!DOCTYPE html>

<html>

<head>

    <title>Report Submitted</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>

<header>

    <h1>🏫 SchoolSafe</h1>

</header>


<div class="container">

    <h2>✅ Report Submitted!</h2>

    <p class="success">

        Your school safety report has been
        successfully submitted.

    </p>


    <p>
        Your Report ID is:
    </p>


    <div class="report-id">

        {report_id}

    </div>


    <p>

        Please save your Report ID.
        You will need it to check your
        report status.

    </p>


    <a href="/status" class="btn">
        🔎 Check Status
    </a>


    <a href="/" class="btn">
        🏠 Home
    </a>

</div>


</body>

</html>

"""
        )

    return render_template_string(
        STYLE + """

<!DOCTYPE html>

<html>

<head>

    <title>Report a Problem</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>🚨 Report a School Issue</h1>

    <p>SchoolSafe Reporting Form</p>

</header>


<div class="container">

    <h2>Submit a Safety Report</h2>


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

        <select name="issue_type" required>

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
            Description of the Problem
        </label>

        <textarea
            name="description"
            placeholder="Explain what happened or what is damaged..."
            required
        ></textarea>


        <label>
            Urgency
        </label>

        <select name="urgency" required>

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


        <button type="submit" class="btn">

            🚨 Submit Report

        </button>


    </form>


    <br>


    <a href="/">
        ← Back to Home
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# STATUS PAGE
# =========================================================

@app.route('/status', methods=['GET', 'POST'])
def status():

    result = ""

    if request.method == 'POST':

        report_id = request.form.get('report_id', '').strip()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        c.execute("""
            SELECT *
            FROM reports
            WHERE report_id = ?
        """, (report_id,))

        report = c.fetchone()

        conn.close()

        if report:

            result = f"""

            <div class="info">

                <h2>Report Found ✅</h2>

                <p>
                    <strong>Report ID:</strong>
                    {report[1]}
                </p>

                <p>
                    <strong>Reporter:</strong>
                    {report[2]}
                </p>

                <p>
                    <strong>Issue:</strong>
                    {report[3]}
                </p>

                <p>
                    <strong>Location:</strong>
                    {report[4]}
                </p>

                <p>
                    <strong>Description:</strong>
                    {report[5]}
                </p>

                <p>
                    <strong>Urgency:</strong>
                    {report[6]}
                </p>

                <p>
                    <strong>Status:</strong>

                    <span class="status">
                        {report[7]}
                    </span>

                </p>

                <p>
                    <strong>Date:</strong>
                    {report[8]}
                </p>

                <p>
                    <strong>Time:</strong>
                    {report[9]}
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

    <title>Check Status</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

</head>

<body>


<header>

    <h1>🔎 Check Report Status</h1>

</header>


<div class="container">

    <h2>Track Your Report</h2>


    <p>
        Enter the Report ID you received
        after submitting your report.
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


        <button type="submit" class="btn">

            🔎 Check Status

        </button>

    </form>


    {result}


    <br>


    <a href="/">
        ← Back to Home
    </a>


</div>


</body>

</html>

"""
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route('/admin')
def admin():

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
    """)

    reports = c.fetchall()

    conn.close()

    rows = ""

    for report in reports:

        rows += f"""

        <tr>

            <td>
                {report[1]}
            </td>

            <td>
                {report[2]}
            </td>

            <td>
                {report[3]}
            </td>

            <td>
                {report[4]}
            </td>

            <td>
                {report[5]}
            </td>

            <td>
                {report[6]}
            </td>

            <td>
                {report[7]}
            </td>

            <td>

                <form
                    method="POST"
                    action="/update/{report[0]}"
                >

                    <select name="status">

                        <option
                            {"selected" if report[7] == "Submitted" else ""}
                        >
                            Submitted
                        </option>

                        <option
                            {"selected" if report[7] == "Under Review" else ""}
                        >
                            Under Review
                        </option>

                        <option
                            {"selected" if report[7] == "In Progress" else ""}
                        >
                            In Progress
                        </option>

                        <option
                            {"selected" if report[7] == "Resolved" else ""}
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

    <h1>👨‍💼 SchoolSafe Admin</h1>

    <p>School Safety Reports</p>

</header>


<div class="container" style="max-width:1200px;">

    <h2>Reported Issues</h2>


    <table>

        <tr>

            <th>Report ID</th>

            <th>Reporter</th>

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


    <a href="/">
        ← Back to Home
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

    status = request.form.get('status')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        UPDATE reports
        SET status = ?
        WHERE id = ?
    """, (status, id))

    conn.commit()
    conn.close()

    return """
    <script>
        window.location.href = "/admin";
    </script>
    """


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == '__main__':

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )