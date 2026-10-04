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
# SCHOOL ID APPLICATION AND TRACKING SYSTEM
# ==========================================================
app = Flask(__name__)
# ----------------------------------------------------------
# SECRET KEY
# ----------------------------------------------------------
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "school-id-system-secret-key"
)
# ----------------------------------------------------------
# DATABASE AND UPLOAD SETTINGS
# ----------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(
    BASE_DIR,
    "school_id.db"
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
# Maximum upload size = 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png"
}
# ----------------------------------------------------------
# ADMIN LOGIN
# ----------------------------------------------------------
ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)
ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)

# ==========================================================
# DATABASE
# ==========================================================
def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = get_db()
    cursor = connection.cursor()
    # ------------------------------------------------------
    # ID APPLICATIONS TABLE
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
# HELPER FUNCTIONS
# ==========================================================
def generate_application_id():
    while True:
        code = secrets.token_hex(3).upper()
        application_id = "SID-" + code
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

def add_history(application_id, status, remarks=""):
    connection = get_db()
    connection.execute(
        """
        INSERT INTO application_history
        (application_id, status, remarks, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            application_id,
            status,
            remarks,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    connection.commit()
    connection.close()

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper

# ==========================================================
# DESIGN / CSS
# ==========================================================
STYLE = """
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
.navbar {
    background: linear-gradient(135deg, #0756a6, #008bd2);
    color: white;
    padding: 16px 6%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}
.logo {
    font-size: 23px;
    font-weight: bold;
}
.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 15px;
}
.container {
    width: 92%;
    max-width: 1150px;
    margin: 30px auto;
}
.hero {
    background: linear-gradient(135deg, #0756a6, #008bd2);
    color: white;
    padding: 55px 30px;
    border-radius: 22px;
    text-align: center;
}
.hero h1 {
    font-size: 42px;
    margin: 0 0 12px;
}
.hero p {
    font-size: 18px;
}
.card {
    background: white;
    padding: 25px;
    border-radius: 17px;
    margin-bottom: 20px;
    box-shadow: 0 4px 18px rgba(0,0,0,.07);
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
}
.stat {
    background: white;
    padding: 25px;
    border-radius: 16px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,.07);
}
.stat h2 {
    font-size: 34px;
    color: #0756a6;
    margin: 5px;
}
.btn {
    display: inline-block;
    padding: 12px 18px;
    background: #0756a6;
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
.btn-success {
    background: #198754;
}
.btn-danger {
    background: #dc3545;
}
.btn-warning {
    background: #f0ad00;
    color: black;
}
input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 15px;
    border: 1px solid #ccd4df;
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
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 15px;
}
.status {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: bold;
}
.pending { background: #fff0b3; color: #775c00; }
.processing { background: #cce5ff; color: #0756a6; }
.approved { background: #d4edda; color: #155724; }
.ready { background: #d1ecf1; color: #0c5460; }
.released { background: #198754; color: white; }
.rejected { background: #f8d7da; color: #842029; }
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
.application-id {
    font-size: 30px;
    font-weight: bold;
    color: #0756a6;
    letter-spacing: 2px;
}
.profile-photo {
    width: 180px;
    height: 180px;
    object-fit: cover;
    border-radius: 12px;
    border: 4px solid #0756a6;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}
th {
    background: #0756a6;
    color: white;
}
.timeline {
    border-left: 3px solid #0756a6;
    padding-left: 20px;
}
.timeline-item {
    margin-bottom: 20px;
}
.small {
    color: #667085;
    font-size: 13px;
}
footer {
    text-align: center;
    padding: 30px;
    color: #667085;
}
@media(max-width: 700px) {
    .hero h1 { font-size: 30px; }
    .navbar { justify-content: center; text-align: center; }
    table { font-size: 12px; }
}
</style>
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
<title>School ID System</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <div>
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('student_portal') }}">Student</a>
        <a href="{{ url_for('admin_login') }}">Admin</a>
    </div>
</div>
<div class="container">
    <div class="hero">
        <h1>🪪 School ID Application</h1>
        <p>Apply for your school ID and track your application online.</p>
        <br>
        <a class="btn" href="{{ url_for('student_portal') }}">Get Started</a>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h2>📝 Apply Online</h2>
            <p>Submit your student information and ID photo online.</p>
        </div>
        <div class="card">
            <h2>🔎 Track Application</h2>
            <p>Check your ID application status using your Application ID.</p>
        </div>
        <div class="card">
            <h2>🔐 Admin Management</h2>
            <p>School administrators can review, approve, and manage applications.</p>
        </div>
    </div>
</div>
<footer>School ID Application and Tracking System © 2026</footer>
</body>
</html>
        """,
        style=STYLE
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
<title>Student Portal</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('home') }}">Home</a>
</div>
<div class="container">
    <div class="hero">
        <h1>Student Portal</h1>
        <p>What would you like to do?</p>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h2>📝 Apply for School ID</h2>
            <p>Submit your information and photo for your school ID.</p>
            <a class="btn" href="{{ url_for('apply_id') }}">Apply Now</a>
        </div>
        <div class="card">
            <h2>🔎 Track Application</h2>
            <p>Check the status of your school ID application.</p>
            <a class="btn" href="{{ url_for('track_application') }}">Track Now</a>
        </div>
    </div>
</div>
</body>
</html>
        """,
        style=STYLE
    )

# ==========================================================
# APPLY FOR SCHOOL ID
# ==========================================================
@app.route("/student/apply", methods=["GET", "POST"])
def apply_id():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        suffix = request.form.get("suffix", "").strip()
        course = request.form.get("course", "").strip()
        year_level = request.form.get("year_level", "").strip()
        section = request.form.get("section", "").strip()
        birth_date = request.form.get("birth_date", "").strip()
        sex = request.form.get("sex", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        emergency_phone = request.form.get("emergency_phone", "").strip()

        # Required fields
        if not (student_id and first_name and last_name and course and year_level):
            return """
            <script>
                alert("Please complete all required fields.");
                history.back();
            </script>
            """

        # Check duplicate application
        connection = get_db()
        existing = connection.execute(
            """
            SELECT * FROM applications
            WHERE student_id = ? AND status NOT IN ('Rejected', 'Released')
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
<title>Existing Application</title>
{{ style|safe }}
</head>
<body>
<div class="container">
    <div class="card">
        <h2>⚠️ Existing Application</h2>
        <p>An active application already exists for this Student ID.</p>
        <p>Application ID:</p>
        <div class="application-id">{{ application_id }}</div>
        <br>
        <a class="btn" href="{{ url_for('track_application') }}">Track Application</a>
    </div>
</div>
</body>
</html>
                """,
                style=STYLE,
                application_id=existing["application_id"]
            )

        # PHOTO UPLOAD
        photo_name = None
        photo = request.files.get("photo")
        application_id = generate_application_id()

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                return """
                <script>
                    alert("Only JPG, JPEG, and PNG files are allowed.");
                    history.back();
                </script>
                """
            original_name = secure_filename(photo.filename)
            photo_name = application_id + "_" + original_name
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_name))

        # SAVE APPLICATION
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection = get_db()
        connection.execute(
            """
            INSERT INTO applications (
                application_id, student_id, first_name, middle_name, last_name, suffix,
                course, year_level, section, birth_date, sex, email, phone, address,
                emergency_contact, emergency_phone, photo, status, remarks, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id, student_id, first_name, middle_name, last_name, suffix,
                course, year_level, section, birth_date, sex, email, phone, address,
                emergency_contact, emergency_phone, photo_name, "Pending", "", now, now
            )
        )
        connection.commit()
        connection.close()

        # Add history
        add_history(application_id, "Pending", "Application submitted successfully")

        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
<title>Application Submitted</title>
{{ style|safe }}
</head>
<body>
<div class="container">
    <div class="card">
        <h2>✅ Application Submitted!</h2>
        <p>Your application has been received. Please save your Application ID:</p>
        <div class="application-id">{{ application_id }}</div>
        <p>Use this ID to track your application status later.</p>
        <br>
        <a class="btn" href="{{ url_for('track_application', app_id=application_id) }}">Track My Application</a>
        &nbsp;&nbsp;
        <a class="btn btn-success" href="{{ url_for('home') }}">Return Home</a>
    </div>
</div>
</body>
</html>
            """,
            style=STYLE,
            application_id=application_id
        )

    # GET form
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>Apply for School ID</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('student_portal') }}">Back</a>
</div>
<div class="container">
    <div class="card">
        <h2>📝 School ID Application Form</h2>
        <form method="post" enctype="multipart/form-data">
            <div class="form-grid">
                <div>
                    <label>Student ID *</label>
                    <input type="text" name="student_id" required>
                </div>
                <div>
                    <label>First Name *</label>
                    <input type="text" name="first_name" required>
                </div>
                <div>
                    <label>Middle Name</label>
                    <input type="text" name="middle_name">
                </div>
                <div>
                    <label>Last Name *</label>
                    <input type="text" name="last_name" required>
                </div>
                <div>
                    <label>Suffix</label>
                    <input type="text" name="suffix" placeholder="e.g. Jr., Sr., III">
                </div>
                <div>
                    <label>Course / Program *</label>
                    <input type="text" name="course" required>
                </div>
                <div>
                    <label>Year Level *</label>
                    <select name="year_level" required>
                        <option value="">Select Year</option>
                        <option>1st Year</option>
                        <option>2nd Year</option>
                        <option>3rd Year</option>
                        <option>4th Year</option>
                        <option>5th Year</option>
                        <option>Irregular</option>
                    </select>
                </div>
                <div>
                    <label>Section</label>
                    <input type="text" name="section">
                </div>
                <div>
                    <label>Birth Date</label>
                    <input type="date" name="birth_date">
                </div>
                <div>
                    <label>Sex</label>
                    <select name="sex">
                        <option value="">Select</option>
                        <option>Male</option>
                        <option>Female</option>
                    </select>
                </div>
                <div>
                    <label>Email</label>
                    <input type="email" name="email">
                </div>
                <div>
                    <label>Phone Number</label>
                    <input type="tel" name="phone">
                </div>
            </div>
            <div>
                <label>Complete Address</label>
                <textarea name="address"></textarea>
            </div>
            <div class="form-grid">
                <div>
                    <label>Emergency Contact Person</label>
                    <input type="text" name="emergency_contact">
                </div>
                <div>
                    <label>Emergency Contact Phone</label>
                    <input type="tel" name="emergency_phone">
                </div>
            </div>
            <div>
                <label>ID Photo (JPG, JPEG, PNG only, max 5MB)</label>
                <input type="file" name="photo" accept=".jpg,.jpeg,.png">
            </div>
            <p><em>Fields marked with * are required.</em></p>
            <button type="submit" class="btn">Submit Application</button>
        </form>
    </div>
</div>
</body>
</html>
        """,
        style=STYLE
    )

# ==========================================================
# TRACK APPLICATION
# ==========================================================
@app.route("/student/track", methods=["GET", "POST"])
def track_application():
    if request.method == "POST":
        app_id = request.form.get("application_id", "").strip()
        return redirect(url_for("track_application", app_id=app_id))
    
    app_id = request.args.get("app_id", "").strip()
    if not app_id:
        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
<title>Track Application</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('student_portal') }}">Back</a>
</div>
<div class="container">
    <div class="card">
        <h2>🔎 Track Your Application</h2>
        <form method="post">
            <label>Enter your Application ID</label>
            <input type="text" name="application_id" placeholder="e.g. SID-ABC123" required>
            <button type="submit" class="btn">Check Status</button>
        </form>
    </div>
</div>
</body>
</html>
            """,
            style=STYLE
        )
    
    connection = get_db()
    app = connection.execute(
        "SELECT * FROM applications WHERE application_id = ?", (app_id,)
    ).fetchone()
    history = connection.execute(
        "SELECT * FROM application_history WHERE application_id = ? ORDER BY created_at DESC",
        (app_id,)
    ).fetchall()
    connection.close()
    
    if not app:
        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
<title>Application Not Found</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('student_portal') }}">Back</a>
</div>
<div class="container">
    <div class="card">
        <h2>❌ Not Found</h2>
        <p>No application found with ID: <strong>{{ app_id }}</strong></p>
        <a class="btn" href="{{ url_for('track_application') }}">Try Again</a>
    </div>
