# auth_routes.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, login_user, logout_user
from models import db, User, UserRole, ClassGroup, QuestionType, FormType
from utils import requires_role

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/enums', methods=['GET'])
def get_enums():
    """Return all enum values for frontend use"""
    return jsonify({
        'user_roles': [role.value for role in UserRole],
        'class_groups': [group.value for group in ClassGroup],
        'question_types': [qtype.value for qtype in QuestionType],
        'form_types': [ftype.value for ftype in FormType]
    })

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({"message": "Logged in successfully"})
    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/api/users/create', methods=['POST'])
def create_user():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    if 'email' in data and data['email']:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Email already exists"}), 400
    
    # Handle class_group for clients
    class_group = None
    if 'class_group' in data and data['class_group']:
        try:
            class_group = ClassGroup[data['class_group'].upper()]
        except KeyError:
            return jsonify({"error": "Invalid class group"}), 400

    user = User(
        username=data['username'],
        role=UserRole[data['role'].upper()],
        email=data.get('email'),
        class_group=class_group
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201

@auth_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@requires_role(UserRole.ADMIN)
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'username' in data:
        user.username = data['username']
    if 'password' in data:
        user.set_password(data['password'])
    if 'role' in data:
        user.role = UserRole[data['role'].upper()]
    if 'email' in data:
        if data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({"error": "Email already exists"}), 400
        user.email = data['email']
    if 'class_group' in data:
        try:
            user.class_group = ClassGroup[data['class_group'].upper()] if data['class_group'] else None
        except KeyError:
            return jsonify({"error": "Invalid class group"}), 400
    
    db.session.commit()
    return jsonify({"message": "User updated successfully"})

@auth_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@requires_role(UserRole.ADMIN)
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})

@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})

@auth_bp.route('/api/users', methods=['GET'])
@login_required
@requires_role(UserRole.ADMIN)
def get_all_users():
    users = User.query.all()
    users_data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name,
            "class_group": user.class_group.name if user.class_group else None
        }
        for user in users
    ]
    return jsonify(users_data)