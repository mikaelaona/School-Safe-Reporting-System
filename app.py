From flask import (
    Flask,
    Request,
    Redirect,
    url_for,
    session,
    render_template_string,
    send_from_directory
)

Import sqlite3
Import os
Import secrets
From datetime import datetime
From functools import wraps
From werkzeug.utils import secure_filename


# ==========================================================
# SCHOOL ID APPLICATION AND TRACKING SYSTEM
# ==========================================================

App = Flask(__name__)

# ----------------------------------------------------------
# SECRET KEY
# ----------------------------------------------------------

App.secret_key = os.environ.get(
    “SECRET_KEY”,
    “school-id-system-secret-key”
)


# ----------------------------------------------------------
# DATABASE AND UPLOAD SETTINGS
# ----------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(
    BASE_DIR,
    “school_id.db”
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    “uploads”
)

Os.makedirs(
    UPLOAD_FOLDER,
    Exist_ok=True
)

App.config[“UPLOAD_FOLDER”] = UPLOAD_FOLDER

# Maximum upload size = 5 MB
App.config[“MAX_CONTENT_LENGTH”] = 5 * 1024 * 1024


ALLOWED_EXTENSIONS = {
    “jpg”,
    “jpeg”,
    “png”
}


# ----------------------------------------------------------
# ADMIN LOGIN
# ----------------------------------------------------------

ADMIN_USERNAME = os.environ.get(
    “ADMIN_USERNAME”,
    “admin”
)

ADMIN_PASSWORD = os.environ.get(
    “ADMIN_PASSWORD”,
    “admin123”
)


# ==========================================================
# DATABASE
# ==========================================================

Def get_db():

    Connection = sqlite3.connect(DB_FILE)

    Connection.row_factory = sqlite3.Row

    Return connection


Def init_db():

    Connection = get_db()

    Cursor = connection.cursor()

    # ------------------------------------------------------
    # ID APPLICATIONS TABLE
    # ------------------------------------------------------

    Cursor.execute(“””
        CREATE TABLE IF NOT EXISTS applications (

            Id INTEGER PRIMARY KEY AUTOINCREMENT,

            Application_id TEXT UNIQUE NOT NULL,

            Student_id TEXT NOT NULL,

            First_name TEXT NOT NULL,

            Middle_name TEXT,

            Last_name TEXT NOT NULL,

            Suffix TEXT,

            Course TEXT NOT NULL,

            Year_level TEXT NOT NULL,

            Section TEXT,

            Birth_date TEXT,

            Sex TEXT,

            Email TEXT,

            Phone TEXT,

            Address TEXT,

            Emergency_contact TEXT,

            Emergency_phone TEXT,

            Photo TEXT,

            Status TEXT DEFAULT ‘Pending’,

            Remarks TEXT,

            Created_at TEXT NOT NULL,

            Updated_at TEXT NOT NULL
        )
    “””)

    # ------------------------------------------------------
    # APPLICATION HISTORY
    # ------------------------------------------------------

    Cursor.execute(“””
        CREATE TABLE IF NOT EXISTS application_history (

            Id INTEGER PRIMARY KEY AUTOINCREMENT,

            Application_id TEXT NOT NULL,

            Status TEXT NOT NULL,

            Remarks TEXT,

            Created_at TEXT NOT NULL
        )
    “””)

    Connection.commit()

    Connection.close()


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

Def generate_application_id():

    While True:

        Code = secrets.token_hex(3).upper()

        Application_id = “SID-“ + code

        Connection = get_db()

        Existing = connection.execute(
            “””
            SELECT id
            FROM applications
            WHERE application_id = ?
            “””,
            (application_id,)
        ).fetchone()

        Connection.close()

        If not existing:

            Return application_id


Def allowed_file(filename):

    If “.” Not in filename:
        Return False

    Extension = filename.rsplit(
        “.”,
        1
    )[1].lower()

    Return extension in ALLOWED_EXTENSIONS


Def add_history(
    Application_id,
    Status,
    Remarks=””
):

    Connection = get_db()

    Connection.execute(
        “””
        INSERT INTO application_history
        (
            Application_id,
            Status,
            Remarks,
            Created_at
        )
        VALUES (?, ?, ?, ?)
        “””,
        (
            Application_id,
            Status,
            Remarks,
            Datetime.now().strftime(
                “%Y-%m-%d %H:%M:%S”
            )
        )
    )

    Connection.commit()

    Connection.close()