</div>
</body>
</html>
            """,
            style=STYLE,
            app_id=app_id
        )
    
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>Application Status - {{ app_id }}</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('student_portal') }}">Back</a>
</div>
<div class="container">
    <div class="card">
        <h2>Application Status</h2>
        <p>Application ID:</p>
        <div class="application-id">{{ app_id }}</div>
        <p>Name: <strong>{{ app['first_name'] }} {{ app['last_name'] }}</strong></p>
        <p>Student ID: {{ app['student_id'] }}</p>
        <p>Current Status: <span class="status {{ app['status'].lower() }}">{{ app['status'] }}</span></p>
        {% if app['remarks'] %}
        <p>Remarks: {{ app['remarks'] }}</p>
        {% endif %}
        {% if app['photo'] %}
        <p>Submitted Photo:</p>
        <img src="{{ url_for('uploaded_file', filename=app['photo']) }}" class="profile-photo" alt="ID Photo">
        {% endif %}
    </div>
    
    <div class="card">
        <h3>📋 Status History</h3>
        <div class="timeline">
            {% for item in history %}
            <div class="timeline-item">
                <p><span class="status {{ item['status'].lower() }}">{{ item['status'] }}</span></p>
                <p>{{ item['remarks'] or 'No remarks' }}</p>
                <p class="small">{{ item['created_at'] }}</p>
            </div>
            {% else %}
            <p>No history available.</p>
            {% endfor %}
        </div>
    </div>
</div>
</body>
</html>
        """,
        style=STYLE,
        app_id=app_id,
        app=app,
        history=history
    )

