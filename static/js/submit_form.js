let formData = null;
let isSubmitting = false;
let isSurveyForm = false;
let resizeTimeout = null;
let timer = null;
let resizeStrikes = 0;
let visibilityStrikes = 0;
const MAX_STRIKES = 3;

const urlParams = new URLSearchParams(window.location.search);
const formId = urlParams.get('form_id');

if (!formId) {
    alert('No form ID provided');
    window.location.href = '/dashboard';
}

function startTimer(minutes) {
    if (isSurveyForm) return;

    const endTime = Date.now() + minutes * 60 * 1000;
    const timerElement = document.querySelector('.time-limit');

    timer = setInterval(() => {
        const timeLeft = endTime - Date.now();
        if (timeLeft <= 0) {
            clearInterval(timer);
            handleAutoSubmit();
            return;
        }

        const minutesLeft = Math.floor(timeLeft / 60000);
        const secondsLeft = Math.floor((timeLeft % 60000) / 1000);
        timerElement.textContent = `Time Remaining: ${minutesLeft}:${secondsLeft.toString().padStart(2, '0')}`;
    }, 1000);
}

function collectResponses() {
    const responses = {};
    if (formData && formData.questions) {
        formData.questions.forEach(question => {
            const inputElement = document.querySelector(`[name="question_${question.id}"]`);
            if (inputElement) {
                if (question.type === 'checkbox') {
                    responses[question.id] = inputElement.checked;
                } else {
                    responses[question.id] = inputElement.value;
                }
            }
        });
    }
    return responses;
}

function handleAutoSubmit() {
    if (isSurveyForm) return;
    
    const responses = collectResponses();
    if (Object.keys(responses).length > 0) {
        if (timer) clearInterval(timer);
        submitForm(responses, 'time_expired');
    }
}

function handleVisibilityAutoSubmit() {
    if (isSurveyForm) return;
    
    visibilityStrikes++;
    console.warn(`Tab switch warning: Strike ${visibilityStrikes}/${MAX_STRIKES}`);

    if (visibilityStrikes >= MAX_STRIKES) {
        const responses = collectResponses();
        if (Object.keys(responses).length > 0) {
            submitForm(responses, 'User Switched Tabs 3 Times');
        }
    }
}

function handleResizeAutoSubmit() {
    if (isSurveyForm) return;
    
    resizeStrikes++;
    console.warn(`Resize warning: Strike ${resizeStrikes}/${MAX_STRIKES}`);

    if (resizeStrikes >= MAX_STRIKES) {
        const responses = collectResponses();
        if (Object.keys(responses).length > 0) {
            submitForm(responses, 'window_resized_three_times');
        }
    }
}

function handleResize() {
    if (isSurveyForm) return;
    
    if (resizeTimeout) {
        clearTimeout(resizeTimeout);
    }
    resizeTimeout = setTimeout(() => {
        handleResizeAutoSubmit();
    }, 1000);
}

async function submitForm(responses, autoSubmitReason = null) {
    if (isSubmitting) return;
    isSubmitting = true;

    try {
        const response = await fetch(`/api/forms/${formId}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ 
                responses,
                autosubmitted: autoSubmitReason 
            }),
        });

        if (!response.ok) {
            throw new Error('Form submission failed');
        }

        const data = await response.json();
        
        if (!isSurveyForm) {
            alert(`Form submitted successfully! Your score: ${data.score}%`);
        } else {
            alert('Survey submitted successfully!');
        }
        
        window.location.href = '/dashboard';
    } catch (error) {
        console.error('Form submission error:', error);
        alert('Error submitting the form: ' + error.message);
    } finally {
        isSubmitting = false;
    }
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

function renderForm(form) {
    if (!form || !form.questions) {
        console.error('Invalid form data:', form);
        return;
    }

    const formElement = document.getElementById('form-submit');
    formElement.innerHTML = '';

    if (!isSurveyForm && form.time_limit) {
        const timeLimitElement = document.createElement('div');
        timeLimitElement.className = 'time-limit';
        formElement.appendChild(timeLimitElement);
        startTimer(form.time_limit);
    }

    if (!isSurveyForm) {
        shuffleArray(form.questions);
    }

    form.questions.forEach(question => {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';

        const label = document.createElement('label');
        label.htmlFor = `question_${question.id}`;
        label.textContent = question.text;
        formGroup.appendChild(label);

        let input;
        switch (question.type) {
            case 'single_word':
                input = document.createElement('input');
                input.type = 'text';
                break;
            case 'multi_word':
                input = document.createElement('textarea');
                break;
            case 'number':
                input = document.createElement('input');
                input.type = 'number';
                break;
            default:
                input = document.createElement('input');
                input.type = 'text';
        }

        input.id = `question_${question.id}`;
        input.name = `question_${question.id}`;
        input.required = true;
        input.className = 'form-control';

        formGroup.appendChild(input);
        formElement.appendChild(formGroup);
    });

    const submitGroup = document.createElement('div');
    submitGroup.className = 'form-group';

    const submitButton = document.createElement('button');
    submitButton.type = 'submit';
    submitButton.className = 'button';
    submitButton.textContent = 'Submit';

    submitGroup.appendChild(submitButton);
    formElement.appendChild(submitGroup);
}

fetch(`/api/forms/${formId}`, {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json',
    },
    credentials: 'same-origin'
})
.then(response => {
    if (!response.ok) {
        throw new Error('Failed to fetch form details');
    }
    return response.json();
})
.then(data => {
    if (!data || !data.questions) {
        throw new Error('Invalid form data received');
    }
    
    formData = data;
    isSurveyForm = data.form_type === 'SURVEY';
    
    if (isSurveyForm) {
        document.querySelector('.container').style.backgroundColor = '#fffff0';
    }
    
    document.getElementById('form-title').textContent = data.title;
    document.getElementById('form-description').textContent = data.description;

    if (!isSurveyForm) {
        const totalPoints = data.questions.reduce((sum, question) => sum + question.points, 0);
        document.getElementById('total-points').textContent = `Total Maximum Points: ${totalPoints}`;
    } else {
        document.getElementById('total-points').style.display = 'none';
    }

    renderForm(data);

    document.getElementById('form-submit').addEventListener('submit', function(event) {
        event.preventDefault();
        const responses = collectResponses();
        submitForm(responses);
    });
})
.catch(error => {
    console.error('Form loading error:', error);
    alert('Error loading form: ' + error.message);
});

window.addEventListener('beforeunload', function(e) {
    if (!isSurveyForm) {
        handleAutoSubmit();
        e.preventDefault();
        e.returnValue = '';
    }
});

document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') {
        handleVisibilityAutoSubmit();
    }
});

window.addEventListener('resize', handleResize);