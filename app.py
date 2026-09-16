from flask import Flask, render_template_string, request, redirect, session
import sqlite3
import datetime
import random
import string
import os
import html
import hmac

app = Flask(__name__)

# =========================================================
# SECRET KEY
# =========================================================
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "schoolsafe-change-this-secret-key"
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

        exists = c.fetchone()

        conn.close()

        if not exists:
            return report_id


# =========================================================
# CHECK ADMIN LOGIN
# =========================================================
def is_admin():
    return session.get("admin_logged_in", False)


# =========================================================
# STATUS COLORS
# =========================================================
def status_class(status):

    return {
        "Submitted": "submitted",
        "Under Review": "review",
        "In Progress": "progress",
        "Resolved": "resolved"
    }.get(status, "submitted")


# =========================================================
# URGENCY COLORS
# =========================================================
def urgency_class(urgency):

    return {
        "Low": "low",
        "Medium": "medium",
        "High": "high",
        "Emergency": "emergency"
    }.get(urgency, "medium")


# =========================================================
# PROFESSIONAL DESIGN
# =========================================================
STYLE = """

<style>

/* ================================
   GENERAL
================================ */

:root {

    --blue: #1261a0;
    --blue-dark: #083b66;
    --blue-light: #eaf4ff;
    --cyan: #27a7e7;

    --green: #168a57;
    --orange: #e28a16;
    --red: #c73636;

    --text: #172033;
    --muted: #667085;

    --border: #dce6f0;

    --bg: #f4f8fc;
    --white: #ffffff;

    --shadow:
        0 18px 45px rgba(18, 61, 96, .12);
}


* {
    box-sizing: border-box;
}


body {

    margin: 0;

    font-family:
        Inter,
        Segoe UI,
        Arial,
        sans-serif;

    color: var(--text);

    background:

        radial-gradient(
            circle at 10% 0%,
            rgba(39, 167, 231, .10),
            transparent 28%
        ),

        radial-gradient(
            circle at 90% 10%,
            rgba(18, 97, 160, .10),
            transparent 25%
        ),

        var(--bg);
}


a {
    color: inherit;
}


/* ================================
   TOP BAR
================================ */

.topbar {

    background:
        linear-gradient(
            135deg,
            var(--blue-dark),
            var(--blue),
            #1885c7
        );

    color: white;

    padding: 18px 5%;

    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 20px;

    box-shadow:
        0 8px 25px
        rgba(8, 59, 102, .20);
}


.brand {

    display: flex;

    align-items: center;

    gap: 12px;
}


.brand-icon {

    width: 46px;
    height: 46px;

    border-radius: 14px;

    display: grid;

    place-items: center;

    background:
        rgba(255,255,255,.16);

    font-size: 24px;

    border:
        1px solid
        rgba(255,255,255,.22);
}


.brand h1 {

    font-size: 22px;

    margin: 0;
}


.brand small {

    opacity: .82;
}


/* ================================
   CONTAINER
================================ */

.container {

    width: 92%;

    max-width: 1050px;

    margin: 38px auto;

    background:
        rgba(255,255,255,.96);

    padding: 34px;

    border:
        1px solid
        rgba(220,230,240,.9);

    border-radius: 24px;

    box-shadow:
        var(--shadow);
}


.wide {

    max-width: 1400px;
}


/* ================================
   HERO
================================ */

.hero {

    text-align: center;

    padding:
        10px 0 5px;
}


.hero h2 {

    font-size: 34px;

    margin:
        5px 0 10px;

    color:
        var(--blue-dark);
}


.hero p {

    max-width: 650px;

    margin: 0 auto;

    color: var(--muted);

    line-height: 1.7;
}


/* ================================
   CARDS
================================ */

.role-container,
.menu-container,
.stats {

    display: grid;

    grid-template-columns:
        repeat(
            2,
            minmax(0, 1fr)
        );

    gap: 20px;

    margin-top: 30px;
}


.role-card,
.menu-card {

    background:
        linear-gradient(
            180deg,
            #fff,
            #f8fbff
        );

    border:
        1px solid
        var(--border);

    padding: 28px;

    border-radius: 20px;

    transition: .2s;

    position: relative;

    overflow: hidden;
}


.role-card:hover,
.menu-card:hover {

    transform:
        translateY(-4px);

    box-shadow:
        0 14px 30px
        rgba(18,97,160,.12);
}


.role-card:before,
.menu-card:before {

    content: "";

    position: absolute;

    left: 0;

    top: 0;

    width: 100%;

    height: 4px;

    background:
        linear-gradient(
            90deg,
            var(--blue),
            var(--cyan)
        );
}


.icon-circle {

    width: 58px;

    height: 58px;

    border-radius: 18px;

    background:
        var(--blue-light);

    display: grid;

    place-items: center;

    font-size: 27px;

    margin-bottom: 14px;
}


h2,
h3 {

    color:
        var(--blue-dark);
}


p {

    line-height: 1.65;
}


.muted {

    color:
        var(--muted);
}


/* ================================
   BUTTONS
================================ */

.btn {

    display: inline-flex;

    align-items: center;

    justify-content: center;

    gap: 8px;

    background:
        linear-gradient(
            135deg,
            var(--blue),
            #1885c7
        );

    color: white;

    padding:
        12px 18px;

    margin:
        8px 5px 0 0;

    border-radius: 11px;

    text-decoration: none;

    border: 0;

    cursor: pointer;

    font-size: 15px;

    font-weight: 700;

    box-shadow:
        0 7px 18px
        rgba(18,97,160,.18);
}


.btn:hover {

    filter:
        brightness(.94);

    transform:
        translateY(-1px);
}


.btn-secondary {

    background:
        #eef5fb;

    color:
        var(--blue-dark);

    box-shadow: none;
}


.btn-danger {

    background:
        linear-gradient(
            135deg,
            #b52b2b,
            #d44949
        );
}


.btn-full {

    width: 100%;
}


/* ================================
   FORMS
================================ */

form {

    margin-top: 20px;
}


.form-grid {

    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap:
        0 18px;
}


.full {

    grid-column:
        1 / -1;
}


label {

    display: block;

    margin-top: 16px;

    font-weight: 700;

    font-size: 14px;
}


input,
select,
textarea {

    width: 100%;

    padding:
        13px 14px;

    margin-top: 7px;

    border:
        1px solid
        #ccd8e4;

    border-radius: 11px;

    font-size: 15px;

    background:
        #fff;

    outline: none;

    transition: .2s;
}


input:focus,
select:focus,
textarea:focus {

    border-color:
        var(--cyan);

    box-shadow:
        0 0 0 4px
        rgba(39,167,231,.10);
}


textarea {

    min-height: 145px;

    resize: vertical;
}


/* ================================
   NOTICE
================================ */

.notice {

    background:
        #f0f8ff;

    border:
        1px solid
        #cfe8fb;

    padding:
        17px 18px;

    border-radius:
        14px;

    margin-top:
        18px;

    color:
        #31546f;
}


/* ================================
   SUCCESS
================================ */

.success-box {

    text-align:
        center;

    background:
        linear-gradient(
            180deg,
            #f2fff9,
            #fff
        );

    border:
        1px solid
        #c8eddc;

    padding:
        28px;

    border-radius:
        20px;
}


.report-id {

    background:
        linear-gradient(
            135deg,
            #e9f5ff,
            #f6fbff
        );

    color:
        var(--blue-dark);

    padding:
        18px;

    border-radius:
        14px;

    text-align:
        center;

    font-size:
        30px;

    font-weight:
        800;

    letter-spacing:
        2px;

    margin:
        18px 0;

    border:
        1px dashed
        #9cccf0;
}


.success {

    color:
        var(--green);

    font-weight:
        700;
}


.error {

    color:
        var(--red);

    font-weight:
        700;
}


/* ================================
   INFORMATION
================================ */

.info {

    background:
        #f8fbff;

    padding:
        22px;

    border-radius:
        17px;

    margin-top:
        20px;

    border:
        1px solid
        var(--border);
}


/* ================================
   BADGES
================================ */

.status,
.badge {

    display:
        inline-flex;

    padding:
        5px 10px;

    border-radius:
        999px;

    font-weight:
        800;

    font-size:
        12px;
}


.submitted {

    background:
        #eaf3ff;

    color:
        #24639a;
}


.review {

    background:
        #fff5d9;

    color:
        #946300;
}


.progress {

    background:
        #efe9ff;

    color:
        #6942a5;
}


.resolved {

    background:
        #e5f8ef;

    color:
        #17734b;
}


.low {

    background:
        #eaf7ef;

    color:
        #237449;
}


.medium {

    background:
        #fff4d8;

    color:
        #956300;
}


.high {

    background:
        #ffe9d9;

    color:
        #a74d10;
}


.emergency {

    background:
        #ffe3e3;

    color:
        #a92727;
}


/* ================================
   ADMIN STATISTICS
================================ */

.stats {

    grid-template-columns:
        repeat(
            4,
            minmax(0, 1fr)
        );

    margin-top:
        22px;
}


.stat {

    background:
        #fff;

    border:
        1px solid
        var(--border);

    border-radius:
        16px;

    padding:
        18px;
}


.stat span {

    display:
        block;

    color:
        var(--muted);

    font-size:
        13px;
}


.stat strong {

    font-size:
        28px;

    color:
        var(--blue-dark);
}


/* ================================
   TABLE
================================ */

.table-wrap {

    overflow-x:
        auto;

    border:
        1px solid
        var(--border);

    border-radius:
        15px;

    margin-top:
        20px;
}


table {

    width:
        100%;

    border-collapse:
        collapse;

    min-width:
        1050px;

    font-size:
        14px;
}


th {

    background:
        var(--blue-dark);

    color:
        #fff;

    text-align:
        left;
}


th,
td {

    border-bottom:
        1px solid
        var(--border);

    padding:
        12px;

    vertical-align:
        top;
}


tr:nth-child(even) {

    background:
        #f9fbfd;
}


/* ================================
   SEARCH
================================ */

.searchbar {

    display:
        flex;

    gap:
        10px;

    margin-top:
        18px;
}


.searchbar input {

    margin:
        0;

    flex:
        1;
}


/* ================================
   STEPS
================================ */

.step-list {

    display:
        grid;

    gap:
        10px;

    margin-top:
        16px;
}


.step {

    display:
        flex;

    gap:
        12px;

    align-items:
        flex-start;
}


.step-num {

    min-width:
        30px;

    height:
        30px;

    border-radius:
        50%;

    background:
        var(--blue);

    color:
        #fff;

    display:
        grid;

    place-items:
        center;

    font-weight:
        800;

    font-size:
        13px;
}


/* ================================
   FOOTER
================================ */

.footer {

    text-align:
        center;

    padding:
        25px;

    color:
        #738094;

    font-size:
        13px;
}


/* ================================
   MOBILE
================================ */

@media(max-width:800px) {

    .role-container,
    .menu-container,
    .stats,
    .form-grid {

        grid-template-columns:
            1fr;
    }

    .full {

        grid-column:
            auto;
    }

    .container {

        padding:
            23px;

        margin:
            22px auto;
    }

    .hero h2 {

        font-size:
            28px;
    }

    .topbar {

        padding:
            15px 4%;
    }
}


@media(max-width:520px) {

    .searchbar {

        flex-direction:
            column;
    }

    .btn {

        width:
            100%;
    }
}

</style>

"""


