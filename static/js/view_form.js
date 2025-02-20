let formId = null;
let questions = [];
let editingQuestionIndex = null;

// Load form data when page loads
document.addEventListener('DOMContentLoaded', function() {
    formId = new URLSearchParams(window.location.search).get('form_id');
    if (formId) {
        loadFormData();
        loadSubmissions();
    }
});

function loadFormData() {
    fetch(`/api/forms/${formId}`)
    .then(response => response.json())
    .then(data => {
        console.log('Received form data:', data); // Debug log
        document.getElementById('form-title').value = data.title;
        document.getElementById('form-description').value = data.description;
        
        const formTypeElement = document.getElementById('form-type');
        const formType = data.form_type.toUpperCase();
        console.log('Form type:', formType); // Debug log
        
        // Log all available options
        console.log('Available options:', Array.from(formTypeElement.options).map(opt => opt.value));
        
        for(let option of formTypeElement.options) {
            if(option.value === formType) {
                option.selected = true;
                console.log('Found matching option:', option.value); // Debug log
                break;
            }
        }
        
        formTypeElement.dispatchEvent(new Event('change'));

        questions = data.questions;
        renderQuestions();
    })
    .catch(error => {
        console.error('Error loading form:', error);
        alert('Error loading form data');
    });
}

function loadSubmissions() {
    fetch(`/api/forms/${formId}/submissions`)
        .then(response => response.json())
        .then(data => {
            renderSubmissions(data);
        })
        .catch(error => console.error('Error loading submissions:', error));
}

function renderSubmissions(submissions) {
    const container = document.getElementById('submissions-container');
    const submissionsCard = container.closest('.card');

    if (submissions.length === 0) {
        submissionsCard.style.display = 'none';
        return;
    } else {
        submissionsCard.style.display = 'block';
    }

    // Helper function to get appropriate icon and color for autosubmission reason
    function getAutoSubmitInfo(reason) {
    if (!reason) return null;
    
    const info = {
        'time_expired': { icon: 'fa-clock', color: '#F59E0B ', text: 'Time Expired' },
        'tab_switched': { icon: 'fa-exchange-alt', color: '#F59E0B ', text: 'Tab Switched' },
        'window_resized': { icon: 'fa-expand-arrows-alt', color: '#F59E0B ', text: 'Window Resized' }
    };
    
    return info[reason] || { icon: 'fa-robot', color: '#F59E0B ', text: reason };
}


container.innerHTML = submissions.map(sub => {
    const initials = sub.username ? sub.username.charAt(0).toUpperCase() : '?';
    const autoSubmitInfo = getAutoSubmitInfo(sub.autosubmitted);
    
    // Create a proper Date object from ISO string and format it
    const submittedDate = new Date(sub.submitted_at);
    const formattedDate = submittedDate.toLocaleString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short'
    });

    return `
    <div class="submission-item card" style="margin-bottom: 1rem; padding: 1rem;">
        <div class="submission-header" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="width: 50px; height: 50px; background-color: #ddd; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 1.2rem; color: #555;">
                    ${initials}
                </div>
                <div>
                    <p><strong>User:</strong> ${sub.username} ( ${sub.user_email} ) (ID: ${sub.user_id})</p>
                    ${sub.form_type === 'QUESTION_BANK' ? 
                        `<p><strong>Score:</strong> <span style="color: ${sub.score >= 70 ? '#10B981' : '#EF4444'}">${sub.score}%</span></p>` : 
                        ''}
                    <p><strong>Submitted:</strong> ${formattedDate}</p>
                    ${autoSubmitInfo ? `
                    <p style="display: flex; align-items: center; gap: 0.5rem; color: ${autoSubmitInfo.color};">
                        <i class="fas ${autoSubmitInfo.icon}"></i>
                        <span><strong>Auto-submitted:</strong> ${autoSubmitInfo.text}</span>
                    </p>` : ''}
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <button class="button button-danger" onclick="deleteSubmission(${sub.id}); event.stopPropagation();">
                    <i class="fas fa-trash-alt"></i> Delete
                </button>
                <button class="view-report-button" onclick="toggleResponses(${sub.id}); event.stopPropagation();">
                    <i class="fas fa-eye"></i> View Submission
                </button>
                <button class="send-report-button" onclick="sendReport(${sub.id}); event.stopPropagation();">
                    <i class="fas fa-paper-plane"></i> Email Report
                </button>
            </div>
        </div>
        <div class="submission-responses" id="responses-${sub.id}" style="display: none; margin-top: 1rem;">
            ${renderResponses(sub.responses, sub.questions)}
        </div>
    </div>
    `;
}).join('');
}

