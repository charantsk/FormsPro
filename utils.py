# utils.py
from functools import wraps
from flask_login import login_required, current_user
from flask import jsonify
import json 
from models import Question, Submission,QuestionType
from evaluate_answer import check_answer


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