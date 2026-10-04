from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string,
    send_from_directory
)

import sqlite3
import os
import secrets
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename


# ==========================================================
# SLSU JGE SCHOOL ID APPLICATION AND TRACKING SYSTEM
# ==========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "slsu-jge-school-id-secret-key"
)


# ==========================================================
# SETTINGS
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_FILE = os.path.join(
    BASE_DIR,
    "slsu_jge_id.db"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum upload = 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png"
}


# ==========================================================
# ADMIN ACCOUNT
# ==========================================================

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


# ==========================================================
# OFFICIAL SLSU LOGO
# ==========================================================

SLSU_LOGO = (
    "https://www.slsu.edu.ph/"
    "wp-content/uploads/2023/05/"
    "cropped-SLSU_Logo-1.png"
)


# ==========================================================
# DATABASE
# ==========================================================

def get_db():

    connection = sqlite3.connect(
        DB_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_db():

    connection = get_db()

    cursor = connection.cursor()

    # ------------------------------------------------------
    # APPLICATIONS
    # ------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            application_id TEXT UNIQUE NOT NULL,

            student_id TEXT NOT NULL,

            first_name TEXT NOT NULL,

            middle_name TEXT,

            last_name TEXT NOT NULL,

            suffix TEXT,

            course TEXT NOT NULL,

            year_level TEXT NOT NULL,

            section TEXT,

            birth_date TEXT,

            sex TEXT,

            email TEXT,

            phone TEXT,

            address TEXT,

            emergency_contact TEXT,

            emergency_phone TEXT,

            photo TEXT,

            status TEXT DEFAULT 'Pending',

            remarks TEXT,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL
        )
    """)

    # ------------------------------------------------------
    # APPLICATION HISTORY
    # ------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            application_id TEXT NOT NULL,

            status TEXT NOT NULL,

            remarks TEXT,

            created_at TEXT NOT NULL
        )
    """)

    connection.commit()

    connection.close()


# ==========================================================
# HELPERS
# ==========================================================

def generate_application_id():

    while True:

        code = secrets.token_hex(
            3
        ).upper()

        application_id = (
            "SLSU-JGE-" + code
        )

        connection = get_db()

        existing = connection.execute(
            """
            SELECT id
            FROM applications
            WHERE application_id = ?
            """,
            (application_id,)
        ).fetchone()

        connection.close()

        if not existing:

            return application_id


def allowed_file(filename):

    if "." not in filename:

        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


def add_history(
    application_id,
    status,
    remarks=""
):

    connection = get_db()

    connection.execute(
        """
        INSERT INTO application_history
        (
            application_id,
            status,
            remarks,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            application_id,
            status,
            remarks,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    connection.commit()

    connection.close()


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get(
            "admin_logged_in"
        ):

            return redirect(
                url_for(
                    "admin_login"
                )
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


# ==========================================================
# STATUS CLASS
# ==========================================================

def status_class(status):

    classes = {
        "Pending": "pending",
        "Processing": "processing",
        "Approved": "approved",
        "Ready for Pickup": "ready",
        "Released": "released",
        "Rejected": "rejected"
    }

    return classes.get(
        status,
        "pending"
    )


# ==========================================================
# DESIGN
# ==========================================================

STYLE = """

<style>

* {
    box-sizing: border-box;
}

:root {

    --slsu-blue: #0756a6;
    --slsu-dark: #063b72;
    --slsu-green: #087443;
    --slsu-red: #c62828;
    --slsu-gold: #f2b705;

    --background: #f4f7fb;

    --text: #172033;

    --muted: #667085;
}


body {

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        var(--background);

    color:
        var(--text);
}


/* ======================================================
   TOP BAR
====================================================== */

.navbar {

    background:
        linear-gradient(
            135deg,
            var(--slsu-dark),
            var(--slsu-blue)
        );

    color: white;

    padding:
        12px 6%;

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    flex-wrap: wrap;

    gap: 15px;

    box-shadow:
        0 3px 15px
        rgba(0,0,0,.15);

}


.brand {

    display: flex;

    align-items: center;

    gap: 12px;

}


.brand img {

    width: 58px;

    height: 58px;

    object-fit: contain;

    background: white;

    border-radius: 50%;

    padding: 3px;

}


.brand-title {

    font-size: 18px;

    font-weight: bold;

}


.brand-subtitle {

    font-size: 12px;

    opacity: .9;

}


.navbar a {

    color: white;

    text-decoration: none;

    margin-left: 15px;

    font-size: 14px;

}


/* ======================================================
   CONTAINER
====================================================== */

.container {

    width: 92%;

    max-width: 1150px;

    margin:
        30px auto;

}


/* ======================================================
   HERO
====================================================== */

.hero {

    position: relative;

    overflow: hidden;

    background:
        linear-gradient(
            135deg,
            var(--slsu-dark),
            var(--slsu-blue)
        );

    color: white;

    padding:
        60px 30px;

    border-radius: 24px;

    text-align: center;

    box-shadow:
        0 8px 25px
        rgba(0,0,0,.15);

}


.hero:after {

    content: "";

    position: absolute;

    width: 280px;

    height: 280px;

    border-radius: 50%;

    border:
        35px solid
        rgba(255,255,255,.07);

    right: -90px;

    top: -90px;

}


.hero-logo {

    width: 110px;

    height: 110px;

    object-fit: contain;

    background: white;

    border-radius: 50%;

    padding: 5px;

    position: relative;

    z-index: 2;

}


.hero h1 {

    font-size: 40px;

    margin:
        15px 0 8px;

}


.hero p {

    font-size: 17px;

    opacity: .95;

}


/* ======================================================
   CARDS
====================================================== */

.card {

    background: white;

    padding: 25px;

    border-radius: 17px;

    margin-bottom: 20px;

    box-shadow:
        0 4px 18px
        rgba(0,0,0,.07);

}


.card h2 {

    margin-top: 0;

}


/* ======================================================
   GRID
====================================================== */

.grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap: 18px;

}