# ==========================================================
# SERVE UPLOADED FILES
# ==========================================================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ==========================================================
# ADMIN LOGIN
# ==========================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template_string(
            """
<!DOCTYPE html>
<html>
<head>
<title>Admin Login</title>
{{ style|safe }}
</head>
<body>
<div class="container">
    <div class="card">
        <h2>❌ Invalid Credentials</h2>
        <p>Username or password is incorrect.</p>
        <a class="btn" href="{{ url_for('admin_login') }}">Try Again</a>
    </div>
</div>
</body>
</html>
            """,
            style=STYLE
        )
    
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>Admin Login</title>
{{ style|safe }}
</head>
<body>
<div class="container">
    <div class="card" style="max-width: 450px; margin: 50px auto;">
        <h2>🔐 Admin Login</h2>
        <form method="post">
            <label>Username</label>
            <input type="text" name="username" required>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit" class="btn" style="width: 100%;">Login</button>
        </form>
        <p style="margin-top: 15px;"><a href="{{ url_for('home') }}">← Back to Home</a></p>
    </div>
</div>
</body>
</html>
        """,
        style=STYLE
    )

# ==========================================================
# ADMIN DASHBOARD
# ==========================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    connection = get_db()
    applications = connection.execute(
        "SELECT * FROM applications ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>Admin Dashboard</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 Admin Dashboard</div>
    <div>
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('admin_logout') }}">Logout</a>
    </div>
</div>
<div class="container">
    <h2>📋 All Applications</h2>
    {% if applications %}
    <table>
        <tr>
            <th>Application ID</th>
            <th>Student Name</th>
            <th>Course / Year</th>
            <th>Status</th>
            <th>Submitted</th>
            <th>Action</th>
        </tr>
        {% for app in applications %}
        <tr>
            <td>{{ app['application_id'] }}</td>
            <td>{{ app['first_name'] }} {{ app['last_name'] }}</td>
            <td>{{ app['course'] }} - {{ app['year_level'] }}</td>
            <td><span class="status {{ app['status'].lower() }}">{{ app['status'] }}</span></td>
            <td>{{ app['created_at'] }}</td>
            <td>
                <a class="btn" style="padding: 6px 10px; font-size: 12px;" 
                   href="{{ url_for('admin_view', app_id=app['application_id']) }}">View</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <div class="card">
        <p>No applications yet.</p>
    </div>
    {% endif %}
</div>
</body>
</html>
        """,
        style=STYLE,
        applications=applications
    )