# =========================================================
# PAGE TEMPLATE
# =========================================================
def page(
    title,
    body,
    top_title="🏫 SchoolSafe",
    top_subtitle="School Issue Reporting System"
):

    return render_template_string(

        STYLE +

        f"""

<!DOCTYPE html>

<html>

<head>

<title>
{html.escape(title)}
</title>

<meta
name="viewport"
content="width=device-width, initial-scale=1"
>

</head>


<body>


<header class="topbar">

    <div class="brand">

        <div class="brand-icon">
            🛡️
        </div>

        <div>

            <h1>
                {top_title}
            </h1>

            <small>
                {top_subtitle}
            </small>

        </div>

    </div>

</header>


{body}


<footer class="footer">

    SchoolSafe © {datetime.date.today().year}

    • Safer schools, faster action.

</footer>


</body>

</html>

"""
    )


# =========================================================
# HOME / ROLE SELECTION
# =========================================================
@app.route("/")
def index():

    return page(
        "SchoolSafe",
        """

<main class="container">


<section class="hero">

    <div
        class="icon-circle"
        style="margin:0 auto"
    >
        🛡️
    </div>


    <h2>
        Welcome to SchoolSafe
    </h2>


    <p>

        A simple and secure way to
        report school facility issues
        and monitor their progress.

    </p>

</section>


<div class="role-container">


<!-- STUDENT -->

<div class="role-card">

    <div class="icon-circle">
        🎓
    </div>


    <h3>
        Student Portal
    </h3>


    <p class="muted">

        Report a school issue or
        check the status of a
        submitted report.

    </p>


    <a
        href="/student"
        class="btn btn-full"
    >

        Continue as Student →

    </a>

</div>


<!-- ADMIN -->

<div class="role-card">

    <div class="icon-circle">
        🔐
    </div>


    <h3>
        Administrator Portal
    </h3>


    <p class="muted">

        Review reports,
        monitor urgent concerns,
        and update report status.

    </p>


    <a
        href="/admin-login"
        class="btn btn-full"
    >

        Continue as Admin →

    </a>

</div>


</div>


<div class="notice">

<strong>
💡 How SchoolSafe works:
</strong>


Students submit a report and
receive a unique Report ID.

Administrators review the report
and update its status so students
can track its progress.


</div>


</main>

"""
    )