.stat {

    background: white;

    padding: 24px;

    border-radius: 16px;

    text-align: center;

    box-shadow:
        0 4px 15px
        rgba(0,0,0,.07);

    border-top:
        4px solid
        var(--slsu-blue);

}


.stat h2 {

    font-size: 34px;

    color:
        var(--slsu-blue);

    margin: 5px;

}


/* ======================================================
   BUTTON
====================================================== */

.btn {

    display: inline-block;

    padding:
        12px 18px;

    background:
        var(--slsu-blue);

    color: white;

    border: none;

    border-radius: 9px;

    text-decoration: none;

    cursor: pointer;

    font-weight: bold;

}


.btn:hover {

    opacity: .9;

}


.btn-green {

    background:
        var(--slsu-green);

}


.btn-red {

    background:
        var(--slsu-red);

}


.btn-gold {

    background:
        var(--slsu-gold);

    color: #222;

}


/* ======================================================
   FORM
====================================================== */

input,
select,
textarea {

    width: 100%;

    padding: 12px;

    margin-top: 7px;

    margin-bottom: 15px;

    border:
        1px solid #ccd4df;

    border-radius: 8px;

    font-size: 15px;

}


textarea {

    min-height: 120px;

    resize: vertical;

}


label {

    font-weight: bold;

}


.form-grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(230px, 1fr)
        );

    gap: 15px;

}


/* ======================================================
   STATUS
====================================================== */

.status {

    display: inline-block;

    padding:
        7px 12px;

    border-radius: 20px;

    font-size: 13px;

    font-weight: bold;

}


.pending {

    background: #fff0b3;

    color: #775c00;

}


.processing {

    background: #cce5ff;

    color: #0756a6;

}


.approved {

    background: #d4edda;

    color: #155724;

}


.ready {

    background: #d1ecf1;

    color: #0c5460;

}


.released {

    background: #198754;

    color: white;

}


.rejected {

    background: #f8d7da;

    color: #842029;

}


/* ======================================================
   APPLICATION ID
====================================================== */

.application-id-box {

    text-align: center;

    padding: 25px;

    border-radius: 15px;

    background:
        linear-gradient(
            135deg,
            #eef7ff,
            #ffffff
        );

    border:
        2px dashed
        var(--slsu-blue);

}


.application-id {

    font-size: 30px;

    font-weight: bold;

    color:
        var(--slsu-blue);

    letter-spacing: 2px;

}


/* ======================================================
   ALERT
====================================================== */

.alert {

    padding: 14px;

    border-radius: 9px;

    background: #d1ecf1;

    color: #0c5460;

    margin-bottom: 15px;

}


.success {

    background: #d4edda;

    color: #155724;

}


.danger {

    background: #f8d7da;

    color: #842029;

}


/* ======================================================
   TABLE
====================================================== */

.table-wrapper {

    overflow-x: auto;

}


table {

    width: 100%;

    border-collapse:
        collapse;

}


th,
td {

    padding: 12px;

    border-bottom:
        1px solid #ddd;

    text-align: left;

}


th {

    background:
        var(--slsu-blue);

    color: white;

}


/* ======================================================
   TIMELINE
====================================================== */

.timeline {

    border-left:
        3px solid
        var(--slsu-blue);

    padding-left: 20px;

}


.timeline-item {

    margin-bottom: 20px;

}


/* ======================================================
   PHOTO
====================================================== */

