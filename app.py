import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-ward42-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fixit.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

csrf = CSRFProtect(app)

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "worker-src 'self';"
    )
    return response

app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    street = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_cell = db.Column(db.String(10), nullable=False)
    photo_path = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coordinator(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Coordinator.query.get(int(user_id))

@app.before_request
def create_tables_and_admin():
    db.create_all()
    if not Coordinator.query.filter_by(username='coordinator').first():
        admin = Coordinator(username='coordinator')
        admin.set_password('TestPassword123!')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        category = request.form.get('category')
        street = request.form.get('street')
        description = request.form.get('description')
        reporter_name = request.form.get('reporter_name')
        reporter_cell = request.form.get('reporter_cell')
        
        errors = []
        if not category: errors.append("Category is required.")
        if not street: errors.append("Street is required.")
        if not description or len(description) < 10 or len(description) > 500:
            errors.append("Description must be between 10 and 500 characters.")
        if not reporter_name: errors.append("Name is required.")
        if not reporter_cell or not reporter_cell.startswith('0') or len(reporter_cell) != 10 or not reporter_cell.isdigit():
            errors.append("Valid 10-digit SA cell number required.")
            
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('report.html')

        photo_path = None
        file = request.files.get('photo')
        if file and file.filename != '':
            if file.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                flash("Invalid file type. Only JPEG, PNG, and WebP are allowed.", 'danger')
                return render_template('report.html')
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(filepath)
                photo_path = unique_name
            else:
                flash("Invalid file extension.", 'danger')
                return render_template('report.html')

        ref_num = f"W42-{uuid.uuid4().hex[:4].upper()}"
        new_report = Report(
            reference=ref_num, category=category, street=street,
            description=description, reporter_name=reporter_name,
            reporter_cell=reporter_cell, photo_path=photo_path
        )
        db.session.add(new_report)
        db.session.commit()
        flash(f"Report submitted! Reference: {ref_num}", 'success')
        return redirect(url_for('status'))

    return render_template('report.html')

@app.route('/status', methods=['GET', 'POST'])
def status():
    report_data = None
    if request.method == 'POST':
        ref = request.form.get('reference')
        report_data = Report.query.filter_by(reference=ref).first()
        if not report_data:
            flash("Reference number not found.", 'warning')
    return render_template('status.html', report=report_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Coordinator.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/all-reports')
@login_required
def all_reports():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('all_reports.html', reports=reports)

@app.route('/report/<int:report_id>/update', methods=['POST'])
@login_required
def update_status(report_id):
    new_status = request.form.get('status')
    if new_status in ['Open', 'In progress', 'Closed']:
        report = Report.query.get(report_id)
        if report:
            report.status = new_status
            db.session.commit()
            flash("Status updated.", 'success')
    return redirect(url_for('all_reports'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/reports/summary')
@csrf.exempt
def api_summary():
    categories = db.session.query(Report.category, db.func.count(Report.id)).group_by(Report.category).all()
    statuses = db.session.query(Report.status, db.func.count(Report.id)).group_by(Report.status).all()
    return jsonify({"categories": dict(categories), "statuses": dict(statuses)})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# IMPROVEMENT 2: Added route to serve offline.html from the root directory
@app.route('/offline.html')
def offline():
    return send_from_directory('.', 'offline.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)