import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(_name_)
CORS(app)

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(_file_))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload Configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Admin Password Configuration (Maaari mong palitan ito)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# -------------------------------------------------------------------
# Database Models
# -------------------------------------------------------------------

class Item(db.Model):
    _tablename_ = 'items'
    
    id = db.Column(db.String(50), primary_key=True)
    user_role = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    turnover_location = db.Column(db.String(150), nullable=True)
    secret_question = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "userRole": self.user_role,
            "title": self.title,
            "type": self.type,
            "category": self.category,
            "location": self.location,
            "date": self.date,
            "description": self.description,
            "contact": self.contact,
            "turnoverLocation": self.turnover_location,
            "secretQuestion": self.secret_question,
            "imageUrl": self.image_url
        }

class Claim(db.Model):
    _tablename_ = 'claims'
    
    claim_id = db.Column(db.String(50), primary_key=True)
    item_id = db.Column(db.String(50), db.ForeignKey('items.id'), nullable=False)
    item_title = db.Column(db.String(150), nullable=False)
    claimant_name = db.Column(db.String(100), nullable=False)
    claimant_contact = db.Column(db.String(100), nullable=False)
    claim_answer = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            "claimId": self.claim_id,
            "itemId": self.item_id,
            "itemTitle": self.item_title,
            "claimantName": self.claimant_name,
            "claimantContact": self.claimant_contact,
            "claimAnswer": self.claim_answer,
            "submittedAt": self.submitted_at
        }

with app.app_context():
    db.create_all()

# -------------------------------------------------------------------
# Routes & API Endpoints
# -------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/items', methods=['GET'])
def get_items():
    items = Item.query.order_by(Item.created_at.desc()).all()
    return jsonify([item.to_dict() for item in items]), 200

@app.route('/api/items', methods=['POST'])
def create_item():
    user_role = request.form.get('userRole')
    title = request.form.get('title')
    item_type = request.form.get('type')
    category = request.form.get('category')
    location = request.form.get('location')
    date = request.form.get('date')
    description = request.form.get('description')
    contact = request.form.get('contact')
    turnover_location = request.form.get('turnoverLocation')
    secret_question = request.form.get('secretQuestion')
    item_id = request.form.get('id') or f"item_{int(datetime.utcnow().timestamp()*1000)}"

    image_url = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"{item_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/uploads/{filename}"

    new_item = Item(
        id=item_id,
        user_role=user_role,
        title=title,
        type=item_type,
        category=category,
        location=location,
        date=date,
        description=description,
        contact=contact,
        turnover_location=turnover_location,
        secret_question=secret_question,
        image_url=image_url
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({"message": "Item registered successfully", "item": new_item.to_dict()}), 201

@app.route('/api/admin/verify', methods=['POST'])
def verify_admin():
    data = request.get_json() or {}
    password = data.get('password', '')
    if password == ADMIN_PASSWORD:
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "message": "Incorrect password"}), 401

@app.route('/api/claims', methods=['GET'])
def get_claims():
    claims = Claim.query.all()
    return jsonify([claim.to_dict() for claim in claims]), 200

@app.route('/api/claims', methods=['POST'])
def create_claim():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    new_claim = Claim(
        claim_id=data.get('claimId'),
        item_id=data.get('itemId'),
        item_title=data.get('itemTitle'),
        claimant_name=data.get('claimantName'),
        claimant_contact=data.get('claimantContact'),
        claim_answer=data.get('claimAnswer'),
        submitted_at=data.get('submittedAt')
    )
    db.session.add(new_claim)
    db.session.commit()
    return jsonify({"message": "Claim submitted successfully", "claim": new_claim.to_dict()}), 201

@app.route('/api/claims/<claim_id>/approve', methods=['POST'])
def approve_claim(claim_id):
    claim = Claim.query.get(claim_id)
    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    item = Item.query.get(claim.item_id)
    if item:
        db.session.delete(item)
        
    Claim.query.filter_by(item_id=claim.item_id).delete()
    db.session.commit()
    return jsonify({"message": "Claim approved"}), 200

@app.route('/api/claims/<claim_id>/reject', methods=['DELETE'])
def reject_claim(claim_id):
    claim = Claim.query.get(claim_id)
    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    db.session.delete(claim)
    db.session.commit()
    return jsonify({"message": "Claim rejected"}), 200

if _name_ == '_main_':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)