.profile-photo {

    width: 180px;

    height: 180px;

    object-fit: cover;

    border-radius: 12px;

    border:
        4px solid
        var(--slsu-blue);

}


/* ======================================================
   FOOTER
====================================================== */

footer {

    text-align: center;

    padding: 35px;

    color:
        var(--muted);

}


/* ======================================================
   PRINT
====================================================== */

@media print {

    .navbar,
    .no-print,
    footer {

        display: none !important;

    }

    body {

        background: white;

    }

    .container {

        width: 100%;

        margin: 0;

    }

    .card {

        box-shadow: none;

        border:
            1px solid #ddd;

    }

}


/* ======================================================
   MOBILE
====================================================== */

@media(max-width:700px) {

    .hero h1 {

        font-size: 30px;

    }

    .brand-title {

        font-size: 15px;

    }

    .brand img {

        width: 45px;

        height: 45px;

    }

    .navbar {

        justify-content: center;

        text-align: center;

    }

}

</style>

"""


# ==========================================================
# HEADER HTML
# ==========================================================

HEADER = """

<div class="navbar">

    <div class="brand">

        <img
            src="{{ logo }}"
            alt="SLSU Logo"
        >

        <div>

            <div class="brand-title">
                SOUTHERN LUZON STATE UNIVERSITY
            </div>

            <div class="brand-subtitle">
                Judge Guillermo Eleazar Campus
                • Tagkawayan, Quezon
            </div>

        </div>

    </div>


    <div>

        <a href="{{ url_for('home') }}">
            Home
        </a>

        <a href="{{ url_for('student_portal') }}">
            Student
        </a>

        <a href="{{ url_for('admin_login') }}">
            Admin
        </a>

    </div>

</div>

"""


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():

    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    SLSU JGE School ID System
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="hero">


<img
    class="hero-logo"
    src="{{ logo }}"
    alt="SLSU Logo"
>


<h1>
    School ID Application
</h1>


<p>
    Southern Luzon State University
    <br>
    Judge Guillermo Eleazar Campus
</p>


<br>


<a
    class="btn btn-gold"
    href="{{ url_for(
        'student_portal'
    ) }}"
>
    Start Application
</a>


</div>


<br>


<div class="grid">


<div class="card">

<h2>
    📝 Apply Online
</h2>

<p>
    Submit your student information
    and ID photo online.
</p>

</div>


<div class="card">

<h2>
    🔎 Track Your ID
</h2>

<p>
    Check your application status
    using your Application ID.
</p>

</div>


<div class="card">

<h2>
    📋 Application History
</h2>

<p>
    See updates made by the
    authorized administrator.
</p>

</div>


<div class="card">

<h2>
    🪪 Faster ID Processing
</h2>

<p>
    Reduce manual paperwork by
    submitting your information online.
</p>

</div>


</div>


<div class="card">

<h2>
    About the System
</h2>

<p>
    The SLSU JGE School ID Application
    and Tracking System provides students
    with a convenient way to submit and
    monitor their School ID applications.
</p>

<p>
    Students receive a unique Application ID
    after submission which can be used to
    track the application.
</p>

</div>


</div>


<footer>

    SLSU JGE School ID Application
    and Tracking System © 2026

</footer>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO
    )


# ==========================================================
# STUDENT PORTAL
# ==========================================================

@app.route("/student")
def student_portal():

    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Student Portal
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="hero">

<img
    class="hero-logo"
    src="{{ logo }}"
>


<h1>
    Student Portal
</h1>

<p>
    Manage your School ID application.
</p>

</div>


<br>


<div class="grid">


<div class="card">

<h2>
    📝 Apply for School ID
</h2>

<p>
    Complete the application form
    and upload your ID photo.
</p>

<a
    class="btn"
    href="{{ url_for('apply_id') }}"
>
    Apply Now
</a>

</div>


<div class="card">

<h2>
    🔎 Track Application
</h2>

<p>
    Check the current status of
    your application.
</p>

<a
    class="btn"
    href="{{ url_for(
        'track_application'
    ) }}"
>
    Track Now
</a>

</div>


</div>


</div>

</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO
    )


# ==========================================================
# APPLY
# ==========================================================

@app.route(
    "/student/apply",
    methods=["GET", "POST"]
)
def apply_id():

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        middle_name = request.form.get(
            "middle_name",
            ""
        ).strip()

        last_name = request.form.get(
            "last_name",
            ""
        ).strip()

        suffix = request.form.get(
            "suffix",
            ""
        ).strip()

        course = request.form.get(
            "course",
            ""
        ).strip()

        year_level = request.form.get(
            "year_level",
            ""
        ).strip()

        section = request.form.get(
            "section",
            ""
        ).strip()

        birth_date = request.form.get(
            "birth_date",
            ""
        ).strip()

        sex = request.form.get(
            "sex",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        emergency_contact = request.form.get(
            "emergency_contact",
            ""
        ).strip()

        emergency_phone = request.form.get(
            "emergency_phone",
            ""
        ).strip()


        # Required fields

        if not (
            student_id
            and first_name
            and last_name
            and course
            and year_level
        ):

            return """
            <script>
                alert(
                    "Please complete all required fields."
                );
                history.back();
            </script>
            """


        # Check existing application

        connection = get_db()

        existing = connection.execute(
            """
            SELECT *
            FROM applications

            WHERE student_id = ?

            AND status NOT IN (
                'Rejected',
                'Released'
            )
            """,
            (student_id,)
        ).fetchone()

        connection.close()


        if existing:

            return render_template_string(
                """