// Keep the original renderResponses function unchanged
function renderResponses(responses, questions) {
    return Object.entries(responses)
        .map(([questionId, answer]) => {
            const question = questions[questionId];
            if (!question) return '';
            
            const isCorrect = question.correct_answer === 'null' || question.correct_answer.toLowerCase() === String(answer).toLowerCase();
            
            return `
                <div class="response-item" style="margin: 0.8rem 0; padding: 1rem; background-color: #fdfdfb; border-radius: 8px;">
    <div class="question-text" style="margin-bottom: 0.5rem; font-weight: bold;">
        Field: ${question.text}
    </div>
    <div style="padding: 0.75rem; border-radius: 6px; background-color: #ffeeba;">
        <strong>Response:</strong> ${answer}
    </div>
</div>


            `;
        }).join('');
}

// Updated function to match API expectations
async function evaluateAnswer(question, correctAnswer, userAnswer, button) {
    const container = button.closest('.ai-review-container');
    const reviewBox = container.querySelector('.aireview-box');
    const spinner = reviewBox.querySelector('.loading-spinner');
    const content = reviewBox.querySelector('.review-content');

    // Toggle review box if it's already been evaluated
    if (content.innerHTML !== '') {
        reviewBox.style.display = reviewBox.style.display === 'none' ? 'block' : 'none';
        return;
    }

    // Show loading state
    reviewBox.style.display = 'block';
    spinner.style.display = 'block';
    button.disabled = true;

    try {
        const response = await fetch('/api/evaluate-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mode: "evaluate",
                question: question,
                correct_answer: correctAnswer,
                user_answer: userAnswer
            })
        });

        if (!response.ok) {
            throw new Error('Failed to evaluate answer');
        }

        const data = await response.json();
        
        // Access the 'evaluate' property from the response
        content.innerHTML = data.evaluate || 'No evaluation available';
    } catch (error) {
        content.innerHTML = `<p style="color: #721c24;">Error: Failed to generate AI review. Please try again later.</p>`;
    } finally {
        spinner.style.display = 'none';
        button.disabled = false;
    }
}

// Function to send the report (example using a basic fetch, adapt for your backend)
function sendReport() {
    alert('The report shown below will be sent to the client\'s email.');
}

function toggleResponses(submissionId) {
const responsesDiv = document.getElementById(`responses-${submissionId}`);
const button = responsesDiv.parentElement.querySelector('.view-report-button');

if (responsesDiv.style.display === 'none') {
responsesDiv.style.display = 'block';
button.textContent = 'Hide Submission';
} else {
responsesDiv.style.display = 'none';
button.textContent = 'View Submission';
}
}

function deleteSubmission(submissionId) {
    if (confirm('Are you sure you want to delete this submission?')) {
        fetch(`/api/forms/submissions/${submissionId}`, {
            method: 'DELETE'
        })
        .then(() => loadSubmissions())
        .catch(error => alert('Error deleting submission'));
    }
}

