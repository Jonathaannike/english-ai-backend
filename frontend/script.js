// script.js - FINAL VERSION (with Vocabulary Display)

// --- Configuration ---
const API_BASE_URL = 'http://127.0.0.1:8000'; // Just the URL string

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
const questionsContainer = document.getElementById('questions-container');
const submitButton = document.getElementById('submit-button');
const resultsSection = document.getElementById('results-section');
const passageContainer = document.getElementById('passage-container');
const translationTooltip = document.getElementById('translation-tooltip');
const loadLesson4Button = document.getElementById('load-lesson-4-button');
const loadLesson5Button = document.getElementById('load-lesson-5-button');
const loadLesson6Button = document.getElementById('load-lesson-6-button');
const lessonTitleElement = document.getElementById('lesson-title');
const vocabularyContainer = document.getElementById('vocabulary-container'); // Reference for vocab

// --- Event Listeners ---
loginForm.addEventListener('submit', handleLogin);
submitButton.addEventListener('click', handleSubmitAnswers);
loadLesson4Button.addEventListener('click', () => handleLoadLesson(11));
loadLesson5Button.addEventListener('click', () => handleLoadLesson(12));
loadLesson6Button.addEventListener('click', () => handleLoadLesson(13));
// Hover listeners are added dynamically in displayLesson

// --- Timer Variable ---
let hoverTimer = null;
const HOVER_DELAY = 500; // 0.5 seconds

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
            try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { console.log("Could not parse error response JSON."); }
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
 * Fetches a specific lesson from the backend by ID.
 */
