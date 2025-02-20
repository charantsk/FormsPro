    let questions = [];
    let currentQuestion = null;

    // Open question modal
    function openQuestionModal() {
      document.getElementById('question-modal').style.display = 'flex';
    }

    // Close question modal
    function closeModal() {
      document.getElementById('question-modal').style.display = 'none';
      clearQuestionFields();
    }

    // Clear the input fields
    function clearQuestionFields() {
      document.getElementById('question-text').value = '';
      document.getElementById('question-type').value = 'text';
      document.getElementById('correct-answer').value = '';
      document.getElementById('points').value = '1';
    }

    // Add a new question
    function addQuestion() {
  const text = document.getElementById('question-text').value;
  const type = document.getElementById('question-type').value;
  const correctAnswer = document.getElementById('correct-answer').value;
  const points = document.getElementById('points').value;

  let choices = [];
  if (type === 'MULTIPLE_CHOICE') {
    const choiceInputs = document.querySelectorAll('.choice-input');
    choices = Array.from(choiceInputs).map(input => input.value);
  }

  const question = {
    text,
    type,
    correctAnswer,
    points,
    choices
  };

  questions.push(question);
  renderQuestions();
  closeModal();
}

    // Render questions in the UI
    function renderQuestions() {
      const container = document.getElementById('questions-container');
      container.innerHTML = '';
      questions.forEach((question, index) => {
        const questionElement = document.createElement('div');
        questionElement.classList.add('question-item');
        questionElement.setAttribute('draggable', true);
        questionElement.setAttribute('data-index', index);
        questionElement.addEventListener('dragstart', handleDragStart);
        questionElement.addEventListener('dragover', handleDragOver);
        questionElement.addEventListener('drop', handleDrop);
        
        questionElement.innerHTML = `
    <span class="question-title">${question.text}</span>
    <div class="question-actions">
        <button class="button" onclick="editQuestion(${index})">Edit</button>
        <button class="button" onclick="deleteQuestion(${index})">Delete</button>
    </div>
`;


        container.appendChild(questionElement);
      });
    }

    // Edit a question
    function editQuestion(index) {
      const question = questions[index];
      currentQuestion = index;
      document.getElementById('question-text').value = question.text;
      document.getElementById('question-type').value = question.type;
      document.getElementById('correct-answer').value = question.correctAnswer;
      document.getElementById('points').value = question.points;
      openQuestionModal();
    }

    // Delete a question
    function deleteQuestion(index) {
      questions.splice(index, 1);
      renderQuestions();
    }

    // Save the form
    function saveForm() {
    const formType = document.getElementById('form-type').value;
    const formData = {
        title: document.getElementById('form-title').value,
        description: document.getElementById('form-description').value,
        form_type: formType,
        questions: questions.map(q => ({
          text: q.text,
          type: q.type,
          correct_answer: q.correctAnswer,
          points: parseInt(q.points),
          choices: q.choices || []
      }))
    };

    // Add timer only for QUESTION_BANK type
    if (formType === 'QUESTION_BANK') {
        const timerValue = document.getElementById('form-timer').value;
        
        // Validate timer
        if (!timerValue || timerValue < 1 || timerValue > 180) {
            alert('Please set a valid time limit between 1 and 180 minutes');
            return;
        }
        
        formData.time_limit = parseInt(timerValue);
    }

    if (!formData.title) {
        alert('Please enter a form title');
        return;
    }

    if (formType === 'QUESTION_BANK' && formData.questions.length === 0) {
        alert('Please add at least one question');
        return;
    }

    console.log('Sending form data:', formData);

    fetch('/api/forms/create', {
        method: 'POST',
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
        alert('Form created successfully!');
        window.location.href = '/dashboard';
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`Error creating form: ${error.message}`);
    });
}

    // Drag and drop handling
    let draggedItem = null;

    function handleDragStart(event) {
      draggedItem = event.target;
      setTimeout(() => {
        draggedItem.classList.add('dragging');
      }, 0);
    }

    function handleDragOver(event) {
      event.preventDefault();
      const currentItem = event.target;
      if (currentItem.classList.contains('question-item') && draggedItem !== currentItem) {
        currentItem.style.border = '1px solid #2980b9';
      }
    }

    function handleDrop(event) {
      event.preventDefault();
      const target = event.target;
      target.style.border = 'none';
      if (target.classList.contains('question-item') && draggedItem !== target) {
        const draggedIndex = draggedItem.getAttribute('data-index');
        const targetIndex = target.getAttribute('data-index');

        const draggedQuestion = questions[draggedIndex];
        questions.splice(draggedIndex, 1);
        questions.splice(targetIndex, 0, draggedQuestion);

        renderQuestions();
      }
      draggedItem.classList.remove('dragging');
    }

    // Add event listener for form type changes
    document.getElementById('form-type').addEventListener('change', function() {
    const questionSection = document.querySelector('.card:nth-child(2)');
    const timerSection = document.getElementById('timer-section');
    
    if (this.value === 'QUESTION_BANK') {
        questionSection.style.display = 'block';
        timerSection.style.display = 'block';
    } else {
        questionSection.style.display = 'none';
        timerSection.style.display = 'none';
    }
});

// Update the window load event listener
window.addEventListener('load', function() {
    const formType = document.getElementById('form-type').value;
    const questionSection = document.querySelector('.card:nth-child(2)');
    const timerSection = document.getElementById('timer-section');
    
    if (formType === 'QUESTION_BANK') {
        questionSection.style.display = 'block';
        timerSection.style.display = 'block';
    } else {
        questionSection.style.display = 'none';
        timerSection.style.display = 'none';
    }
});

document.getElementById("form-type").addEventListener("change", function () {
    let timerSection = document.getElementById("timer-section");
    if (this.value === "QUESTION_BANK") {
        timerSection.style.display = "block"; // Show the timer section
    } else {
        timerSection.style.display = "none"; // Hide it for other types
    }
});

// Trigger change event on page load to set the correct initial state
document.getElementById("form-type").dispatchEvent(new Event("change"));