Def admin_required(function):

    @wraps(function)
    Def wrapper(*args, **kwargs):

        If not session.get(
            “admin_logged_in”
        ):

            Return redirect(
                url_for(“admin_login”)
            )

        Return function(
            *args,
            **kwargs
        )

    Return wrapper


# ==========================================================
# DESIGN / CSS
# ==========================================================

STYLE = “””

<style>

{
    Box-sizing: border-box;
}

Body {

    Margin: 0;

    Font-family:
        Arial,
        Helvetica,
        Sans-serif;

    Background: #f4f7fb;

    Color: #172033;
}


.navbar {

    Background:
        Linear-gradient(
            135deg,
            #0756a6,
            #008bd2
        );

    Color: white;

    Padding: 16px 6%;

    Display: flex;

    Justify-content: space-between;

    Align-items: center;

    Flex-wrap: wrap;

    Gap: 10px;

}


.logo {

    Font-size: 23px;

    Font-weight: bold;

}


.navbar a {

    Color: white;

    Text-decoration: none;

    Margin-left: 15px;

}


.container {

    Width: 92%;

    Max-width: 1150px;

    Margin: 30px auto;

}


.hero {

    Background:
        Linear-gradient(
            135deg,
            #0756a6,
            #008bd2
        );

    Color: white;

    Padding: 55px 30px;

    Border-radius: 22px;

    Text-align: center;

}


.hero h1 {

    Font-size: 42px;

    Margin: 0 0 12px;

}


.hero p {

    Font-size: 18px;

}


.card {

    Background: white;

    Padding: 25px;

    Border-radius: 17px;

    Margin-bottom: 20px;

    Box-shadow:
        0 4px 18px
        Rgba(0,0,0,.07);

}


.grid {

    Display: grid;

    Grid-template-columns:
        Repeat(
            Auto-fit,
            Minmax(220px, 1fr)
        );

    Gap: 18px;

}


.stat {

    Background: white;

    Padding: 25px;

    Border-radius: 16px;

    Text-align: center;

    Box-shadow:
        0 4px 15px
        Rgba(0,0,0,.07);

}


.stat h2 {

    Font-size: 34px;

    Color: #0756a6;

    Margin: 5px;

}


.btn {

    Display: inline-block;

    Padding: 12px 18px;

    Background: #0756a6;

    Color: white;

    Border: none;

    Border-radius: 9px;

    Text-decoration: none;

    Cursor: pointer;

    Font-weight: bold;

}


.btn:hover {

    Opacity: .9;

}


.btn-success {

    Background: #198754;

}


.btn-danger {

    Background: #dc3545;

}


.btn-warning {

    Background: #f0ad00;

    Color: black;

}


Input,
Select,
Textarea {

    Width: 100%;

    Padding: 12px;

    Margin-top: 7px;

    Margin-bottom: 15px;

    Border:
        1px solid #ccd4df;

    Border-radius: 8px;

    Font-size: 15px;

}


Textarea {

    Min-height: 120px;

    Resize: vertical;

}


Label {

    Font-weight: bold;

}


.form-grid {

    Display: grid;

    Grid-template-columns:
        Repeat(
            Auto-fit,
            Minmax(230px, 1fr)
        );

    Gap: 15px;

}


.status {

    Display: inline-block;

    Padding: 7px 12px;

    Border-radius: 20px;

    Font-size: 13px;

    Font-weight: bold;

}


.pending {

    Background: #fff0b3;

    Color: #775c00;

}


.processing {

    Background: #cce5ff;

    Color: #0756a6;

}


.approved {

    Background: #d4edda;

    Color: #155724;

}


.ready {

    Background: #d1ecf1;

    Color: #0c5460;

}


.released {

    Background: #198754;

    Color: white;

}


.rejected {

    Background: #f8d7da;

    Color: #842029;

}


.alert {

    Padding: 14px;

    Border-radius: 9px;

    Background: #d1ecf1;

    Color: #0c5460;

    Margin-bottom: 15px;

}


.success {

    Background: #d4edda;

    Color: #155724;

}


.danger {

    Background: #f8d7da;

    Color: #842029;

}


.application-id {

    Font-size: 30px;

    Font-weight: bold;

    Color: #0756a6;

    Letter-spacing: 2px;

}