<!DOCTYPE html>

<html>

<head>

<title>
    Existing Application
</title>

{{ style|safe }}

</head>

<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    ⚠️ Existing Application
</h1>


<p>
    An active School ID application
    already exists for this Student ID.
</p>


<div class="application-id-box">

<p>
    Application ID
</p>

<div class="application-id">

{{ application_id }}

</div>

</div>


<br>


<a
    class="btn"
    href="{{ url_for(
        'track_application'
    ) }}"
>
    Track Application
</a>


</div>


</div>


</body>

</html>
                """,
                style=STYLE,
                header=HEADER,
                logo=SLSU_LOGO,
                application_id=existing[
                    "application_id"
                ]
            )


        # Generate ID

        application_id = (
            generate_application_id()
        )


        # Upload photo

        photo_name = None

        photo = request.files.get(
            "photo"
        )


        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                return """
                <script>
                    alert(
                        "Only JPG, JPEG and PNG files are allowed."
                    );
                    history.back();
                </script>
                """


            filename = secure_filename(
                photo.filename
            )


            photo_name = (
                application_id
                + "_"
                + filename
            )


            photo.save(
                os.path.join(
                    app.config[
                        "UPLOAD_FOLDER"
                    ],
                    photo_name
                )
            )


        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        # Save

        connection = get_db()


        connection.execute(
            """
            INSERT INTO applications
            (
                application_id,
                student_id,
                first_name,
                middle_name,
                last_name,
                suffix,
                course,
                year_level,
                section,
                birth_date,
                sex,
                email,
                phone,
                address,
                emergency_contact,
                emergency_phone,
                photo,
                status,
                remarks,
                created_at,
                updated_at
            )

            VALUES
            (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                application_id,
                student_id,
                first_name,
                middle_name,
                last_name,
                suffix,
                course,
                year_level,
                section,
                birth_date,
                sex,
                email,
                phone,
                address,
                emergency_contact,
                emergency_phone,
                photo_name,
                "Pending",
                "",
                now,
                now
            )
        )


        connection.commit()

        connection.close()


        add_history(
            application_id,
            "Pending",
            "Application successfully submitted."
        )


        # IMPORTANT:
        # Redirect to confirmation output

        return redirect(
            url_for(
                "application_success",
                application_id=application_id
            )
        )


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Apply for School ID
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    🪪 School ID Application
</h1>


<div class="alert">

<b>
    Important:
</b>

Please make sure all information is
correct before submitting.

</div>


<form
    method="POST"
    enctype="multipart/form-data"
>


<div class="form-grid">


<div>

<label>
    Student ID *
</label>

<input
    type="text"
    name="student_id"
    placeholder="Example: 2026-00123"
    required
>

</div>


<div>

<label>
    First Name *
</label>

<input
    type="text"
    name="first_name"
    required
>

</div>


<div>

<label>
    Middle Name
</label>

<input
    type="text"
    name="middle_name"
>

</div>


<div>

<label>
    Last Name *
</label>

<input
    type="text"
    name="last_name"
    required
>

</div>


<div>

<label>
    Suffix
</label>

<input
    type="text"
    name="suffix"
    placeholder="Jr., III, etc."
>

</div>


<div>

<label>
    Course *
</label>

<input
    type="text"
    name="course"
    placeholder="Example: BSIT"
    required
>

</div>


<div>

<label>
    Year Level *
</label>

<select
    name="year_level"
    required
>

<option value="">
    Select Year
</option>

<option>1st Year</option>
<option>2nd Year</option>
<option>3rd Year</option>
<option>4th Year</option>
<option>5th Year</option>

</select>

</div>


<div>

<label>
    Section
</label>

<input
    type="text"
    name="section"
>

</div>


<div>

<label>
    Birth Date
</label>

<input
    type="date"
    name="birth_date"
>

</div>


<div>

<label>
    Sex
</label>

<select name="sex">

<option value="">
    Select
</option>

