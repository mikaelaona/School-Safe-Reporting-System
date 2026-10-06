from flask import Flask, request, jsonify, session, send_from_directory, render_template
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
from pathlib import Path
import sqlite3
import os
import secrets
import uuid

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "findhub.db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates")
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().isoformat(timespec="seconds")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            user_role TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('LOST','FOUND')),
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            report_date TEXT NOT NULL,
            description TEXT NOT NULL,
            contact TEXT NOT NULL,
            turnover_location TEXT,
            secret_question TEXT,
            image_filename TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            item_title TEXT NOT NULL,
            claimant_name TEXT NOT NULL,
            claimant_contact TEXT NOT NULL,
            claim_answer TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            admin_note TEXT,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"message": "Admin authentication required."}), 401
        return view(*args, **kwargs)
    return wrapped


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/api/items")
def get_items():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, user_role, type, title, category, location, report_date,
               description, contact, turnover_location, secret_question,
               image_filename, status, created_at
        FROM items
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(row)
        item["userRole"] = item.pop("user_role")
        item["date"] = item.pop("report_date")
        item["turnoverLocation"] = item.pop("turnover_location")
        item["secretQuestion"] = item.pop("secret_question")
        filename = item.pop("image_filename")
        item["imageUrl"] = f"/uploads/{filename}" if filename else ""
        items.append(item)

    return jsonify(items)


@app.post("/api/items")
def create_item():
    form = request.form

    required = [
        "id", "userRole", "type", "title", "category",
        "location", "date", "description", "contact"
    ]

    missing = [field for field in required if not form.get(field, "").strip()]
    if missing:
        return jsonify({
            "message": "Please complete all required fields.",
            "missing": missing
        }), 400

    item_type = form["type"].strip().upper()
    if item_type not in {"LOST", "FOUND"}:
        return jsonify({"message": "Invalid report type."}), 400

    image_filename = None
    image = request.files.get("image")

    if image and image.filename:
        if not allowed_file(image.filename):
            return jsonify({"message": "Unsupported image format."}), 400

        original = secure_filename(image.filename)
        extension = original.rsplit(".", 1)[1].lower()
        image_filename = f"{uuid.uuid4().hex}.{extension}"
        image.save(UPLOAD_DIR / image_filename)

    item_id = form["id"].strip()
    if not item_id or len(item_id) > 120:
        item_id = f"item_{secrets.token_hex(8)}"

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO items (
                id, user_role, type, title, category, location,
                report_date, description, contact,
                turnover_location, secret_question,
                image_filename, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (
                item_id,
                form["userRole"].strip(),
                item_type,
                form["title"].strip(),
                form["category"].strip(),
                form["location"].strip(),
                form["date"].strip(),
                form["description"].strip(),
                form["contact"].strip(),
                form.get("turnoverLocation", "").strip(),
                form.get("secretQuestion", "").strip(),
                image_filename,
                now(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        if image_filename:
            (UPLOAD_DIR / image_filename).unlink(missing_ok=True)
        conn.close()
        return jsonify({"message": "That item ID already exists. Please submit again."}), 409

    conn.close()
    return jsonify({"message": "Report saved successfully.", "id": item_id}), 201


@app.get("/api/claims")
def get_claims():
    # Claims are only returned after admin authentication.
    if not session.get("is_admin"):
        return jsonify([])

    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, item_id, item_title, claimant_name, claimant_contact,
               claim_answer, status, admin_note, submitted_at
        FROM claims
        ORDER BY submitted_at DESC
        """
    ).fetchall()
    conn.close()

    result = []
    for row in rows:
        claim = dict(row)
        claim["claimId"] = claim.pop("id")
        claim["itemId"] = claim.pop("item_id")
        claim["itemTitle"] = claim.pop("item_title")
        claim["claimantName"] = claim.pop("claimant_name")
        claim["claimantContact"] = claim.pop("claimant_contact")
        claim["claimAnswer"] = claim.pop("claim_answer")
        claim["submittedAt"] = claim.pop("submitted_at")
        result.append(claim)

    return jsonify(result)


@app.post("/api/claims")
def create_claim():
    data = request.get_json(silent=True) or {}

    required = ["claimId", "itemId", "itemTitle", "claimantName", "claimantContact"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]

    if missing:
        return jsonify({
            "message": "Please complete your name and contact information.",
            "missing": missing
        }), 400

    conn = get_db()
    item = conn.execute(
        "SELECT id, title, type, status FROM items WHERE id=?",
        (str(data["itemId"]),),
    ).fetchone()

    if not item or item["status"] != "ACTIVE" or item["type"] != "FOUND":
        conn.close()
        return jsonify({"message": "This found item is no longer available for claiming."}), 404

    claim_id = str(data["claimId"]).strip() or f"claim_{secrets.token_hex(8)}"

    try:
        conn.execute(
            """
            INSERT INTO claims (
                id, item_id, item_title, claimant_name,
                claimant_contact, claim_answer, status,
                submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (
                claim_id,
                str(data["itemId"]),
                str(data["itemTitle"]).strip(),
                str(data["claimantName"]).strip(),
                str(data["claimantContact"]).strip(),
                str(data.get("claimAnswer", "")).strip(),
                now(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return jsonify({"message": "Unable to save the claim. Please try again."}), 409

    conn.close()
    return jsonify({"message": "Claim submitted successfully.", "id": claim_id}), 201


@app.post("/api/admin/verify")
def verify_admin():
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", ""))

    if secrets.compare_digest(password, ADMIN_PASSWORD):
        session["is_admin"] = True
        return jsonify({"ok": True})

    session.pop("is_admin", None)
    return jsonify({"message": "Incorrect admin password."}), 401


@app.post("/api/claims/<claim_id>/approve")
@admin_required
def approve_claim(claim_id):
    conn = get_db()
    claim = conn.execute(
        "SELECT * FROM claims WHERE id=?",
        (claim_id,),
    ).fetchone()

    if not claim:
        conn.close()
        return jsonify({"message": "Claim not found."}), 404

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (claim["item_id"],),
    ).fetchone()

    if not item:
        conn.close()
        return jsonify({"message": "Item not found."}), 404

    try:
        conn.execute(
            """
            UPDATE claims
            SET status='Approved',
                admin_note='Claim approved. Please coordinate with the school office for item turnover.'
            WHERE id=?
            """,
            (claim_id,),
        )
        conn.execute(
            "UPDATE items SET status='CLAIMED' WHERE id=?",
            (claim["item_id"],),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        return jsonify({"message": "Unable to approve claim."}), 500

    conn.close()
    return jsonify({"message": "Claim approved."})


@app.delete("/api/claims/<claim_id>/reject")
@admin_required
def reject_claim(claim_id):
    conn = get_db()
    claim = conn.execute(
        "SELECT id FROM claims WHERE id=?",
        (claim_id,),
    ).fetchone()

    if not claim:
        conn.close()
        return jsonify({"message": "Claim not found."}), 404

    conn.execute(
        """
        UPDATE claims
        SET status='Rejected',
            admin_note='Claim rejected. Please contact the school office for more information.'
        WHERE id=?
        """,
        (claim_id,),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Claim rejected."})


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"message": "Uploaded file is too large. Maximum size is 5 MB."}), 413


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