.profile-photo {

    Width: 180px;

    Height: 180px;

    Object-fit: cover;

    Border-radius: 12px;

    Border:
        4px solid #0756a6;

}


Table {

    Width: 100%;

    Border-collapse: collapse;

}


Th,
Td {

    Padding: 12px;

    Border-bottom:
        1px solid #ddd;

    Text-align: left;

}


Th {

    Background: #0756a6;

    Color: white;

}


.timeline {

    Border-left:
        3px solid #0756a6;

    Padding-left: 20px;

}


.timeline-item {

    Margin-bottom: 20px;

}


.small {

    Color: #667085;

    Font-size: 13px;

}


Footer {

    Text-align: center;

    Padding: 30px;

    Color: #667085;

}


@media(max-width: 700px) {

    .hero h1 {

        Font-size: 30px;

    }

    .navbar {

        Justify-content: center;

        Text-align: center;

    }

    Table {

        Font-size: 12px;

    }

}

</style>

“””


# ==========================================================
# HOME
# ==========================================================

@app.route(“/”)
Def home():

    Return render_template_string(
        “””
<!DOCTYPE html>

<html>

<head>

<title>School ID System</title>

{{ style|safe }}

</head>

<body>


<div class=”navbar”>

    <div class=”logo”>
        🪪 School ID System
    </div>

    <div>

        <a href=”{{ url_for(‘home’) }}”>
            Home
        </a>

        <a href=”{{ url_for(‘student_portal’) }}”>
            Student
        </a>

        <a href=”{{ url_for(‘admin_login’) }}”>
            Admin
        </a>

    </div>

</div>


<div class=”container”>


    <div class=”hero”>

        <h1>
            🪪 School ID Application
        </h1>

        <p>
            Apply for your school ID
            And track your application online.
        </p>

        <br>

        <a
            Class=”btn”
            Href=”{{ url_for(‘student_portal’) }}”
        >
            Get Started
        </a>

    </div>


    <br>


    <div class=”grid”>


        <div class=”card”>

            <h2>
                📝 Apply Online
            </h2>

            <p>
                Submit your student information
                And ID photo online.
            </p>

        </div>


        <div class=”card”>

            <h2>
                🔎 Track Application
            </h2>

            <p>
                Check your ID application status
                Using your Application ID.
            </p>

        </div>


        <div class=”card”>

            <h2>
                🔐 Admin Management
            </h2>

            <p>
                School administrators can review,
                Approve, and manage applications.
            </p>

        </div>


    </div>


</div>


<footer>

    School ID Application and Tracking System © 2026

</footer>


</body>

</html>
        “””,
        Style=STYLE
    )


# ==========================================================
# STUDENT PORTAL
# ==========================================================

@app.route(“/student”)
Def student_portal():

    Return render_template_string(
        “””
<!DOCTYPE html>

<html>

<head>

<title>Student Portal</title>

{{ style|safe }}

</head>

<body>


<div class=”navbar”>

    <div class=”logo”>
        🪪 School ID System
    </div>

    <a href=”{{ url_for(‘home’) }}”>
        Home
    </a>

</div>


<div class=”container”>


    <div class=”hero”>

        <h1>
            Student Portal
        </h1>

        <p>
            What would you like to do?
        </p>

    </div>


    <br>


    <div class=”grid”>


        <div class=”card”>

            <h2>
                📝 Apply for School ID
            </h2>

            <p>
                Submit your information
                And photo for your school ID.
            </p>

            <a
                Class=”btn”
                Href=”{{ url_for(‘apply_id’) }}”
            >
                Apply Now
            </a>

        </div>


        <div class=”card”>

            <h2>
                🔎 Track Application
            </h2>

            <p>
                Check the status of your
                School ID application.
            </p>

            <a
                Class=”btn”
                Href=”{{ url_for(‘track_application’) }}”
            >
                Track Now
            </a>

        </div>


    </div>


</div>


</body>

</html>
        “””,
        Style=STYLE
    )


# ==========================================================
# APPLY FOR SCHOOL ID
# ==========================================================