<option>Male</option>
<option>Female</option>
<option>Prefer not to say</option>

</select>

</div>


<div>

<label>
    Email
</label>

<input
    type="email"
    name="email"
>

</div>


<div>

<label>
    Phone
</label>

<input
    type="text"
    name="phone"
>

</div>


</div>


<label>
    Complete Address
</label>

<textarea
    name="address"
></textarea>


<div class="form-grid">


<div>

<label>
    Emergency Contact
</label>

<input
    type="text"
    name="emergency_contact"
>

</div>


<div>

<label>
    Emergency Contact Number
</label>

<input
    type="text"
    name="emergency_phone"
>

</div>


</div>


<label>
    Student ID Photo *
</label>

<input
    type="file"
    name="photo"
    accept=".jpg,.jpeg,.png"
    required
>


<p class="small">
    JPG, JPEG or PNG only.
    Maximum size: 5 MB.
</p>


<button
    class="btn"
    type="submit"
>
    Submit Application
</button>


</form>


</div>


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO
    )


# ==========================================================
# APPLICATION SUCCESS / OUTPUT
# ==========================================================

@app.route(
    "/student/success/<application_id>"
)
def application_success(
    application_id
):

    connection = get_db()

    application = connection.execute(
        """
        SELECT *
        FROM applications
        WHERE application_id = ?
        """,
        (application_id,)
    ).fetchone()

    connection.close()


    if not application:

        return "Application not found.", 404


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Application Submitted
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<div style="text-align:center;">


<img
    src="{{ logo }}"
    style="
        width:90px;
        height:90px;
        object-fit:contain;
    "
>


<h1>
    ✅ Application Submitted!
</h1>


<p>
    Your SLSU JGE School ID application
    was successfully received.
</p>


</div>


<div class="application-id-box">


<p>
    YOUR APPLICATION ID
</p>


<div class="application-id">

{{ application["application_id"] }}

</div>


<p class="small">

Please save this Application ID.
You will use it to track your application.

</p>


</div>


<br>


<div class="card">


<h2>
    Application Summary
</h2>


<p>

<b>
    Student ID:
</b>

{{ application["student_id"] }}

</p>


<p>

<b>
    Student Name:
</b>

{{ application["first_name"] }}
{{ application["middle_name"] or "" }}
{{ application["last_name"] }}

</p>


<p>

<b>
    Course:
</b>

{{ application["course"] }}

</p>


<p>

<b>
    Year Level:
</b>

{{ application["year_level"] }}

</p>


<p>

<b>
    Status:
</b>

<span class="status pending">
    Pending
</span>

</p>


<p>

<b>
    Date Submitted:
</b>

{{ application["created_at"] }}

</p>


</div>


<div class="alert success">

<b>
    Next Step:
</b>

Use your Application ID to track
your School ID application.

</div>


<div
    class="no-print"
    style="text-align:center;"
>


<a
    class="btn"
    href="{{ url_for(
        'track_application'
    ) }}"
>
    🔎 Track Application
</a>


<button
    class="btn btn-green"
    onclick="window.print()"
>
    🖨️ Print Confirmation
</button>


<a
    class="btn btn-gold"
    href="{{ url_for(
        'student_portal'
    ) }}"
>
    Student Portal
</a>


</div>


</div>


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        application=application
    )


# ==========================================================
# TRACK APPLICATION
# ==========================================================

@app.route(
    "/student/track",
    methods=["GET", "POST"]
)
def track_application():

    application = None

    history = []


    if request.method == "POST":

        application_id = request.form.get(
            "application_id",
            ""
        ).strip().upper()


        connection = get_db()


        application = connection.execute(
            """
            SELECT *
            FROM applications
            WHERE application_id = ?
            """,
            (application_id,)
        ).fetchone()


        history = connection.execute(
            """
            SELECT *
            FROM application_history

            WHERE application_id = ?

            ORDER BY id ASC
            """,
            (application_id,)
        ).fetchall()


        connection.close()


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Track Application
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    🔎 Track Your Application
</h1>


<form method="POST">


<label>
    Application ID
</label>


<input
    type="text"
    name="application_id"
    placeholder="SLSU-JGE-XXXXXX"
    required
>


<button
    class="btn"
    type="submit"
>
    Track Application
</button>


</form>


</div>


{% if request.method == "POST"
      and not application %}


<div class="alert danger">

❌ Application not found.

Please check your Application ID.

</div>


{% endif %}


{% if application %}


<div class="card">


<h1>

{{ application["application_id"] }}

</h1>


<p>

<b>
    Student:
</b>

{{ application["first_name"] }}
{{ application["middle_name"] or "" }}
{{ application["last_name"] }}

</p>


<p>

<b>
    Student ID:
</b>