async function handleLoadLesson(lessonId) {
    console.log(`Loading lesson ${lessonId}...`);
    // Clear all content areas
    lessonTitleElement.textContent = '';
    passageContainer.innerHTML = 'Loading lesson content...';
    passageContainer.style.color = 'black';
    vocabularyContainer.innerHTML = ''; // Clear vocab
    questionsContainer.innerHTML = ''; // Clear questions
    resultsSection.innerHTML = ''; // Clear results
    submitButton.classList.add('hidden'); // Hide submit button
    passageContainer.removeEventListener('mouseover', handleWordHover); // Clear old listeners
    passageContainer.removeEventListener('mouseout', handleWordOut);  // Clear old listeners

    if (!authToken) { // Check if logged in
        passageContainer.textContent = 'Please log in first.';
        passageContainer.style.color = 'orange';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/lessons/${lessonId}`, { method: 'GET' });
        if (!response.ok) {
            let errorDetail = `Failed to load lesson: ${response.status}`;
            try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { console.log("Could not parse error response JSON."); }
            throw new Error(errorDetail);
        }
        const lessonData = await response.json();
        console.log("Lesson data received:", lessonData);
        displayLesson(lessonData); // Call function to display all parts
    } catch (error) {
        console.error('Error loading lesson:', error);
        passageContainer.innerHTML = `Error loading lesson: ${error.message}`;
        passageContainer.style.color = 'red';
    }
}

/**
 * Displays the fetched lesson content (title, passage, vocab, questions).
 */
function displayLesson(lessonData) {
    // Display Title
    lessonTitleElement.textContent = lessonData.title || `Lesson ${lessonData.id || ''}`;

    // Display Passage with Translatable Words
    passageContainer.innerHTML = '';
    passageContainer.style.color = 'black';
    if (lessonData.text_passage) {
        const wordsAndPunctuation = lessonData.text_passage.match(/(\w+)|(\s+|[.,!?;:])/g);
        if (wordsAndPunctuation) {
            wordsAndPunctuation.forEach(item => {
                if (item.match(/^\w+$/)) { // Match only actual words
                    const wordSpan = document.createElement('span');
                    wordSpan.textContent = item;
                    wordSpan.className = 'translatable-word';
                    passageContainer.appendChild(wordSpan);
                } else {
                    passageContainer.appendChild(document.createTextNode(item));
                }
            });
            // Add hover listeners after spans are created
            passageContainer.addEventListener('mouseover', handleWordHover);
            passageContainer.addEventListener('mouseout', handleWordOut);
        } else {
             passageContainer.innerHTML = 'Could not process passage text.';
        }
    } else {
        passageContainer.innerHTML = 'Lesson passage is empty.';
    }

    // --- Display Vocabulary ---
    displayVocabulary(lessonData.vocabulary_items || []); // <<< CALL to display vocab

    // --- Display Comprehension Questions ---
    displayQuestions(lessonData.questions || []); // Pass questions or empty array
}

/**
 * Renders the vocabulary list into the HTML.
 */
function displayVocabulary(vocabularyItems) { // <<< ADDED this function
    console.log("Attempting to display vocabulary:", vocabularyItems);
    vocabularyContainer.innerHTML = ''; // Clear previous vocab

    if (!vocabularyItems || vocabularyItems.length === 0) {
        vocabularyContainer.innerHTML = '<p>No vocabulary items for this lesson.</p>';
        return;
    }

    const list = document.createElement('ul');
    list.style.listStyleType = 'none';
    list.style.paddingLeft = '0';

    vocabularyItems.forEach(item => {
        if (!item || !item.word) {
            console.warn("Skipping invalid vocabulary item:", item);
            return;
        }
        const listItem = document.createElement('li');
        listItem.style.marginBottom = '8px';

        let itemHTML = `<strong>${item.word}</strong>`;
        if (item.phonetic_guide) {
            itemHTML += ` - <i>[${item.phonetic_guide}]</i>`;
        }
        if (item.translation) {
             itemHTML += `: ${item.translation}`; // Display the translation
        }
        // Placeholder for audio button later:
        // itemHTML += ` <button class="vocab-audio-button" data-vocab-id="${item.id}">🔊</button>`;
        listItem.innerHTML = itemHTML;
        list.appendChild(listItem);
    });
    vocabularyContainer.appendChild(list);
}

/**
 * Renders the multiple-choice questions into the HTML.
 */
function displayQuestions(exercises) {
    console.log("Attempting to display questions:", exercises);
    questionsContainer.innerHTML = '';
    currentQuestions = exercises; // Store for submission check

    if (!exercises || exercises.length === 0) {
        questionsContainer.innerHTML = 'No comprehension questions for this lesson.';
        submitButton.classList.add('hidden');
        return;
    }

    const quizForm = document.createElement('form');
    quizForm.id = 'quiz-form';

    exercises.forEach((exercise, questionIndex) => {
        if (!exercise || typeof exercise.id === 'undefined' || !exercise.question_text || !Array.isArray(exercise.options)) {
             console.warn("Skipping invalid question data:", exercise);
             return;
        }
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question';
        questionDiv.dataset.questionId = exercise.id;

        const questionText = document.createElement('p');
        questionText.innerHTML = `<strong>${questionIndex + 1}.</strong> ${exercise.question_text}`;
        questionDiv.appendChild(questionText);

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'options';

        exercise.options.forEach((option, optionIndex) => {
            const optionId = `q${exercise.id}_option${optionIndex}`;
            const radioInput = document.createElement('input');
            radioInput.type = 'radio';
            radioInput.name = `question_${exercise.id}`;
            radioInput.value = option;
            radioInput.id = optionId;

            const label = document.createElement('label');
            label.htmlFor = optionId;
            label.textContent = ` ${option}`;

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
 * Handles mouse moving OVER a word span. Starts the timer for translation.
 */
function handleWordHover(event) {
    if (event.target.classList.contains('translatable-word')) {
        const wordElement = event.target;
        const word = wordElement.textContent.trim().toLowerCase().replace(/[.,!?;:]$/, '');
        if (!word || word.length <= 1 || !isNaN(word)) return;

        clearTimeout(hoverTimer);
        translationTooltip.style.display = 'none';
        hoverTimer = setTimeout(() => { showTranslation(word, wordElement); }, HOVER_DELAY);
    }
}

/**
 * Handles mouse moving OUT of a word span. Clears the timer, hides tooltip.
 */
function handleWordOut(event) {
    if (event.target.classList.contains('translatable-word')) {
        clearTimeout(hoverTimer);
        translationTooltip.style.display = 'none';
    }
}

/**
 * Fetches translation using Gemini via backend and displays it in a tooltip.
 */
async function showTranslation(word, element) {
    console.log(`Requesting translation for: ${word}`);
    const rect = element.getBoundingClientRect();
    translationTooltip.textContent = 'Translating...';
    translationTooltip.style.left = `${rect.left + window.scrollX}px`;
    translationTooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;
    translationTooltip.style.display = 'block';

    try {
        const response = await fetch(`${API_BASE_URL}/translate?word=${encodeURIComponent(word)}&target_language=es`);
        if (!response.ok) {
            let errorDetail = `Translation failed: ${response.status}`;
             try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
            throw new Error(errorDetail);
        }
        const data = await response.json(); // Expects RichTranslationResponse
        let tooltipContent = '';
        if (data.primary_translation) {
             tooltipContent = `<strong>${data.primary_translation}</strong>`;
             if (data.part_of_speech) { tooltipContent += ` <i>(${data.part_of_speech})</i>`; }
             if (data.other_meanings && data.other_meanings.length > 0) {
                 tooltipContent += `<br><small>Others: ${data.other_meanings.join(', ')}</small>`;
             }
        } else { tooltipContent = 'Not found.'; }

        translationTooltip.innerHTML = tooltipContent; // Use innerHTML for tags
        translationTooltip.style.display = 'block';
    } catch (error) {
        console.error("Translation fetch error:", error);
        translationTooltip.textContent = `Error`;
        translationTooltip.style.display = 'block';
    }
}


/**
 * Handles the click on the "Submit Answers" button for the quiz.
 */
async function handleSubmitAnswers() {
    console.log("Submitting answers...");
    resultsSection.innerHTML = 'Submitting...';
    resultsSection.style.color = 'black';

    const answers = [];
    const questionDivs = questionsContainer.querySelectorAll('.question');

    questionDivs.forEach(qDiv => {
        const questionId = parseInt(qDiv.dataset.questionId);
        const selectedOptionInput = qDiv.querySelector(`input[name="question_${questionId}"]:checked`);
        if (selectedOptionInput) {
            answers.push({ question_id: questionId, selected_option: selectedOptionInput.value });
        } else {
            console.log(`Question ${questionId} was not answered.`);
        }
    });

    if (answers.length === 0 && questionDivs.length > 0) {
         resultsSection.textContent = 'Please answer at least one question.';
         resultsSection.style.color = 'orange';
         return;
    }

    const submissionPayload = { answers: answers };

    if (!authToken) { // Check login status
        resultsSection.textContent = 'ERROR: Not logged in.';
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
            try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
            throw new Error(errorDetail);
        }
        const resultData = await response.json();
        console.log("Submission successful:", resultData);
        displayResults(resultData); // Show score
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
         resultsSection.textContent = 'Received invalid result format.';
         resultsSection.style.color = 'orange';
    }
    // submitButton.classList.add('hidden'); // Optional: hide after submit
}

// --- Initialization ---
console.log("Script loaded. Waiting for user actions.");