# =========================================================
# STUDENT PAGE
# =========================================================
@app.route("/student")
def student():

    return page(
        "Student Portal",
        """

<main class="container">


<section class="hero">

    <div
        class="icon-circle"
        style="margin:0 auto"
    >
        🎓
    </div>


    <h2>
        Student Portal
    </h2>


    <p>
        What would you like to do today?
    </p>

</section>


<div class="menu-container">


<!-- REPORT -->

<div class="menu-card">

    <div class="icon-circle">
        🚨
    </div>


    <h3>
        Report an Issue
    </h3>


    <p class="muted">

        Tell the school about a
        damaged, unsafe, or
        problematic facility.

    </p>


    <a
        href="/report"
        class="btn"
    >

        Create a Report →

    </a>

</div>


<!-- TRACK -->

<div class="menu-card">

    <div class="icon-circle">
        🔎
    </div>


    <h3>
        Track Report
    </h3>


    <p class="muted">

        Enter your Report ID
        to see the latest status
        of your concern.

    </p>


    <a
        href="/status"
        class="btn"
    >

        Track My Report →

    </a>

</div>


</div>


<div class="notice">

<strong>
🔒 Privacy reminder:
</strong>

Only submit information needed
to describe the issue.

Do not include passwords or
other sensitive personal information.

</div>


<a
    href="/"
    class="btn btn-secondary"
>

    ← Back to Home

</a>


</main>

"""
    )