{{ application["student_id"] }}

</p>


<p>

<b>
    Course:
</b>

{{ application["course"] }}

</p>


<p>

<b>
    Status:
</b>


<span class="status
{{ status_class(application['status']) }}"
>

{{ application["status"] }}

</span>


</p>


{% if application["remarks"] %}

<div class="alert">

<b>
    Admin Remarks:
</b>

<br>

{{ application["remarks"] }}

</div>

{% endif %}


</div>


<div class="card">


<h2>
    📜 Application Timeline
</h2>


<div class="timeline">


{% for item in history %}


<div class="timeline-item">


<strong>

{{ item["status"] }}

</strong>


<p>

{{ item["remarks"]
   or "Application status updated." }}

</p>


<span class="small">

{{ item["created_at"] }}

</span>


</div>


{% endfor %}


</div>


</div>


{% endif %}


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        application=application,
        history=history,
        status_class=status_class
    )


# ==========================================================
# ADMIN LOGIN
# ==========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    error = ""


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )


        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session[
                "admin_logged_in"
            ] = True

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        error = (
            "Invalid username or password."
        )


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Admin Login
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div
    class="card"
    style="
        max-width:450px;
        margin:70px auto;
    "
>


<div style="text-align:center;">


<img
    src="{{ logo }}"
    style="
        width:90px;
        height:90px;
    "
>


<h1>
    🔐 Admin Login
</h1>


<p>
    SLSU JGE ID Administration
</p>


</div>


{% if error %}

<div class="alert danger">

{{ error }}

</div>

{% endif %}


<form method="POST">


<label>
    Username
</label>

<input
    type="text"
    name="username"
    required
>


<label>
    Password
</label>

<input
    type="password"
    name="password"
    required
>


<button
    class="btn"
    type="submit"
>
    Login
</button>


</form>


</div>


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        error=error
    )


# ==========================================================
# ADMIN LOGOUT
# ==========================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = get_db()


    total = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        """
    ).fetchone()["count"]


    pending = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Pending'
        """
    ).fetchone()["count"]


    processing = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Processing'
        """
    ).fetchone()["count"]


    approved = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Approved'
        """
    ).fetchone()["count"]


    ready = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Ready for Pickup'
        """
    ).fetchone()["count"]


    released = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Released'
        """
    ).fetchone()["count"]


    rejected = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM applications
        WHERE status = 'Rejected'
        """
    ).fetchone()["count"]


    recent = connection.execute(
        """
        SELECT *
        FROM applications
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()


    connection.close()


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Admin Dashboard
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    📊 SLSU JGE Admin Dashboard
</h1>


<p>
    School ID Application Management
</p>


</div>


<div class="grid">


<div class="stat">

<h2>
    {{ total }}
</h2>

<p>
    Total Applications
</p>

</div>


<div class="stat">

<h2>
    {{ pending }}
</h2>

<p>
    Pending
</p>

</div>


<div class="stat">

<h2>
    {{ processing }}
</h2>

<p>
    Processing
</p>

</div>


<div class="stat">

<h2>
    {{ approved }}
</h2>

<p>
    Approved
</p>

</div>


<div class="stat">

<h2>
    {{ ready }}
</h2>

<p>
    Ready for Pickup
</p>

</div>


<div class="stat">

<h2>
    {{ released }}
</h2>

<p>
    Released
</p>

</div>


<div class="stat">

<h2>
    {{ rejected }}
</h2>

<p>
    Rejected
</p>

</div>


</div>


<br>


<div class="card">


<h2>
    Quick Actions
</h2>


<a
    class="btn"
    href="{{ url_for(
        'admin_applications'
    ) }}"
>
    📋 Manage Applications
</a>


<a
    class="btn btn-green"
    href="{{ url_for(
        'admin_logout'
    ) }}"
>
    Logout
</a>


</div>


<div class="card">


<h2>
    🆕 Recent Applications
</h2>


<div class="table-wrapper">


<table>


<tr>

<th>
    Application ID
</th>

<th>
    Student
</th>

<th>
    Student ID
</th>

<th>
    Course
</th>

<th>
    Status
</th>

<th>
    Action
</th>

</tr>


{% for application in recent %}


<tr>


<td>
{{ application["application_id"] }}
</td>


<td>
{{ application["first_name"] }}
{{ application["last_name"] }}
</td>


<td>
{{ application["student_id"] }}
</td>


<td>
{{ application["course"] }}
</td>


<td>

<span class="status
{{ status_class(application['status']) }}"
>

{{ application["status"] }}

</span>

</td>


<td>

<a
    class="btn"
    href="{{ url_for(
        'admin_application_detail',
        application_id=application[
            'application_id'
        ]
    ) }}"
>
    View
</a>

</td>


