from flask import jsonify, request, render_template, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from functools import wraps
import json
from datetime import datetime, timezone
from models import db, User, Form, Question, Submission, UserRole, QuestionType, FormType
from evaluate_answer import check_answer
from edbot import EdBot  # Import the EdBot class



# Initialize EdBot (you might want to do this at application startup)
bot = EdBot(model_path="customweights.gguf")  # Adjust the path as needed


def requires_role(*roles):
    def wrapper(f):
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            return f(*args, **kwargs)
        wrapped.__name__ = f.__name__
        return wrapped
    return wrapper

def calculate_score(form_id, responses): 
    total_score = 0
    total_points = 0
    questions = Question.query.filter_by(form_id=form_id).all()
    
    responses_dict = json.loads(responses) if isinstance(responses, str) else responses
    
    for question in questions:
        total_points += question.points
        if str(question.id) in responses_dict:
            client_answer = str(responses_dict[str(question.id)]).strip()
            correct_answer = str(question.correct_answer).strip()
            
            # For multi-word questions
            if question.type == QuestionType.MULTI_WORD:  # Fixed reference
                # Convert keywords string to list
                keywords = [k.strip() for k in question.keywords.split(',')] if question.keywords else []
                
                # Use check_answer function for evaluation
                result = check_answer(
                    question=question.text,
                    correct_answer=correct_answer,
                    keywords=keywords,
                    client_answer=client_answer
                )
                
                if result == "Correct":
                    total_score += question.points
                    
            # For other question types
            else:
                if correct_answer == 'null' or client_answer.lower() == correct_answer.lower():
                    total_score += question.points
    
    return (total_score / total_points * 100) if total_points > 0 else 0


    
def has_submitted_form(user_id, form_id):
    submission = Submission.query.filter_by(
        user_id=user_id,
        form_id=form_id
    ).first()
    return submission is not None