# =========================================================
# REPORT AN ISSUE
# =========================================================
@app.route("/report", methods=["GET", "POST"])
def report():

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


        if not all([
            reporter,
            issue_type,
            location,
            description,
            urgency
        ]):

            return page(
                "Incomplete Report",
                """

<main class="container">

<h2>
⚠️ Incomplete Report
</h2>


<p class="error">

Please fill in all required
fields before submitting.

</p>


<a
    href="/report"
    class="btn"
>

← Go Back

</a>

</main>

"""
            )


        report_id = generate_report_id()


        now_dt = datetime.datetime.now()


        today = now_dt.date().isoformat()


        now = now_dt.strftime("%H:%M")


        conn = sqlite3.connect(DB_FILE)


        c = conn.cursor()


        c.execute(
            """

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

            """,

            (
                report_id,
                reporter,
                issue_type,
                location,
                description,
                urgency,
                "Submitted",
                today,
                now
            )
        )


        conn.commit()


        conn.close()


        return page(
            "Report Submitted",
            f"""

<main class="container">


<div class="success-box">


<div
    class="icon-circle"
    style="margin:0 auto"
>

    ✅

</div>


<h2>

Report Submitted Successfully!

</h2>


<p class="success">

Your school issue has been recorded.

</p>


<p>

Your unique Report ID is:

</p>


<div class="report-id">

{html.escape(report_id)}

</div>


<p class="muted">

<strong>
Save this ID.
</strong>

You will need it to track
your report.

</p>


<a
    href="/status"
    class="btn"
>

🔎 Track Report

</a>


<a
    href="/student"
    class="btn btn-secondary"
>

🏠 Student Portal

</a>


</div>


</main>

"""
        )


    return page(
        "Report an Issue",
        """

<main class="container">


<section class="hero">


<div
    class="icon-circle"
    style="margin:0 auto"
>

🚨

</div>


<h2>

Report a School Issue

</h2>


<p>

Please provide accurate
information so the concern
can be reviewed quickly.

</p>


</section>


<form
    method="POST"
    onsubmit="return confirm(
        'Are you sure you want to submit this report?'
    );"
>


<div class="form-grid">


<div>

<label>
Your Name *
</label>


<input
    type="text"
    name="reporter"
    placeholder="Enter your name"
    maxlength="100"
    required
>

</div>


<div>

<label>
Type of Issue *
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

</div>


<div>

<label>
Location *
</label>


<input
    type="text"
    name="location"
    placeholder="Example: Room 204"
    maxlength="120"
    required
>

</div>


<div>

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


<div class="full">

<label>
Description *
</label>


<textarea
    name="description"
    placeholder="Describe what happened, where it is, and why it needs attention..."
    maxlength="2000"
    required
></textarea>

</div>


</div>


<div class="notice">

<strong>
Before submitting:
</strong>

Check the location,
issue type, and urgency.

Accurate details help
administrators respond appropriately.

</div>


<button
    type="submit"
    class="btn"
>

🚨 Submit Report

</button>


<a
    href="/student"
    class="btn btn-secondary"
>

Cancel

</a>


</form>


</main>

"""
    )