# ==========================================================
# ADMIN VIEW & UPDATE
# ==========================================================
@app.route("/admin/view/<app_id>", methods=["GET", "POST"])
@admin_required
def admin_view(app_id):
    connection = get_db()
    app = connection.execute(
        "SELECT * FROM applications WHERE application_id = ?", (app_id,)
    ).fetchone()
    history = connection.execute(
        "SELECT * FROM application_history WHERE application_id = ? ORDER BY created_at DESC",
        (app_id,)
    ).fetchall()
    
    if not app:
        connection.close()
        return "Application not found", 404
    
    if request.method == "POST":
        new_status = request.form.get("status", "")
        remarks = request.form.get("remarks", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection.execute(
            "UPDATE applications SET status=?, remarks=?, updated_at=? WHERE application_id=?",
            (new_status, remarks, now, app_id)
        )
        add_history(app_id, new_status, remarks)
        connection.commit()
        connection.close()
        return redirect(url_for("admin_view", app_id=app_id))
    
    connection.close()
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>View Application - {{ app_id }}</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 Application Details</div>
    <div>
        <a href="{{ url_for('admin_dashboard') }}">Back</a>
        <a href="{{ url_for('admin_logout') }}">Logout</a>
    </div>
</div>
<div class="container">
    <div class="card">
        <h2>{{ app_id }}</h2>
        {% if app['photo'] %}
        <img src="{{ url_for('uploaded_file', filename=app['photo']) }}" class="profile-photo">
        {% endif %}
        <div class="form-grid" style="margin-top: 20px;">
            <div><label>Student ID</label><p>{{ app['student_id'] }}</p></div>
            <div><label>Full Name</label><p>{{ app['first_name'] }} {{ app['middle_name'] }} {{ app['last_name'] }} {{ app['suffix'] }}</p></div>
            <div><label>Course</label><p>{{ app['course'] }}</p></div>
            <div><label>Year / Section</label><p>{{ app['year_level'] }} {{ app['section'] }}</p></div>
            <div><label>Contact</label><p>{{ app['email'] }}<br>{{ app['phone'] }}</p></div>
            <div><label>Current Status</label><p><span class="status {{ app['status'].lower() }}">{{ app['status'] }}</span></p></div>
        </div>
    </div>
    
    <div class="card">
        <h3>Update Status</h3>
        <form method="post">
            <label>Status</label>
            <select name="status">
                {% for s in ['Pending', 'Processing', 'Approved', 'Ready', 'Released', 'Rejected'] %}
                <option value="{{ s }}" {{ 'selected' if app['status']==s else '' }}>{{ s }}</option>
                {% endfor %}
            </select>
            <label>Remarks</label>
            <textarea name="remarks">{{ app['remarks'] or '' }}</textarea>
            <button type="submit" class="btn">Update Status</button>
        </form>
    </div>
    
    <div class="card">
        <h3>History</h3>
        <div class="timeline">
            {% for item in history %}
            <div class="timeline-item">
                <p><span class="status {{ item['status'].lower() }}">{{ item['status'] }}</span></p>
                <p>{{ item['remarks'] or '—' }}</p>
                <p class="small">{{ item['created_at'] }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
</body>
</html>
        """,
        style=STYLE,
        app_id=app_id,
        app=app,
        history=history
    )

# ==========================================================
# ADMIN LOGOUT
# ==========================================================
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# ==========================================================
# INITIALIZE DATABASE AND RUN
# ==========================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)