@app.route(
    “/student/apply”,
    Methods=[“GET”, “POST”]
)
Def apply_id():

    If request.method == “POST”:

        Student_id = request.form.get(
            “student_id”,
            “”
        ).strip()

        First_name = request.form.get(
            “first_name”,
            “”
        ).strip()

        Middle_name = request.form.get(
            “middle_name”,
            “”
        ).strip()

        Last_name = request.form.get(
            “last_name”,
            “”
        ).strip()

        Suffix = request.form.get(
            “suffix”,
            “”
        ).strip()

        Course = request.form.get(
            “course”,
            “”
        ).strip()

        Year_level = request.form.get(
            “year_level”,
            “”
        ).strip()

        Section = request.form.get(
            “section”,
            “”
        ).strip()

        Birth_date = request.form.get(
            “birth_date”,
            “”
        ).strip()

        Sex = request.form.get(
            “sex”,
            “”
        ).strip()

        Email = request.form.get(
            “email”,
            “”
        ).strip()

        Phone = request.form.get(
            “phone”,
            “”
        ).strip()

        Address = request.form.get(
            “address”,
            “”
        ).strip()

        Emergency_contact = request.form.get(
            “emergency_contact”,
            “”
        ).strip()

        Emergency_phone = request.form.get(
            “emergency_phone”,
            “”
        ).strip()


        # Required fields

        If not (
            Student_id
            And first_name
            And last_name
            And course
            And year_level
        ):

            Return “””
            <script>
                Alert(
                    “Please complete all required fields.”
                );
                History.back();
            </script>
            “””


        # Check duplicate application

        Connection = get_db()

        Existing = connection.execute(
            “””
            SELECT *
            FROM applications
            WHERE student_id = ?
            AND status NOT IN (
                ‘Rejected’,
                ‘Released’
            )
            “””,
            (student_id,)
        ).fetchone()

        Connection.close()


        If existing:

            Return render_template_string(
                “””
                <!DOCTYPE html>

                <html>

                <head>
                    <title>Existing Application</title>
                    {{ style|safe }}
                </head>

                <body>

                <div class=”container”>

                    <div class=”card”>

                        <h2>
                            ⚠️ Existing Application
                        </h2>

                        <p>
                            An active application already
                            Exists for this Student ID.
                        </p>

                        <p>
                            Application ID:
                        </p>

                        <div class=”application-id”>
                            {{ application_id }}
                        </div>

                        <br>

                        <a
                            Class=”btn”
                            Href=”{{ url_for(
                                ‘track_application’
                            ) }}”
                        >
                            Track Application
                        </a>

                    </div>

                </div>

                </body>

                </html>
                “””,
                Style=STYLE,
                Application_id=existing[
                    “application_id”
                ]
            )


        # --------------------------------------------------
        # PHOTO UPLOAD
        # --------------------------------------------------

        Photo_name = None

        Photo = request.files.get(
            “photo”
        )

        Application_id = (
            Generate_application_id()
        )


        If photo and photo.filename:

            If not allowed_file(
                Photo.filename
            ):

                Return “””
                <script>
                    Alert(
                        “Only JPG, JPEG, and PNG files are allowed.”
                    );
                    History.back();
                </script>
                “””


            Original_name = secure_filename(
                Photo.filename
            )

            Photo_name = (
                Application_id
                + “_”
                + original_name
            )


            Photo.save(
                Os.path.join(
                    App.config[“UPLOAD_FOLDER”],
                    Photo_name
                )
            )


        # --------------------------------------------------
        # SAVE APPLICATION
        # --------------------------------------------------

        Now = datetime.now().strftime(
            “%Y-%m-%d %H:%M:%S”
        )


        Connection = get_db()


        Connection.execute(
            “””
            INSERT INTO applications
            (
                Application_id,
                Student_id,
                First_name,
                Middle_name,
                Last_name,
                Suffix,
                Course,
                Year_level,
                Section,
                Birth_date,
                Sex,
                Email,
                Phone,
                Address,
                Emergency_contact,
                Emergency_phone,
                Photo,
                Status,
                Remarks,
                Created_at,
                Updated_at
            )

            VALUES
            (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            “””,
            (
                Application_id,
                Student_id,
                First_name,
                Middle_name,
                Last_name,
                Suffix,
                Course,
                Year_level,
                Section,
                Birth_date,
                Sex,
                Email,
                Phone,
                Address,
                Emergency_contact,
                Emergency_phone,
                Photo_name,
                “Pending”,
                “”,
                Now,
                Now
            )
        )


        Connection.commit()

        Connection.close()


        # Add history

        Add_history(
            Application_id,
            “Pending”,
            “Application submitted 
