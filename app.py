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

# SECRET KEY
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "school-id-system-secret-key-change-in-production"
)

# DATABASE AND UPLOAD SETTINGS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "school_id.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# ADMIN LOGIN
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ==========================================================
# DATABASE FUNCTIONS
# ==========================================================
def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = get_db()
    cursor = connection.cursor()
    
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL,
            status TEXT NOT NULL,
            remarks TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_student_id
        ON applications(student_id)
    """)

    connection.commit()
    connection.close()

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def generate_application_id():
    while True:
        code = secrets.token_hex(3).upper()
        application_id = f"SID-{code}"
        connection = get_db()
        existing = connection.execute(
            "SELECT id FROM applications WHERE application_id = ?",
            (application_id,)
        ).fetchone()
        connection.close()
        if not existing:
            return application_id

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def add_history(application_id, status, remarks=""):
    connection = get_db()
    connection.execute(
        "INSERT INTO application_history (application_id, status, remarks, created_at) VALUES (?, ?, ?, ?)",
        (application_id, status, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
# CSS / STYLE
# ==========================================================
STYLE = """
<style>
* { box-sizing: border-box; }
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
.logo { font-size: 23px; font-weight: bold; }
.navbar a { color: white; text-decoration: none; margin-left: 15px; }
.container { width: 92%; max-width: 1150px; margin: 30px auto; }
.hero {
    background: linear-gradient(135deg, #0756a6, #008bd2);
    color: white;
    padding: 55px 30px;
    border-radius: 22px;
    text-align: center;
}
.hero h1 { font-size: 42px; margin: 0 0 12px; }
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
.btn:hover { opacity: .9; }
.btn-success { background: #198754; }
input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 15px;
    border: 1px solid #ccd4df;
    border-radius: 8px;
    font-size: 15px;
}
label { font-weight: bold; }
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
table { width: 100%; border-collapse: collapse; }
th, td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}
th { background: #0756a6; color: white; }
.timeline { border-left: 3px solid #0756a6; padding-left: 20px; }
.timeline-item { margin-bottom: 20px; }
.small { color: #667085; font-size: 13px; }
footer { text-align: center; padding: 30px; color: #667085; }
.success-box { background: #d4edda; color: #155724; padding: 20px; border-radius: 12px; }
</style>
"""

# ==========================================================
# HOME
# ==========================================================
@app.route("/")
def home():
    return render_template_string("""
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
</div>
</body>
</html>
    """, style=STYLE)

# ==========================================================
# STUDENT PORTAL
# ==========================================================
@app.route("/student")
def student_portal():
    return render_template_string("""
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
            <p>Track your application using your Student ID or Application ID.</p>
            <a class="btn" href="{{ url_for('track_application') }}">Track Now</a>
        </div>
    </div>
</div>
</body>
</html>
    """, style=STYLE)

# ==========================================================
# APPLY FOR SCHOOL ID
# ==========================================================
@app.route("/student/apply", methods=["GET", "POST"])
def apply_id():
    if request.method == "POST":
        # Get form data
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

        # Validate required fields
        if not (student_id and first_name and last_name and course and year_level):
            return """
            <script>alert("Please fill in ALL required fields."); history.back();</script>
            """

        # Check existing active application
        connection = get_db()
        existing = connection.execute("""
            SELECT application_id FROM applications
            WHERE student_id = ? AND status NOT IN ('Rejected', 'Released')
        """, (student_id,)).fetchone()
        connection.close()

        if existing:
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Existing Application</title>
{{ style|safe }}
</head>
<body>
<div class="container">
    <div class="card">
        <h2>⚠️ Application Already Exists</h2>
        <p>You already have an active application.</p>
        <p>Application ID:</p>
        <div class="application-id">{{ app_id }}</div>
        <br>
        <a class="btn" href="{{ url_for('track_application') }}">Track Status</a>
    </div>
</div>
</body>
</html>
            """, style=STYLE, app_id=existing["application_id"])

        # Generate ID
        application_id = generate_application_id()

        # Handle photo upload
        photo_name = None
        photo = request.files.get("photo")
        if photo and photo.filename:
            if not allowed_file(photo.filename):
                return """
                <script>alert("Only JPG, JPEG, and PNG files are allowed."); history.back();</script>
                """
            ext = os.path.splitext(photo.filename)[1].lower()
            photo_name = f"{application_id}{ext}"
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_name))

        # Save the application and its first history entry in one transaction.
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection = get_db()

        try:
            connection.execute("""
                INSERT INTO applications (
                    application_id, student_id, first_name, middle_name, last_name, suffix,
                    course, year_level, section, birth_date, sex, email, phone, address,
                    emergency_contact, emergency_phone, photo, status, remarks, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                application_id, student_id, first_name, middle_name, last_name, suffix,
                course, year_level, section, birth_date, sex, email, phone, address,
                emergency_contact, emergency_phone, photo_name, "Pending", "", now, now
            ))

            connection.execute("""
                INSERT INTO application_history
                    (application_id, status, remarks, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                application_id,
                "Pending",
                "Application submitted successfully",
                now
            ))

            connection.commit()

        except sqlite3.IntegrityError:
            connection.rollback()

            if photo_name:
                photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_name)
                if os.path.exists(photo_path):
                    os.remove(photo_path)

            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Submission Error</title>
                {{ style|safe }}
            </head>
            <body>
            <div class="container">
                <div class="card">
                    <h2>⚠️ Submission Could Not Be Completed</h2>
                    <p>This Student ID already has an active application.</p>
                    <a class="btn" href="{{ url_for('track_application') }}">Track Application</a>
                    &nbsp;
                    <a class="btn btn-success" href="{{ url_for('apply_id') }}">Try Again</a>
                </div>
            </div>
            </body>
            </html>
            """, style=STYLE)

        finally:
            connection.close()

        # ✅ SUCCESS PAGE
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>✅ Submitted Successfully</title>
{{ style|safe }}
</head>
<body>
<div class="navbar">
    <div class="logo">🪪 School ID System</div>
    <a href="{{ url_for('home') }}">Home</a>
</div>
<div class="container">
    <div class="card success-box">
        <h2>✅ Application Submitted Successfully!</h2>
        <p>Thank you for submitting your application. Please save your Application ID below:</p>
        <div class="application-id">{{ application_id }}</div>
        <p style="margin-top: 15px;">Use this ID to check your status later.</p>
        <br>
        <a class="btn" href="{{ url_for('track_application', app_id=application_id) }}">Track My Application</a>
        &nbsp;&nbsp;
        <a class="btn btn-success" href="{{ url_for('home') }}">Back to Home</a>
    </div>
</div>
</body>
</html>
        """, style=STYLE, application_id=application_id)

    # GET — Show form
    return render_template_string("""
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
                <div><label>Student ID *</label><input type="text" name="student_id" required></div>
                <div><label>First Name *</label><input type="text" name="first_name" required></div>
                <div><label>Middle Name</label><input type="text" name="middle_name"></div>
                <div><label>Last Name *</label><input type="text" name="last_name" required></div>
                <div><label>Suffix</label><input type="text" name="suffix" placeholder="Jr., Sr., III"></div>
                <div><label>Course / Program *</label><input type="text" name="course" required></div>
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
                <div><label>Section</label><input type="text" name="section"></div>
                <div><label>Birth Date</label><input type="date" name="birth_date"></div>
                <div>
                    <label>Sex</label>
                    <select name="sex">
                        <option value="">Select</option>
                        <option>Male</option>
                        <option>Female</option>
                    </select>
                </div>
                <div><label>Email</label><input type="email" name="email"></div>
                <div><label>Phone Number</label><input type="tel" name="phone"></div>
            </div>
            <div><label>Complete Address</label><textarea name="address"></textarea></div>
            <div class="form-grid">
                <div><label>Emergency Contact Person</label><input type="text" name="emergency_contact"></div>
                <div><label>Emergency Contact Phone</label><input type="tel" name="emergency_phone"></div>
            </div>
            <div>
                <label>ID Photo (JPG, JPEG, PNG only — max 5MB)</label>
                <input type="file" name="photo" accept=".jpg,.jpeg,.png">
            </div>
            <p><em>* Required fields</em></p>
            <button type="submit" class="btn">Submit Application</button>
        </form>
    </div>
</div>
</body>
</html>
    """, style=STYLE)