# =========================================================
# TRACK REPORT
# =========================================================
@app.route("/status", methods=["GET", "POST"])
def status():

    result = ""


    if request.method == "POST":

        report_id = request.form.get(
            "report_id",
            ""
        ).strip().upper()


        conn = sqlite3.connect(DB_FILE)


        c = conn.cursor()


        c.execute(
            """

            SELECT *

            FROM reports

            WHERE report_id = ?

            """,

            (report_id,)
        )


        report_data = c.fetchone()


        conn.close()


        if report_data:

            result = f"""

<div class="info">


<h2>
Report Found ✅
</h2>


<p>

<strong>
Report ID:
</strong>

{html.escape(report_data[1])}

</p>


<p>

<strong>
Issue:
</strong>

{html.escape(report_data[3])}

</p>


<p>

<strong>
Location:
</strong>

{html.escape(report_data[4])}

</p>


<p>

<strong>
Description:
</strong>

{html.escape(report_data[5])}

</p>


<p>

<strong>
Urgency:
</strong>


<span class="badge {urgency_class(report_data[6])}">

{html.escape(report_data[6])}

</span>


</p>


<p>

<strong>
Status:
</strong>


<span class="status {status_class(report_data[7])}">

{html.escape(report_data[7])}

</span>


</p>


<p>

<strong>
Date Reported:
</strong>

{html.escape(report_data[8])}

</p>


<p>

<strong>
Time Reported:
</strong>

{html.escape(report_data[9])}

</p>


<div class="step-list">


<div class="step">

<span class="step-num">
1
</span>

<span>

<strong>
Submitted
</strong>

— Your report has been received.

</span>

</div>


<div class="step">

<span class="step-num">
2
</span>

<span>

<strong>
Under Review
</strong>

— An administrator is checking the concern.

</span>

</div>


<div class="step">

<span class="step-num">
3
</span>

<span>

<strong>
In Progress
</strong>

— Action is being taken.

</span>

</div>


<div class="step">

<span class="step-num">
4
</span>

<span>

<strong>
Resolved
</strong>

— The reported concern has been addressed.

</span>

</div>


</div>


</div>

"""


        else:

            result = """

<p class="error">

❌ Report ID not found.

Please check the ID and
try again.

</p>

"""


    return page(
        "Track Report",
        f"""

<main class="container">


<section class="hero">


<div
    class="icon-circle"
    style="margin:0 auto"
>

🔎

</div>


<h2>

Track Your Report

</h2>


<p>

Enter the Report ID you received
after submitting your concern.

</p>


</section>


<form method="POST">


<label>

Report ID *

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

🔎 Check Status

</button>


<a
    href="/student"
    class="btn btn-secondary"
>

← Student Portal

</a>


</form>


{result}


</main>

"""
    )


