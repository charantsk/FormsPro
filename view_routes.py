# view_routes.py
from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from models import db, User, UserRole, Submission, Form
from utils import requires_role, has_submitted_form
from datetime import datetime

view_bp = Blueprint('view', __name__)

@view_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@view_bp.route('/tutor')
@login_required
@requires_role(UserRole.CLIENT)
def tutor():
    return render_template('tutor.html')

@view_bp.route('/client_courses')
@login_required
@requires_role(UserRole.CLIENT)
def client_courses():
    return render_template('client_courses.html')

@view_bp.route('/admin_courses')
@login_required
@requires_role(UserRole.ADMIN)
def admin_courses():
    return render_template('admin_courses.html')

@view_bp.route('/client_research')
@login_required
@requires_role(UserRole.CLIENT)
def client_research():
    return render_template('client_research.html')

@view_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@view_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == UserRole.ADMIN:
        return render_template('admin_dashboard.html')
    elif current_user.role == UserRole.CLIENT:
        return render_template('client_dashboard.html')
    return jsonify({"error": "Unauthorized"}), 403

@view_bp.route('/client_profile')
@login_required
def client_profile():
    client = current_user
    submissions = db.session.query(
        Submission, Form.title.label('form_title')
    ).join(
        Form, Submission.form_id == Form.id
    ).filter(
        Submission.user_id == current_user.id
    ).all()
    
    submissions_data = [{
        'form_title': sub.form_title,
        'submitted_at': sub.Submission.submitted_at,
        'score': sub.Submission.score
    } for sub in submissions]

    return render_template('client_profile.html', client=client, submissions=submissions_data)

@view_bp.route('/admin_profile')
@login_required
def admin_profile():
    admin = current_user
    return render_template('admin_profile.html', admin=admin)

@view_bp.route('/register_user', methods=['GET', 'POST'])
def create_user_page():
    return render_template('create_user.html')

@view_bp.route('/admin/create_form')
@login_required
@requires_role(UserRole.ADMIN)
def create_form_page():
    return render_template('create_form.html')

@view_bp.route('/admin/view_form')
@login_required
@requires_role(UserRole.ADMIN)
def view_form_page():
    form_id = request.args.get('form_id')
    if not form_id:
        return redirect(url_for('dashboard'))
    return render_template('view_form.html', form_id=form_id)

@view_bp.route('/client/submit_form')
@login_required
@requires_role(UserRole.CLIENT)
def submit_form_page():
    form_id = request.args.get('form_id')
    if not form_id:
        return redirect(url_for('dashboard'))

    form = Form.query.get(int(form_id))
    if not form:
        return render_template('error.html', message="Form not found"), 404

    if has_submitted_form(current_user.id, int(form_id)):
        return render_template('error.html', message="You have already submitted this form"), 403

    current_time = datetime.now()

    if form.deadline and current_time > form.deadline:
        return render_template('deadline_passed.html', deadline=form.deadline)

    elif form.scheduled_at and current_time < form.scheduled_at:
        return render_template('wait_for_test.html', scheduled_at=form.scheduled_at)

    return render_template('submit_form.html', form_id=form_id, form_type=form.form_type)