# Authentication routes
def init_routes(app):
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error", "details": str(error)}), 500

    @app.route('/api/users/create', methods=['POST'])
    def create_user():
        data = request.get_json()
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already exists"}), 400
        
        if 'email' in data:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({"error": "Email already exists"}), 400
        
        user = User(
            username=data['username'],
            role=UserRole[data['role'].upper()],
            email=data.get('email')
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
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
        
        db.session.commit()
        return jsonify({"message": "User updated successfully"})

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @requires_role(UserRole.ADMIN)
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"})

    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and user.check_password(data['password']):
            login_user(user)
            return jsonify({"message": "Logged in successfully"})
        return jsonify({"error": "Invalid credentials"}), 401

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "Logged out successfully"})



    @app.route('/api/users', methods=['GET'])
    @login_required
    @requires_role(UserRole.ADMIN)  # Optional: Restrict to admin/admin users
    def get_all_users():
        users = User.query.all()
        users_data = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.name
            }
            for user in users
        ]
        return jsonify(users_data)



    # Form management routes
    @app.route('/api/forms/create', methods=['POST'])
    @requires_role(UserRole.ADMIN)
    def create_form():
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No data provided"}), 400

            if not data.get('title'):
                return jsonify({"error": "Form title is required"}), 400

            form_type = FormType[data.get('form_type', 'NOTIFICATION').upper()]

            form = Form(
                title=data['title'],
                description=data.get('description', ''),
                created_by=current_user.id,
                form_type=form_type,
                time_limit=data.get('time_limit') if form_type == FormType.QUESTION_BANK else None,
                scheduled=data.get('scheduled', False),  # Handle scheduled flag
                schedule_time=data.get('schedule_time')  # Add schedule time if provided
            )

            for q_data in data['questions']:
                question = Question(
                    text=q_data['text'],
                    type=QuestionType[q_data['type']],
                    correct_answer=q_data['correct_answer'],
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
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500


    @app.route('/api/forms/<int:form_id>', methods=['PUT'])
    @requires_role(UserRole.ADMIN)
    def edit_form(form_id):
        form = Form.query.get_or_404(form_id)
        data = request.get_json()
        
        form.title = data.get('title', form.title)
        form.description = data.get('description', form.description)
        
        if 'questions' in data:
            Question.query.filter_by(form_id=form_id).delete()
            for q_data in data['questions']:
                question = Question(
                    form_id=form_id,
                    text=q_data['text'],
                    type=QuestionType[q_data['type'].upper()],
                    correct_answer=q_data['correct_answer'],
                    points=q_data.get('points', 1)
                )
                db.session.add(question)
        
        db.session.commit()
        return jsonify({"message": "Form updated successfully"})

    @app.route('/api/forms/<int:form_id>', methods=['DELETE'])
    @requires_role(UserRole.ADMIN)
    def delete_form(form_id):
        form = Form.query.get_or_404(form_id)
        db.session.delete(form)
        db.session.commit()
        return jsonify({"message": "Form deleted successfully"})

    @app.route('/api/forms', methods=['GET'])
    @login_required
    def get_all_forms():
        if current_user.role == UserRole.CLIENT:
            forms = Form.query.filter(Form.form_type.in_([FormType.QUESTION_BANK, FormType.NOTIFICATION, FormType.SURVEY])).all()
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

    @app.route('/api/forms/<int:form_id>', methods=['GET'])
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

    @app.route('/api/forms/<int:form_id>/submit', methods=['POST'])
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

    @app.route('/api/forms/<int:form_id>/submissions', methods=['GET'])
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

    
    @app.route('/api/forms/submissions/<int:submission_id>', methods=['DELETE'])
    @requires_role(UserRole.ADMIN)
    def delete_submission(submission_id):
        submission = Submission.query.get_or_404(submission_id)
        db.session.delete(submission)
        db.session.commit()
        return jsonify({"message": "Submission deleted successfully"})

    @app.route('/api/user/submissions')
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

    # HTML Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
        

    @app.route('/tutor')
    @login_required
    @requires_role(UserRole.CLIENT)
    def tutor():
        return render_template('tutor.html')
    

    @app.route('/client_courses')
    @login_required
    @requires_role(UserRole.CLIENT)
    def client_courses():
        return render_template('client_courses.html')

    

    @app.route('/login', methods=['GET', 'POST'])
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == UserRole.ADMIN:
            return render_template('admin_dashboard.html')
        elif current_user.role == UserRole.CLIENT:
            return render_template('client_dashboard.html')
        return jsonify({"error": "Unauthorized"}), 403

    @app.route('/client_profile')
    @login_required
    def client_profile():
        client = current_user
        # Fetch submissions for the current user
        submissions = db.session.query(
            Submission, Form.title.label('form_title')
        ).join(
            Form, Submission.form_id == Form.id
        ).filter(
            Submission.user_id == current_user.id
        ).all()
        
        # Format submissions data
        submissions_data = [{
            'form_title': sub.form_title,
            'submitted_at': sub.Submission.submitted_at,
            'score': sub.Submission.score
        } for sub in submissions]
        
        return render_template('client_profile.html', 
                            client=client, 
                            submissions=submissions_data)

    @app.route('/admin_profile')
    @login_required
    def admin_profile():
        admin = current_user
        return render_template('admin_profile.html', admin=admin)

    @app.route('/register_user', methods=['GET', 'POST'])
    def create_user_page():
        return render_template('create_user.html')

    @app.route('/admin/create_form')
    @login_required
    @requires_role(UserRole.ADMIN)
    def create_form_page():
        return render_template('create_form.html')

    @app.route('/admin/view_form')
    @login_required
    @requires_role(UserRole.ADMIN)
    def view_form_page():
        form_id = request.args.get('form_id')
        if not form_id:
            return redirect(url_for('dashboard'))
        return render_template('view_form.html', form_id=form_id)

    @app.route('/client/submit_form')
    @login_required
    @requires_role(UserRole.CLIENT)
    def submit_form_page():
        form_id = request.args.get('form_id')
        if not form_id:
            return redirect(url_for('dashboard'))

        form = Form.query.get(int(form_id))
        if not form:
            return render_template('error.html', message="Form not found"), 404

        # Check if the form has been submitted already
        if has_submitted_form(current_user.id, int(form_id)):
            return render_template('error.html', message="You have already submitted this form"), 403

        current_time = datetime.utcnow()

        # Ensure scheduled_at and deadline_at are properly checked
        if form.scheduled_at and current_time < form.scheduled_at:
            # Current time is before the scheduled time
            return render_template('wait_for_test.html', scheduled_at=form.scheduled_at)

        if form.deadline_at and current_time > form.deadline_at:
            # Current time is past the deadline
            return render_template('deadline_passed.html', deadline_at=form.deadline_at)

        # If both checks pass, we are within the valid submission window
        return render_template('submit_form.html', form_id=form_id)
    


    @app.route('/api/evaluate-answer', methods=['POST'])
    def evaluate():
        try:
            data = request.json
            mode = data.get("mode")
            question = data.get("question")
            correct_answer = data.get("correct_answer")
            user_answer = data.get("user_answer")
            keywords = data.get("keywords", [])  # Optional
            context = data.get("context")  # Optional

            # Validate required fields
            if not all([mode, question, correct_answer, user_answer]):
                return jsonify({
                    "error": "Missing required fields. Please provide mode, question, correct_answer, and user_answer"
                }), 400

            if mode != "evaluate":
                return jsonify({"error": "Invalid mode"}), 400

            # Process the evaluation using EdBot
            result = bot.process(
                mode=mode,
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                keywords=keywords,
                context=context
            )

            return jsonify(result)

        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/api/tutor', methods=['POST'])
    def tutor_chat():
        try:
            data = request.json
            mode = "tutor"  # Fixed mode for this endpoint
            question = data.get("message")  # The user's message/question
            
            if not question:
                return jsonify({
                    "error": "Missing required field: message"
                }), 400

            # Process the tutoring request using EdBot
            result = bot.process(
                mode=mode,
                question=question,
                # Other parameters are optional for tutor mode
                correct_answer=None,
                user_answer=None,
                keywords=[],
                context=None,
                attachment=None
            )

            return jsonify({
                "response": result.get("tutor", "Sorry, I couldn't process your request.")
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500