# =========================================================
# ADMIN LOGIN
# =========================================================
@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    message = ""


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        password = request.form.get(
            "password",
            ""
        ).strip()


        if (

            hmac.compare_digest(
                username,
                "admin"
            )

            and

            hmac.compare_digest(
                password,
                "admin123"
            )

        ):

            session[
                "admin_logged_in"
            ] = True


            return redirect("/admin")


        message = """

<p class="error">

❌ Incorrect username or password.

</p>

"""


    return page(
        "Admin Login",
        f"""

<main
    class="container"
    style="max-width:560px"
>


<section class="hero">


<div
    class="icon-circle"
    style="margin:0 auto"
>

🔐

</div>


<h2>

Administrator Login

</h2>


<p>

Authorized personnel only.

</p>


</section>


{message}


<form method="POST">


<label>

Username *

</label>


<input
    type="text"
    name="username"
    placeholder="Enter admin username"
    required
>


<label>

Password *

</label>


<input
    type="password"
    name="password"
    placeholder="Enter admin password"
    required
>


<button
    type="submit"
    class="btn btn-full"
>

🔐 Login Securely

</button>


</form>


<div class="notice">


<strong>
Demo account:
</strong>


Username:

<code>
admin
</code>


<br>


Password:

<code>
admin123
</code>


<br><br>


Change these credentials
before using the system
in a real school environment.


</div>


<a
    href="/"
    class="btn btn-secondary"
>

← Back to Home

</a>


</main>

"""
    )


