# form_routes.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Form, Question, Submission, UserRole, QuestionType, FormType,ClassGroup
from utils import requires_role, calculate_score, has_submitted_form
from models import User
import json
from datetime import datetime, timezone

form_bp = Blueprint('form', __name__)

@form_bp.route('/api/forms/create', methods=['POST'])
@requires_role(UserRole.ADMIN)
def create_form():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if not data.get('title'):
            return jsonify({"error": "Form title is required"}), 400

        if not data.get('target_class_group'):
            return jsonify({"error": "Target class group is required"}), 400
        
        form_type = FormType[data.get('form_type', 'NOTIFICATION').upper()]

        # Handle scheduled time if provided
        scheduled_at = None
        if data.get('scheduled_at'):
            try:
                scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid schedule time format"}), 400
        
        # Handle deadline if provided
        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid deadline format"}), 400
        
        form = Form(
            title=data['title'],
            description=data.get('description', ''),
            created_by=current_user.id,
            form_type=form_type,
            target_class_group=data['target_class_group'],
            time_limit=data.get('time_limit') if form_type == FormType.QUESTION_BANK else None,
            scheduled_at=scheduled_at,
            deadline=deadline
        )
        
        for q_data in data['questions']:
            question = Question(
                text=q_data['text'],
                type=QuestionType[q_data['type'].upper()],
                correct_answer=q_data.get('correct_answer'),
                points=int(q_data.get('points', 1)),
                choices=q_data.get('choices', []),
                keywords=','.join(q_data.get('keywords', [])) if q_data.get('keywords') else None
            )
            form.questions.append(question)
        
        db.session.add(form)
        db.session.commit()
        return jsonify({"message": "Form created successfully", "form_id": form.id}), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error creating form: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_bp.route('/api/forms/<int:form_id>', methods=['PUT'])
@requires_role(UserRole.ADMIN)
def edit_form(form_id):
    form = Form.query.get_or_404(form_id)
    data = request.get_json()
    
    form.title = data.get('title', form.title)
    form.description = data.get('description', form.description)
    
    if 'target_class_group' in data:
        form.target_class_group = ClassGroup[data['target_class_group'].upper()]
    
    if 'questions' in data:
        Question.query.filter_by(form_id=form_id).delete()
        for q_data in data['questions']:
            question = Question(
                form_id=form_id,
                text=q_data['text'],
                type=QuestionType[q_data['type'].upper()],
                correct_answer=q_data.get('correct_answer'),
                points=q_data.get('points', 1)
            )
            db.session.add(question)
    
    db.session.commit()
    return jsonify({"message": "Form updated successfully"})


@form_bp.route('/api/forms/<int:form_id>', methods=['DELETE'])
@requires_role(UserRole.ADMIN)
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    return jsonify({"message": "Form deleted successfully"})

@form_bp.route('/api/forms', methods=['GET'])
@login_required
def get_all_forms():
    if current_user.role == UserRole.CLIENT:
        forms = Form.query.filter(
            Form.form_type.in_([FormType.QUESTION_BANK, FormType.NOTIFICATION, FormType.SURVEY]),
            Form.target_class_group == current_user.class_group.value  # Ensure matching class groups
        ).all()
    else:
        forms = Form.query.all()

    forms_data = {
        'forms': [],
        'notifications': []
    }

    for form in forms:
        form_data = {
            'id': form.id,
            'title': form.title,
            'description': form.description,
            'created_by': form.created_by,
            'created_at': form.created_at.isoformat(),
            'form_type': form.form_type.value
        }

        if form.form_type == FormType.NOTIFICATION:
            forms_data['notifications'].append(form_data)
        else:
            if current_user.role == UserRole.CLIENT:
                form_data['already_submitted'] = has_submitted_form(current_user.id, form.id)
            forms_data['forms'].append(form_data)

    return jsonify(forms_data)



@form_bp.route('/api/forms/<int:form_id>', methods=['GET'])
@login_required
def get_form_details(form_id):
    form = Form.query.get_or_404(form_id)
    
    if current_user.role == UserRole.CLIENT and form.form_type not in [FormType.QUESTION_BANK, FormType.SURVEY]:
        return jsonify({"error": "Unauthorized"}), 403
    
    questions_data = [{
        'id': q.id,
        'text': q.text,
        'type': q.type.value,
        'points': q.points,
        'choices': q.choices if q.type == QuestionType.MULTIPLE_CHOICE else None
    } for q in form.questions]
    
    if current_user.role == UserRole.ADMIN:
        for i, q in enumerate(form.questions):
            questions_data[i]['correct_answer'] = q.correct_answer
    
    return jsonify({
        'id': form.id,
        'title': form.title,
        'description': form.description,
        'created_by': form.created_by,
        'created_at': form.created_at.isoformat(),
        'form_type': form.form_type.name,  # Make sure to use .name to get the string value
        'time_limit': form.time_limit,
        'questions': questions_data
    })

@form_bp.route('/api/forms/<int:form_id>/submit', methods=['POST'])
@login_required
def submit_form(form_id):
    if has_submitted_form(current_user.id, form_id):
        return jsonify({
            "error": "You have already submitted this form"
        }), 403
    
    form = Form.query.get_or_404(form_id)
    data = request.get_json()
    
    score = calculate_score(form_id, data['responses'])
    
    submission = Submission(
        form_id=form_id,
        user_id=current_user.id,
        responses=json.dumps(data['responses']),
        score=score,
        autosubmitted=data.get('autosubmitted'),
        submitted_at=datetime.now(timezone.utc)  # Explicitly set UTC time
    )
    
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({
        "message": "Form submitted successfully",
        "submission_id": submission.id,
        "score": score,
        "autosubmitted": submission.autosubmitted
    }), 201

@form_bp.route('/api/forms/<int:form_id>/submissions', methods=['GET'])
@requires_role(UserRole.ADMIN)
def get_form_submissions(form_id):
    form = Form.query.get_or_404(form_id)
    submissions = db.session.query(Submission, User).join(User, Submission.user_id == User.id)\
        .filter(Submission.form_id == form_id).all()
    
    questions = {q.id: {
        'text': q.text,
        'correct_answer': q.correct_answer,
        'type': q.type.value,
        'points': q.points
    } for q in form.questions}
    
    return jsonify([{
    'id': sub.id,
    'user_id': sub.user_id,
    'username': user.username,
    'user_email': user.email,
    'responses': json.loads(sub.responses),
    'submitted_at': sub.submitted_at.isoformat(),  # This will include timezone info
    'score': sub.score if form.form_type == FormType.QUESTION_BANK else None,
    'form_type': form.form_type.value,
    'questions': questions,
    'autosubmitted': sub.autosubmitted
} for sub, user in submissions])


@form_bp.route('/api/forms/submissions/<int:submission_id>', methods=['DELETE'])
@requires_role(UserRole.ADMIN)
def delete_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    db.session.delete(submission)
    db.session.commit()
    return jsonify({"message": "Submission deleted successfully"})

@form_bp.route('/api/user/submissions')
@login_required
def get_user_submissions():
    submissions = Submission.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': sub.id,
        'form_id': sub.form_id,
        'form_title': Form.query.get(sub.form_id).title,
        'submitted_at': sub.submitted_at.isoformat(),
        'score': sub.score
    } for sub in submissions])