</tr>


{% endfor %}


</table>


</div>


</div>


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        total=total,
        pending=pending,
        processing=processing,
        approved=approved,
        ready=ready,
        released=released,
        rejected=rejected,
        recent=recent,
        status_class=status_class
    )


# ==========================================================
# ADMIN APPLICATIONS
# ==========================================================

@app.route(
    "/admin/applications"
)
@admin_required
def admin_applications():

    search = request.args.get(
        "search",
        ""
    ).strip()


    status = request.args.get(
        "status",
        ""
    ).strip()


    connection = get_db()


    query = """
        SELECT *
        FROM applications
        WHERE 1=1
    """


    parameters = []


    if search:

        query += """
            AND (
                application_id LIKE ?
                OR student_id LIKE ?
                OR first_name LIKE ?
                OR last_name LIKE ?
                OR course LIKE ?
            )
        """

        search_value = (
            f"%{search}%"
        )

        parameters.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])


    if status:

        query += """
            AND status = ?
        """

        parameters.append(
            status
        )


    query += """
        ORDER BY id DESC
    """


    applications = connection.execute(
        query,
        parameters
    ).fetchall()


    connection.close()


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Manage Applications
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    📋 Student ID Applications
</h1>


<form method="GET">


<label>
    Search
</label>


<input
    type="text"
    name="search"
    value="{{ search }}"
    placeholder="
        Application ID, Student ID,
        Name or Course
    "
>


<label>
    Filter by Status
</label>


<select name="status">


<option value="">
    All Applications
</option>


<option
    value="Pending"
    {% if status == "Pending" %}
    selected
    {% endif %}
>
    Pending
</option>


<option
    value="Processing"
    {% if status == "Processing" %}
    selected
    {% endif %}
>
    Processing
</option>


<option
    value="Approved"
    {% if status == "Approved" %}
    selected
    {% endif %}
>
    Approved
</option>


<option
    value="Ready for Pickup"
    {% if status == "Ready for Pickup" %}
    selected
    {% endif %}
>
    Ready for Pickup
</option>


<option
    value="Released"
    {% if status == "Released" %}
    selected
    {% endif %}
>
    Released
</option>


<option
    value="Rejected"
    {% if status == "Rejected" %}
    selected
    {% endif %}
>
    Rejected
</option>


</select>


<button
    class="btn"
    type="submit"
>
    🔎 Search
</button>


</form>


</div>


{% for application in applications %}


<div class="card">


<div
    style="
        display:flex;
        justify-content:space-between;
        gap:20px;
        flex-wrap:wrap;
    "
>


<div>


<h2>
{{ application["application_id"] }}
</h2>


<p>

<b>
Student:
</b>

{{ application["first_name"] }}
{{ application["last_name"] }}

</p>


<p>

<b>
Student ID:
</b>

{{ application["student_id"] }}

</p>


<p>

<b>
Course:
</b>

{{ application["course"] }}

</p>


</div>


<div>


<span class="status
{{ status_class(application['status']) }}"
>

{{ application["status"] }}

</span>


<br><br>


<a
    class="btn"
    href="{{ url_for(
        'admin_application_detail',
        application_id=application[
            'application_id'
        ]
    ) }}"
>
    Manage
</a>


</div>


</div>


</div>


{% else %}


<div class="card">

<h2>
    No applications found.
</h2>

</div>


{% endfor %}


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        applications=applications,
        search=search,
        status=status,
        status_class=status_class
    )


# ==========================================================
# ADMIN APPLICATION DETAILS
# ==========================================================