function openQuestionModal(index = null) {
    editingQuestionIndex = index;
    const modal = document.getElementById('question-modal');
    const choicesSection = document.getElementById('choices-section');
    const questionTypeButtons = document.querySelectorAll('.question-type-btn');
    
    if (index !== null) {
        const question = questions[index];
        document.getElementById('question-text').value = question.text;
        document.getElementById('question-type').value = question.type;
        document.getElementById('correct-answer').value = question.correct_answer;
        document.getElementById('points').value = question.points;
        
        // Reset all buttons' active state
        questionTypeButtons.forEach(btn => btn.classList.remove('active'));
        
        // Set the active state for the correct button
        const activeButton = document.querySelector(`.question-type-btn[data-type="${question.type}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        // Handle multiple choice questions
        if (question.type === 'MULTIPLE_CHOICE') {
            choicesSection.style.display = 'block';
            const choicesContainer = document.getElementById('choices-container');
            choicesContainer.innerHTML = ''; // Clear existing choices
            
            // Add each choice
            if (question.choices && Array.isArray(question.choices)) {
                question.choices.forEach(choice => {
                    const choiceDiv = document.createElement('div');
                    choiceDiv.className = 'choice';
                    choiceDiv.innerHTML = `
                        <input type="text" class="choice-input" value="${choice}" placeholder="Enter choice">
                        <button type="button" onclick="removeChoice(this)">Remove</button>
                    `;
                    choicesContainer.appendChild(choiceDiv);
                });
            } else {
                // Add one empty choice input if no choices exist
                addChoice();
            }
        } else {
            choicesSection.style.display = 'none';
        }
    } else {
        clearQuestionFields();
        // Reset question type buttons
        questionTypeButtons.forEach(btn => btn.classList.remove('active'));
        const defaultButton = document.querySelector('.question-type-btn[data-type="SINGLE_WORD"]');
        if (defaultButton) {
            defaultButton.classList.add('active');
        }
    }
    
    modal.style.display = 'flex';
}

document.addEventListener("DOMContentLoaded", function() {
    const questionTypeButtons = document.querySelectorAll(".question-type-btn");
    const choicesSection = document.getElementById('choices-section');
  
    questionTypeButtons.forEach(button => {
        button.addEventListener("click", function() {
            // Remove active class from all buttons
            questionTypeButtons.forEach(btn => btn.classList.remove("active"));
            
            // Add active class to the selected button
            this.classList.add("active");
            
            // Set selected type to hidden input
            const selectedType = this.dataset.type;
            document.getElementById("question-type").value = selectedType;
            
            // Show/hide choices section based on question type
            if (selectedType === 'MULTIPLE_CHOICE') {
                choicesSection.style.display = 'block';
                if (document.querySelectorAll('.choice').length === 0) {
                    addChoice(); // Add one empty choice if none exist
                }
            } else {
                choicesSection.style.display = 'none';
            }
        });
    });
});

function clearQuestionFields() {
    document.getElementById('question-text').value = '';
    document.getElementById('question-type').value = 'SINGLE_WORD';
    document.getElementById('correct-answer').value = '';
    document.getElementById('points').value = '1';
}

function closeModal() {
    document.getElementById('question-modal').style.display = 'none';
    editingQuestionIndex = null;
}

function saveQuestion() {
    const questionData = {
        text: document.getElementById('question-text').value,
        type: document.getElementById('question-type').value,
        correct_answer: document.getElementById('correct-answer').value,
        points: parseInt(document.getElementById('points').value)
    };

    if (editingQuestionIndex !== null) {
        questions[editingQuestionIndex] = questionData;
    } else {
        questions.push(questionData);
    }

    renderQuestions();
    closeModal();
}

// Add a new question
function addQuestion() {
    const questionText = document.getElementById('question-text').value;
    const questionType = document.getElementById('question-type').value;
    const correctAnswer = document.getElementById('correct-answer').value;
    const points = document.getElementById('points').value;

    let choices = [];
    if (questionType === 'MULTIPLE_CHOICE') {
        const choiceInputs = document.querySelectorAll('.choice-input');
        choices = Array.from(choiceInputs).map(input => input.value).filter(val => val);
    }

    const newQuestion = {
        text: questionText,
        type: questionType,
        correct_answer: correctAnswer,
        points: parseInt(points),
        choices: choices
    };

    if (editingQuestionIndex !== null) {
        questions[editingQuestionIndex] = newQuestion;
    } else {
        questions.push(newQuestion);
    }

    renderQuestions();
    closeModal();
}

function addChoice() {
    const choicesContainer = document.getElementById('choices-container');
    const choiceDiv = document.createElement('div');
    choiceDiv.className = 'choice';
    choiceDiv.innerHTML = `
        <input type="text" class="choice-input" placeholder="Enter choice">
        <button type="button" onclick="removeChoice(this)">Remove</button>
    `;
    choicesContainer.appendChild(choiceDiv);
}

function removeChoice(button) {
    button.parentElement.remove();
}


function renderQuestions() {
const questionsContainer = document.getElementById('questions-container');
questionsContainer.innerHTML = '';

questions.forEach((question, index) => {
const questionElement = document.createElement('div');
questionElement.classList.add('question-item');

let choicesHtml = '';
if (question.type === 'MULTIPLE_CHOICE' && question.choices) {
    choicesHtml = `
        <p>Choices: ${question.choices.join(', ')}</p>
    `;
}

questionElement.innerHTML = `
    <div class="question-content">
        <strong>${question.text}</strong> 
        <p>Type: ${question.type}</p>
        ${choicesHtml}
        <p>Expected Answer: ${question.correct_answer}</p>
        <p>Points: ${question.points}</p>
    </div>
    <div class="question-actions">
        <button class="button" onclick="openQuestionModal(${index})">Edit</button>
        <button class="button button-danger" onclick="deleteQuestion(${index})">Delete</button>
    </div>
`;
questionsContainer.appendChild(questionElement);
});
}


function deleteQuestion(index) {
    if (confirm('Are you sure you want to delete this question?')) {
        questions.splice(index, 1);
        renderQuestions();
    }
}

function saveForm() {
    const formData = {
        title: document.getElementById('form-title').value,
        description: document.getElementById('form-description').value,
        questions: questions.map(q => ({
            text: q.text,
            type: q.type,
            correct_answer: q.correct_answer,
            points: parseInt(q.points)
        }))
    };

    if (!formData.title) {
        alert('Please enter a form title');
        return;
    }

    if (formData.questions.length === 0) {
        alert('Please add at least one question');
        return;
    }

    fetch(`/api/forms/${formId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || 'Unknown error occurred');
            });
        }
        return response.json();
    })
    .then(data => {
        alert('Form updated successfully!');
        window.location.href = '/dashboard';
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`Error updating form: ${error.message}`);
    });
}