# ==========================================================
# TRACK APPLICATION
# ==========================================================
@app.route("/student/track", methods=["GET", "POST"])
def track_application():
    """Track an application using Student ID or Application ID."""
    if request.method == "POST":
        search_type = request.form.get("search_type", "student_id").strip()
        search_value = request.form.get("search_value", "").strip()

        if not search_value:
            return render_template_string("""
            <script>
                alert("Please enter your Student ID or Application ID.");
                history.back();
            </script>
            """)

        if search_type == "application_id":
            return redirect(url_for("track_application", app_id=search_value))

        return redirect(url_for("track_application", student_id=search_value))

    app_id = request.args.get("app_id", "").strip()
    student_id = request.args.get("student_id", "").strip()

    if not app_id and not student_id:
        return render_template_string("""
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
                <p>Enter your Student ID to view your application status and history.</p>

                <form method="post">
                    <label>Search By</label>
                    <select name="search_type" id="search_type" onchange="updatePlaceholder()">
                        <option value="student_id">Student ID</option>
                        <option value="application_id">Application ID</option>
                    </select>

                    <label id="search_label">Student ID</label>
                    <input
                        type="text"
                        id="search_value"
                        name="search_value"
                        placeholder="Enter your Student ID"
                        required
                    >

                    <button type="submit" class="btn">🔎 Track Application</button>
                </form>
            </div>
        </div>

        <script>
        function updatePlaceholder() {
            const type = document.getElementById("search_type").value;
            const label = document.getElementById("search_label");
            const input = document.getElementById("search_value");

            if (type === "student_id") {
                label.textContent = "Student ID";
                input.placeholder = "Enter your Student ID";
            } else {
                label.textContent = "Application ID";
                input.placeholder = "e.g. SID-ABC123";
            }
        }
        </script>
        </body>
        </html>
        """, style=STYLE)

    connection = get_db()

    if student_id:
        applications = connection.execute("""
            SELECT * FROM applications
            WHERE student_id = ?
            ORDER BY created_at DESC
        """, (student_id,)).fetchall()
    else:
        applications = connection.execute("""
            SELECT * FROM applications
            WHERE application_id = ?
        """, (app_id,)).fetchall()

    connection.close()

    if not applications:
        search_display = student_id if student_id else app_id

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Not Found</title>
            {{ style|safe }}
        </head>
        <body>
        <div class="container">
            <div class="card">
                <h2>❌ Application Not Found</h2>
                <p>No application record was found for:</p>
                <div class="application-id" style="font-size:24px;">
                    {{ search_display }}
                </div>
                <p class="small">
                    Please check your Student ID or Application ID and try again.
                </p>
                <a class="btn" href="{{ url_for('track_application') }}">Try Again</a>
            </div>
        </div>
        </body>
        </html>
        """, style=STYLE, search_display=search_display)

    # Load status history for every application belonging to the Student ID.
    results = []
    connection = get_db()

    for app_data in applications:
        history = connection.execute("""
            SELECT * FROM application_history
            WHERE application_id = ?
            ORDER BY created_at DESC
        """, (app_data["application_id"],)).fetchall()

        results.append((app_data, history))

    connection.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Application Status</title>
        {{ style|safe }}
    </head>
    <body>
    <div class="navbar">
        <div class="logo">🪪 School ID System</div>
        <a href="{{ url_for('student_portal') }}">Back</a>
    </div>

    <div class="container">
        <div class="card">
            <h2>🔎 Application Tracking</h2>
            <p>
                <strong>Student ID:</strong>
                {{ results[0][0]['student_id'] }}
            </p>
            <p class="small">
                Your Student ID is linked to the application record stored in the system.
            </p>
        </div>

        {% for app, history in results %}
        <div class="card">
            <h2>Application {{ app['application_id'] }}</h2>

            <div class="form-grid">
                <div>
                    <label>Student ID</label>
                    <p><strong>{{ app['student_id'] }}</strong></p>
                </div>

                <div>
                    <label>Name</label>
                    <p>
                        {{ app['first_name'] }}
                        {{ app['middle_name'] or '' }}
                        {{ app['last_name'] }}
                        {{ app['suffix'] or '' }}
                    </p>
                </div>

                <div>
                    <label>Course / Program</label>
                    <p>{{ app['course'] }}</p>
                </div>

                <div>
                    <label>Year Level</label>
                    <p>{{ app['year_level'] }}</p>
                </div>

                <div>
                    <label>Status</label>
                    <p>
                        <span class="status {{ app['status'].lower() }}">
                            {{ app['status'] }}
                        </span>
                    </p>
                </div>

                <div>
                    <label>Submitted</label>
                    <p>{{ app['created_at'] }}</p>
                </div>
            </div>

            {% if app['remarks'] %}
                <p><strong>Remarks:</strong> {{ app['remarks'] }}</p>
            {% endif %}

            {% if app['photo'] %}
                <p><strong>Submitted Photo:</strong></p>
                <img src="{{ url_for('uploaded_file', filename=app['photo']) }}" class="profile-photo">
            {% endif %}

            <hr style="border:0;border-top:1px solid #ddd;margin:25px 0;">

            <h3>📋 Status History</h3>
            <div class="timeline">
                {% for item in history %}
                <div class="timeline-item">
                    <p>
                        <span class="status {{ item['status'].lower() }}">
                            {{ item['status'] }}
                        </span>
                    </p>
                    <p>{{ item['remarks'] or '—' }}</p>
                    <p class="small">{{ item['created_at'] }}</p>
                </div>
                {% else %}
                <p>No history available.</p>
                {% endfor %}
            </div>
        </div>
        {% endfor %}

        <div class="card">
            <a class="btn" href="{{ url_for('track_application') }}">
                🔎 Track Another Student ID
            </a>
        </div>
    </div>
    </body>
    </html>
    """, style=STYLE, results=results)

