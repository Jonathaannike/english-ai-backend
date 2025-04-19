// script.js

// --- Configuration ---
const API_BASE_URL = 'http://127.0.0.1:8000';

// --- Global State ---
let authToken = null;
let currentQuestions = []; // Stores the currently displayed questions with their IDs

// --- DOM Element References ---
const loginSection = document.getElementById('login-section');
const loginForm = document.getElementById('login-form');
const loginStatus = document.getElementById('login-status');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');

const exerciseSection = document.getElementById('exercise-section');
const generateButton = document.getElementById('generate-button');
const questionsContainer = document.getElementById('questions-container');
const submitButton = document.getElementById('submit-button');
const resultsSection = document.getElementById('results-section');

// --- Event Listeners ---
loginForm.addEventListener('submit', handleLogin);
generateButton.addEventListener('click', handleGenerateExercise);
submitButton.addEventListener('click', handleSubmitAnswers);


// --- Handler Functions ---

/**
 * Handles the login form submission.
 */
async function handleLogin(event) {
    event.preventDefault();
    console.log("Login attempt...");
    loginStatus.textContent = 'Logging in...';
    loginStatus.style.color = 'black';

    const email = emailInput.value;
    const password = passwordInput.value;

    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_BASE_URL}/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!response.ok) {
            let errorDetail = `Login failed: ${response.status}`;
            try { errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
            throw new Error(errorDetail);
        }
        const data = await response.json();

        console.log("Login successful");
        authToken = data.access_token; // Store the token
        loginStatus.textContent = 'Login successful!';
        loginStatus.style.color = 'green';
        loginSection.classList.add('hidden');
        exerciseSection.classList.remove('hidden');
        passwordInput.value = '';

    } catch (error) {
        console.error('Login error:', error);
        authToken = null;
        loginStatus.textContent = `Login failed: ${error.message}`;
        loginStatus.style.color = 'red';
        loginSection.classList.remove('hidden');
        exerciseSection.classList.add('hidden');
    }
}

/**
 * Handles the click on the "Generate Exercise" button.
 */
async function handleGenerateExercise() {
    console.log("Generating exercises...");
    questionsContainer.innerHTML = 'Loading questions...';
    questionsContainer.style.color = 'black';
    resultsSection.innerHTML = '';
    submitButton.classList.add('hidden');

    // Define parameters matching schemas.ExerciseGenerationRequest
    const exerciseParams = {
        topic: "Present Simple vs Present Continuous",
        level: "B1",
        exercise_type: "multiple_choice",
        num_questions: 3
    };

    try {
        const response = await fetch(`${API_BASE_URL}/generate/exercise`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(exerciseParams)
            // No Authorization needed for generation in this setup
        });

        if (!response.ok) {
            let errorDetail = `Exercise generation failed: ${response.status}`;
            try { errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
            throw new Error(errorDetail);
        }
        const data = await response.json();

        console.log("Exercises received");
        displayQuestions(data.exercises); // Call function to show questions

    } catch (error) {
        console.error('Exercise generation error:', error);
        questionsContainer.textContent = `Error generating questions: ${error.message}`;
        questionsContainer.style.color = 'red';
    }
}

/**
 * Renders the questions received from the backend into the HTML.
 */
function displayQuestions(exercises) {
    console.log("Attempting to display questions:", exercises);
    questionsContainer.innerHTML = ''; // Clear previous content
    currentQuestions = exercises; // Store for submission reference

    if (!exercises || exercises.length === 0) {
        questionsContainer.innerHTML = 'No questions were generated, or an error occurred.';
        submitButton.classList.add('hidden');
        return;
    }

    const quizForm = document.createElement('form');
    quizForm.id = 'quiz-form';

    exercises.forEach((exercise, questionIndex) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question';
        questionDiv.dataset.questionId = exercise.id; // Store question ID

        const questionText = document.createElement('p');
        questionText.innerHTML = `<strong>${questionIndex + 1}.</strong> ${exercise.question_text}`;
        questionDiv.appendChild(questionText);

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'options';

        exercise.options.forEach((option, optionIndex) => {
            const optionId = `q${exercise.id}_option${optionIndex}`;
            const radioInput = document.createElement('input');
            radioInput.type = 'radio';
            radioInput.name = `question_${exercise.id}`; // Group radios by question
            radioInput.value = option;
            radioInput.id = optionId;

            const label = document.createElement('label');
            label.htmlFor = optionId;
            label.textContent = ` ${option}`; // Add space before label text

            const optionContainer = document.createElement('div');
            optionContainer.appendChild(radioInput);
            optionContainer.appendChild(label);
            optionsDiv.appendChild(optionContainer);
        });

        questionDiv.appendChild(optionsDiv);
        quizForm.appendChild(questionDiv);
    });

    questionsContainer.appendChild(quizForm);
    submitButton.classList.remove('hidden'); // Show submit button
}

/**
 * Handles the click on the "Submit Answers" button.
 */
async function handleSubmitAnswers() {
    console.log("Submitting answers...");
    resultsSection.innerHTML = 'Submitting...';
    resultsSection.style.color = 'black';

    const answers = [];
    const questionDivs = questionsContainer.querySelectorAll('.question'); // Get all question divs

    questionDivs.forEach(qDiv => {
        const questionId = parseInt(qDiv.dataset.questionId); // Get stored question ID
        const selectedOptionInput = qDiv.querySelector(`input[name="question_${questionId}"]:checked`); // Find checked radio within this question's div

        if (selectedOptionInput) {
            answers.push({
                question_id: questionId,
                selected_option: selectedOptionInput.value
            });
        } else {
            console.log(`Question ${questionId} was not answered.`);
            // Currently skips unanswered questions
        }
    });

    if (answers.length === 0 && questionDivs.length > 0) {
         resultsSection.textContent = 'Please answer at least one question.';
         resultsSection.style.color = 'orange';
         return;
    }

    // Prepare payload matching schemas.QuizSubmission
    const submissionPayload = {
        answers: answers
    };

    // Check if user is logged in
    if (!authToken) {
        resultsSection.textContent = 'ERROR: Not logged in. Cannot submit answers.';
        resultsSection.style.color = 'red';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/submit-answers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}` // Attach the token!
            },
            body: JSON.stringify(submissionPayload)
        });

        if (!response.ok) {
            let errorDetail = `Submission failed: ${response.status}`;
            try { errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
            throw new Error(errorDetail);
        }

        const resultData = await response.json(); // Should match schemas.QuizResult

        console.log("Submission successful:", resultData);
        displayResults(resultData); // Call function to show score

    } catch (error) {
        console.error('Submission error:', error);
        resultsSection.textContent = `Error submitting answers: ${error.message}`;
        resultsSection.style.color = 'red';
    }
}

/**
 * Displays the quiz results (score).
 */
function displayResults(result) {
    console.log("Displaying results:", result);
    if (result && typeof result.score !== 'undefined' && typeof result.total_questions !== 'undefined') {
         resultsSection.innerHTML = `<h3>Quiz Complete!</h3><p>Your score: ${result.score} / ${result.total_questions}</p>`;
         resultsSection.style.color = 'green';
    } else {
         resultsSection.textContent = 'Received invalid result format from server.';
         resultsSection.style.color = 'orange';
    }
    // Optionally hide the submit button again after submission?
    // submitButton.classList.add('hidden');
}

// --- Initialization ---
console.log("Script loaded. Waiting for user actions.");