@app.route(
    "/admin/application/<application_id>",
    methods=["GET", "POST"]
)
@admin_required
def admin_application_detail(
    application_id
):

    connection = get_db()


    application = connection.execute(
        """
        SELECT *
        FROM applications

        WHERE application_id = ?
        """,
        (application_id,)
    ).fetchone()


    if not application:

        connection.close()

        return "Application not found.", 404


    if request.method == "POST":

        new_status = request.form.get(
            "status",
            "Pending"
        )


        remarks = request.form.get(
            "remarks",
            ""
        ).strip()


        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        connection.execute(
            """
            UPDATE applications

            SET
                status = ?,
                remarks = ?,
                updated_at = ?

            WHERE application_id = ?
            """,
            (
                new_status,
                remarks,
                now,
                application_id
            )
        )


        connection.commit()

        connection.close()


        add_history(
            application_id,
            new_status,
            remarks
        )


        return redirect(
            url_for(
                "admin_application_detail",
                application_id=application_id
            )
        )


    history = connection.execute(
        """
        SELECT *
        FROM application_history

        WHERE application_id = ?

        ORDER BY id ASC
        """,
        (application_id,)
    ).fetchall()


    connection.close()


    return render_template_string(
        """
<!DOCTYPE html>

<html>

<head>

<title>
    Application Details
</title>

{{ style|safe }}

</head>


<body>

{{ header|safe }}


<div class="container">


<div class="card">


<h1>
    🪪 Application Details
</h1>


<div class="application-id-box">

<div class="application-id">

{{ application["application_id"] }}

</div>

</div>


<br>


<div
    style="
        display:flex;
        gap:30px;
        flex-wrap:wrap;
    "
>


<div>


{% if application["photo"] %}


<img
    class="profile-photo"
    src="{{ url_for(
        'uploaded_file',
        filename=application['photo']
    ) }}"
>


{% else %}


<div
    class="profile-photo"
    style="
        display:flex;
        align-items:center;
        justify-content:center;
        background:#eef2f7;
    "
>

No Photo

</div>


{% endif %}


</div>


<div>


<h2>
    Student Information
</h2>


<p>

<b>
Student ID:
</b>

{{ application["student_id"] }}

</p>


<p>

<b>
Name:
</b>

{{ application["first_name"] }}

{{ application["middle_name"] or "" }}

{{ application["last_name"] }}

{{ application["suffix"] or "" }}

</p>


<p>

<b>
Course:
</b>

{{ application["course"] }}

</p>


<p>

<b>
Year Level:
</b>

{{ application["year_level"] }}

</p>


<p>

<b>
Section:
</b>

{{ application["section"] or "N/A" }}

</p>


<p>

<b>
Birth Date:
</b>

{{ application["birth_date"] or "N/A" }}

</p>


<p>

<b>
Sex:
</b>

{{ application["sex"] or "N/A" }}

</p>


</div>


</div>


</div>


<div class="card">


<h2>
    📞 Contact Information
</h2>


<p>

<b>
Email:
</b>

{{ application["email"] or "N/A" }}

</p>


<p>

<b>
Phone:
</b>

{{ application["phone"] or "N/A" }}

</p>


<p>

<b>
Address:
</b>

{{ application["address"] or "N/A" }}

</p>


<p>

<b>
Emergency Contact:
</b>

{{ application["emergency_contact"] or "N/A" }}

</p>


<p>

<b>
Emergency Phone:
</b>

{{ application["emergency_phone"] or "N/A" }}

</p>


</div>


<div class="card">


<h2>
    ⚙️ Application Processing
</h2>


<form method="POST">


<label>
    Status
</label>


<select name="status">


<option
{% if application["status"] == "Pending" %}
selected
{% endif %}
>
Pending
</option>


<option
{% if application["status"] == "Processing" %}
selected
{% endif %}
>
Processing
</option>


<option
{% if application["status"] == "Approved" %}
selected
{% endif %}
>
Approved
</option>


<option
{% if application["status"] == "Ready for Pickup" %}
selected
{% endif %}
>
Ready for Pickup
</option>


<option
{% if application["status"] == "Released" %}
selected
{% endif %}
>
Released
</option>


<option
{% if application["status"] == "Rejected" %}
selected
{% endif %}
>
Rejected
</option>


</select>


<label>
    Admin Remarks
</label>


<textarea
    name="remarks"
    placeholder="
        Example:
        Your School ID is ready for pickup.
    "
>{{ application["remarks"] or "" }}</textarea>


<button
    class="btn btn-green"
    type="submit"
>
    💾 Save Update
</button>


</form>


</div>


<div class="card">


<h2>
    📜 Application History
</h2>


<div class="timeline">


{% for item in history %}


<div class="timeline-item">


<strong>

{{ item["status"] }}

</strong>


<p>

{{ item["remarks"]
   or "Application status updated." }}

</p>


<span class="small">

{{ item["created_at"] }}

</span>


</div>


{% endfor %}


</div>


</div>


</div>


</body>

</html>
        """,
        style=STYLE,
        header=HEADER,
        logo=SLSU_LOGO,
        application=application,
        history=history
    )


# ==========================================================
# UPLOADED FILES
# ==========================================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ==========================================================
# ERROR HANDLERS
# ==========================================================

@app.errorhandler(413)
def file_too_large(error):

    return """
    <h2>
        File Too Large
    </h2>

    <p>
        Please upload a photo smaller than 5 MB.
    </p>

    <a href="/student/apply">
        Back to Application
    </a>
    """, 413


@app.errorhandler(404)
def page_not_found(error):

    return """
    <h2>
        Page Not Found
    </h2>

    <p>
        The page you requested does not exist.
    </p>

    <a href="/">
        Back to Home
    </a>
    """, 404


# ==========================================================
# INITIALIZE DATABASE
# ==========================================================

init_db()


# ==========================================================
# RUN
# ==========================================================

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
        debug=False
    )