# ==========================================================
# SERVE UPLOADS
# ==========================================================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ==========================================================
# ADMIN ROUTES
# ==========================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template_string("""
<!DOCTYPE html>
<html>
<head><title>Login Failed</title>{{ style|safe }}</head>
<body>
<div class="container"><div class="card">
    <h2>❌ Invalid Login</h2>
    <a class="btn" href="{{ url_for('admin_login') }}">Try Again</a>
</div></div>
</body>
</html>
        """, style=STYLE)
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head><title>Admin Login</title>{{ style|safe }}</head>
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
    """, style=STYLE)

@app.route("/admin")
@admin_required
def admin_dashboard():
    connection = get_db()
    applications = connection.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
    connection.close()
    return render_template_string("""
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title>{{ style|safe }}</head>
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
            <th>Application ID</th><th>Student ID</th><th>Name</th><th>Course</th><th>Status</th><th>Date</th><th>Action</th>
        </tr>
        {% for app in applications %}
        <tr>
            <td>{{ app['application_id'] }}</td>
            <td><strong>{{ app['student_id'] }}</strong></td>
            <td>{{ app['first_name'] }} {{ app['last_name'] }}</td>
            <td>{{ app['course'] }}</td>
            <td><span class="status {{ app['status'].lower() }}">{{ app['status'] }}</span></td>
            <td>{{ app['created_at'] }}</td>
            <td><a class="btn" style="padding: 6px 10px; font-size: 12px;" 
               href="{{ url_for('admin_view', app_id=app['application_id']) }}">View</a></td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <div class="card"><p>No applications yet.</p></div>
    {% endif %}
</div>
</body>
</html>
    """, style=STYLE, applications=applications)