# =========================================================
# ADMIN MENU
# =========================================================
@app.route("/admin")
def admin():

    if not is_admin():

        return redirect(
            "/admin-login"
        )


    conn = sqlite3.connect(
        DB_FILE
    )


    c = conn.cursor()


    c.execute(
        "SELECT COUNT(*) FROM reports"
    )


    total = c.fetchone()[0]


    c.execute(
        """

        SELECT COUNT(*)

        FROM reports

        WHERE status='Submitted'

        """
    )


    submitted = c.fetchone()[0]


    c.execute(
        """

        SELECT COUNT(*)

        FROM reports

        WHERE status='In Progress'

        """
    )


    progress = c.fetchone()[0]


    c.execute(
        """

        SELECT COUNT(*)

        FROM reports

        WHERE status='Resolved'

        """
    )


    resolved = c.fetchone()[0]


    conn.close()


    return page(
        "Admin Panel",
        f"""

<main class="container">


<section class="hero">


<div
    class="icon-circle"
    style="margin:0 auto"
>

👨‍💼

</div>


<h2>

Administrator Dashboard

</h2>


<p>

Monitor school concerns and
keep reports moving toward resolution.

</p>


</section>


<div class="stats">


<div class="stat">

<span>
Total Reports
</span>

<strong>
{total}
</strong>

</div>


<div class="stat">

<span>
New / Submitted
</span>

<strong>
{submitted}
</strong>

</div>


<div class="stat">

<span>
In Progress
</span>

<strong>
{progress}
</strong>

</div>


<div class="stat">

<span>
Resolved
</span>

<strong>
{resolved}
</strong>

</div>


</div>


<div class="menu-container">


<div class="menu-card">


<div class="icon-circle">
📋
</div>


<h3>

Manage All Reports

</h3>


<p class="muted">

View every submitted report
and update its status.

</p>


<a
    href="/admin-dashboard"
    class="btn"
>

Open Dashboard →

</a>


</div>


<div class="menu-card">


<div class="icon-circle">
🔎
</div>


<h3>

Find a Report

</h3>


<p class="muted">

Search for a specific report
using its Report ID.

</p>


<a
    href="/status"
    class="btn"
>

Track Report →

</a>


</div>


</div>


<a
    href="/logout"
    class="btn btn-danger"
>

🚪 Logout

</a>


</main>

""",
        "👨‍💼 SchoolSafe Admin",
        "Administrator Panel"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================
@app.route("/admin-dashboard")
def admin_dashboard():

    if not is_admin():

        return redirect(
            "/admin-login"
        )


    search = request.args.get(
        "search",
        ""
    ).strip()


    conn = sqlite3.connect(
        DB_FILE
    )


    c = conn.cursor()


    if search:

        like = f"%{search}%"


        c.execute(
            """

            SELECT *

            FROM reports

            WHERE report_id LIKE ?

            OR reporter LIKE ?

            OR issue_type LIKE ?

            OR location LIKE ?

            OR status LIKE ?

            ORDER BY id DESC

            """,

            (
                like,
                like,
                like,
                like,
                like
            )
        )


    else:

        c.execute(
            """

            SELECT *

            FROM reports

            ORDER BY id DESC

            """
        )


    reports = c.fetchall()


    conn.close()


    rows = ""


    if not reports:

        rows = """

<tr>

<td
    colspan="8"
    style="text-align:center"
>

No matching reports found.

</td>

</tr>

"""


    for r in reports:

        rows += f"""

<tr>


<td>

<strong>

{html.escape(r[1])}

</strong>

<br>

<small>

{html.escape(r[8])}
{html.escape(r[9])}

</small>

</td>


<td>

{html.escape(r[2])}

</td>


<td>

{html.escape(r[3])}

</td>


<td>

{html.escape(r[4])}

</td>


<td>

{html.escape(r[5])}

</td>


<td>


<span
    class="badge {urgency_class(r[6])}"
>

{html.escape(r[6])}

</span>


</td>


<td>


<span
    class="status {status_class(r[7])}"
>

{html.escape(r[7])}

</span>


</td>


<td>


<form
    method="POST"
    action="/update/{r[0]}"
    style="margin:0"
>


<select
    name="status"
    required
>


<option
    value="Submitted"
    {"selected" if r[7] == "Submitted" else ""}
>

Submitted

</option>


<option
    value="Under Review"
    {"selected" if r[7] == "Under Review" else ""}
>

Under Review

</option>


<option
    value="In Progress"
    {"selected" if r[7] == "In Progress" else ""}
>

In Progress

</option>


<option
    value="Resolved"
    {"selected" if r[7] == "Resolved" else ""}
>

Resolved

</option>


</select>


<button
    type="submit"
    class="btn"
    style="width:100%"
>

Update

</button>


</form>


</td>


</tr>

"""


    return page(
        "Admin Dashboard",
        f"""

<main class="container wide">


<section class="hero">


<div
    class="icon-circle"
    style="margin:0 auto"
>

📋

</div>


<h2>

All Student Reports

</h2>


<p>

Review, search, and update
submitted school concerns.

</p>


</section>


<form
    method="GET"
    class="searchbar"
>


<input
    type="text"
    name="search"
    value="{html.escape(search)}"
    placeholder="Search by Report ID, student, issue, location, or status..."
>


<button
    class="btn"
    type="submit"
>

🔍 Search

</button>


<a
    href="/admin-dashboard"
    class="btn btn-secondary"
>

Clear

</a>


</form>


<div class="table-wrap">


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
Description
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


{rows}


</table>


</div>


<a
    href="/admin"
    class="btn btn-secondary"
>

← Admin Menu

</a>


</main>

""",
        "📋 SchoolSafe Admin",
        "All Student Reports"
    )


# =========================================================
# UPDATE REPORT STATUS
# =========================================================
@app.route(
    "/update/<int:id>",
    methods=["POST"]
)
def update(id):

    if not is_admin():

        return redirect(
            "/admin-login"
        )


    status_value = request.form.get(
        "status",
        ""
    )


    allowed_statuses = [

        "Submitted",

        "Under Review",

        "In Progress",

        "Resolved"

    ]


    if status_value not in allowed_statuses:

        return redirect(
            "/admin-dashboard"
        )


    conn = sqlite3.connect(
        DB_FILE
    )


    c = conn.cursor()


    c.execute(
        """

        UPDATE reports

        SET status = ?

        WHERE id = ?

        """,

        (
            status_value,
            id
        )
    )


    conn.commit()


    conn.close()


    return redirect(
        "/admin-dashboard"
    )


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":

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