@app.route("/admin/view/<app_id>", methods=["GET", "POST"])
@admin_required
def admin_view(app_id):
    connection = get_db()
    app_data = connection.execute("SELECT * FROM applications WHERE application_id = ?", (app_id,)).fetchone()
    history = connection.execute("SELECT * FROM application_history WHERE application_id = ? ORDER BY created_at DESC", (app_id,)).fetchall()
    
    if not app_data:
        connection.close()
        return "Not found", 404
    
    if request.method == "POST":
        new_status = request.form.get("status", "")
        remarks = request.form.get("remarks", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection.execute(
            "UPDATE applications SET status=?, remarks=?, updated_at=? WHERE application_id=?",
            (new_status, remarks, now, app_id)
        )

        connection.execute("""
            INSERT INTO application_history
                (application_id, status, remarks, created_at)
            VALUES (?, ?, ?, ?)
        """, (app_id, new_status, remarks, now))

        connection.commit()
        connection.close()
        return redirect(url_for("admin_view", app_id=app_id))
    
    connection.close()
    return render_template_string("""
<!DOCTYPE html>
<html>
<head><title>View — {{ app_id }}</title>{{ style|safe }}</head>
<body>
<div class="navbar">
    <div class="logo">🪪 Application</div>
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
            <div><label>Full Name</label><p>{{ app['first_name'] }} {{ app['last_name'] }}</p></div>
            <div><label>Status</label><p><span class="status {{ app['status'].lower() }}">{{ app['status'] }}</span></p></div>
        </div>
    </div>
    <div class="card">
        <h3>Update Status</h3>
        <form method="post">
            <select name="status">
                {% for s in ['Pending', 'Processing', 'Approved', 'Ready', 'Released', 'Rejected'] %}
                <option value="{{ s }}" {{ 'selected' if app['status']==s else '' }}>{{ s }}</option>
                {% endfor %}
            </select>
            <label>Remarks</label>
            <textarea name="remarks">{{ app['remarks'] or '' }}</textarea>
            <button type="submit" class="btn">Update</button>
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
    """, style=STYLE, app_id=app_id, app=app_data, history=history)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# ==========================================================
# RUN
# ==========================================================
# Initialize the database when the application is loaded.
init_db()

if __name__ == "__main__":
    app.run(debug=True)