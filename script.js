const screens = document.querySelectorAll(".screen");
const navItems = document.querySelectorAll(".nav-item");
const promptChips = document.querySelectorAll(".prompt-chip");
const chatBoard = document.getElementById("chat");
const chatInput = document.getElementById("input");
const notesInput = document.getElementById("notesInput");
const notesOutput = document.getElementById("notesOutput");
const quizInput = document.getElementById("quizInput");
const quizCountInput = document.getElementById("quizCountInput");
const quizModeInput = document.getElementById("quizModeInput");
const quizDifficultyInput = document.getElementById("quizDifficultyInput");
const quizPdfFileInput = document.getElementById("quizPdfFile");
const quizOutput = document.getElementById("quizOutput");
const scoreOutput = document.getElementById("scoreOutput");
const assignmentInput = document.getElementById("assignmentInput");
const assignmentLevelInput = document.getElementById("assignmentLevelInput");
const assignmentQuestionCountInput = document.getElementById("assignmentQuestionCountInput");
const assignmentSourceFileInput = document.getElementById("assignmentSourceFile");
const assignmentOutput = document.getElementById("assignmentOutput");
const libraryTitleInput = document.getElementById("libraryTitleInput");
const libraryBoardInput = document.getElementById("libraryBoardInput");
const libraryClassInput = document.getElementById("libraryClassInput");
const librarySubjectInput = document.getElementById("librarySubjectInput");
const libraryTypeInput = document.getElementById("libraryTypeInput");
const libraryFileInput = document.getElementById("libraryFileInput");
const librarySearchInput = document.getElementById("librarySearchInput");
const libraryFilterSubject = document.getElementById("libraryFilterSubject");
const libraryFilterBoard = document.getElementById("libraryFilterBoard");
const libraryFilterClass = document.getElementById("libraryFilterClass");
const libraryFilterType = document.getElementById("libraryFilterType");
const libraryList = document.getElementById("libraryList");
const libraryReader = document.getElementById("libraryReader");
const librarySessionTabs = document.querySelectorAll(".library-session-tab");
const librarySessions = document.querySelectorAll(".library-session");
const ytLinkInput = document.getElementById("ytLink");
const ytQuizCountInput = document.getElementById("ytQuizCountInput");
const ytTranscriptInput = document.getElementById("ytTranscript");
const ytOutput = document.getElementById("ytOutput");
const videoCard = document.getElementById("videoCard");
const pdfFileInput = document.getElementById("pdfFile");
const voiceBtn = document.getElementById("voiceBtn");
const speakToggleBtn = document.getElementById("speakToggleBtn");
const menuToggleBtn = document.getElementById("menuToggleBtn");
const featureMenu = document.getElementById("featureMenu");
const currentScreenLabel = document.getElementById("currentScreenLabel");
const composerMenuBtn = document.getElementById("composerMenuBtn");
const composerMenu = document.getElementById("composerMenu");
const openTeachPanelBtn = document.getElementById("openTeachPanelBtn");
const closeTeachPanelBtn = document.getElementById("closeTeachPanelBtn");
const teachPanel = document.getElementById("teachPanel");
const teachQuestionLabel = document.getElementById("teachQuestionLabel");
const teachAnswerInput = document.getElementById("teachAnswerInput");
const saveTeachBtn = document.getElementById("saveTeachBtn");
const languageSelect = document.getElementById("languageSelect");
const replyModeSelect = document.getElementById("replyModeSelect");
const apiStatusPill = document.getElementById("apiStatusPill");
const HISTORY_KEY = "quadratutor_history_v1";
const HISTORY_LOG_KEY = "quadratutor_activity_log_v1";
const historyList = document.getElementById("historyList");

let generatedQuiz = [];
let latestNotesPayload = null;
let latestYtNotesPayload = null;
let latestAssignmentPayload = null;
let latestLibraryItems = [];
let botVoiceEnabled = true;
let lastAskedQuestion = "";

navItems.forEach((item) => {
    item.addEventListener("click", () => {
        switchScreen(item.dataset.screen);
        closeFeatureMenu();
    });
});

promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
        const screenTarget = chip.dataset.screenTarget;
        const prompt = chip.dataset.prompt;
        if (screenTarget) {
            switchScreen(screenTarget);
            return;
        }
        if (prompt) {
            chatInput.value = prompt;
            chatInput.focus();
        }
    });
});

document.getElementById("sendBtn").addEventListener("click", sendMessage);
voiceBtn.addEventListener("click", startVoice);
speakToggleBtn.addEventListener("click", toggleBotVoice);
document.getElementById("clearChatBtn").addEventListener("click", clearChat);
document.getElementById("generateNotesBtn").addEventListener("click", generateNotes);
document.getElementById("downloadNotesPdfBtn").addEventListener("click", () => downloadNotesPdf(latestNotesPayload));
document.getElementById("generateQuizBtn").addEventListener("click", generateQuiz);
document.getElementById("generateQuizFromPdfBtn").addEventListener("click", generateQuizFromPdf);
document.getElementById("checkQuizBtn").addEventListener("click", checkAnswers);
document.getElementById("clearQuizBtn").addEventListener("click", clearQuiz);
document.getElementById("generateAssignmentBtn").addEventListener("click", generateAssignment);
document.getElementById("downloadAssignmentPdfBtn").addEventListener("click", downloadAssignmentPdf);
document.getElementById("generateAssignmentQuestionsBtn").addEventListener("click", generateAssignmentQuestionsFromUpload);
document.getElementById("libraryUploadBtn").addEventListener("click", uploadLibraryItem);
document.getElementById("librarySearchBtn").addEventListener("click", fetchLibraryItems);
document.getElementById("libraryResetBtn").addEventListener("click", resetLibraryFilters);
libraryList.addEventListener("click", handleLibraryListClick);
librarySessionTabs.forEach((tab) => {
    tab.addEventListener("click", () => switchLibrarySession(tab.dataset.librarySession));
});
document.getElementById("ytTranscriptBtn").addEventListener("click", getYTTranscript);
document.getElementById("ytQuizBtn").addEventListener("click", generateYTQuiz);
document.getElementById("downloadYtPdfBtn").addEventListener("click", () => downloadNotesPdf(latestYtNotesPayload));
document.getElementById("simplifyPdfBtn").addEventListener("click", simplifyPdfNotes);
document.getElementById("clearHistoryBtn").addEventListener("click", clearActivityHistory);
historyList.addEventListener("click", handleHistoryClick);
menuToggleBtn.addEventListener("click", toggleFeatureMenu);
composerMenuBtn.addEventListener("click", toggleComposerMenu);
openTeachPanelBtn.addEventListener("click", openTeachPanel);
closeTeachPanelBtn.addEventListener("click", closeTeachPanel);
saveTeachBtn.addEventListener("click", saveTeachAnswer);
document.addEventListener("keydown", handleMenuEscape);
restoreHistory();
fetchLibraryItems();

chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        sendMessage();
    }
});

function switchScreen(screenId) {
    screens.forEach((screen) => screen.classList.remove("active"));
    navItems.forEach((item) => item.classList.remove("active"));
    const nextScreen = document.getElementById(screenId) || document.getElementById("chatScreen");
    const nextNavItem = document.querySelector(`[data-screen="${nextScreen.id}"]`);
    if (!nextScreen || !nextNavItem) {
        return;
    }
    nextScreen.classList.add("active");
    nextNavItem.classList.add("active");
    currentScreenLabel.textContent = nextNavItem.textContent.trim();
    persistHistory();
}

function toggleFeatureMenu(event) {
    event.stopPropagation();
    const isHidden = featureMenu.hasAttribute("hidden");
    if (isHidden) {
        featureMenu.removeAttribute("hidden");
        menuToggleBtn.setAttribute("aria-expanded", "true");
    } else {
        closeFeatureMenu();
    }
}

function closeFeatureMenu() {
    featureMenu.setAttribute("hidden", "");
    menuToggleBtn.setAttribute("aria-expanded", "false");
}

function toggleComposerMenu(event) {
    event.stopPropagation();
    const isHidden = composerMenu.hasAttribute("hidden");
    if (isHidden) {
        composerMenu.removeAttribute("hidden");
        composerMenuBtn.setAttribute("aria-expanded", "true");
    } else {
        closeComposerMenu();
    }
}

function closeComposerMenu() {
    composerMenu.setAttribute("hidden", "");
    composerMenuBtn.setAttribute("aria-expanded", "false");
}

function handleMenuEscape(event) {
    if (event.key === "Escape") {
        closeFeatureMenu();
        closeComposerMenu();
    }
}

function createMessage(text, type) {
    const article = document.createElement("article");
    article.className = `message ${type}`;

    const label = document.createElement("span");
    label.className = "message-role";
    label.textContent = type === "user" ? "You" : "Quadratutor";

    const body = document.createElement("p");
    const messageText = typeof text === "string" ? text : formatChatMessageText(text);
    body.textContent = messageText;

    article.append(label, body);
    chatBoard.appendChild(article);
    chatBoard.scrollTop = chatBoard.scrollHeight;

    if (type === "bot" && botVoiceEnabled && replyModeSelect.value !== "text") {
        speakText(text);
    }

    persistHistory();
}

async function fetchApiStatus() {
    if (!apiStatusPill) {
        return;
    }

    try {
        const response = await fetch("/api-status", { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Status route failed: ${response.status}`);
        }
        const data = await response.json();
        const connected = Boolean(data.openai_connected);
        apiStatusPill.textContent = connected
            ? `Gemini Connected · ${data.gemini_model || "gemini-1.5-flash"}`
            : "Gemini Not Connected";
        apiStatusPill.classList.toggle("status-online", connected);
        apiStatusPill.classList.toggle("status-offline", !connected);
    } catch (_error) {
        apiStatusPill.textContent = "Restart app to check OpenAI";
        apiStatusPill.classList.remove("status-online");
        apiStatusPill.classList.add("status-offline");
    }
}

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) {
        return;
    }

    lastAskedQuestion = message;
    createMessage(message, "user");
    chatInput.value = "";
    await requestTutorReply(message);
}

async function requestTutorReply(message) {
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                language: languageSelect.value,
                reply_mode: replyModeSelect.value
            })
        });

        const data = await response.json();
        createMessage(data.response || "No response received.", "bot");
        persistHistory();
        logActivity("Chat", `${message}\n\nAnswer: ${typeof data.response === "string" ? data.response : formatChatMessageText(data.response)}`);
    } catch (_error) {
        createMessage("Connection problem. Please try again.", "bot");
    }
}

function openTeachPanel() {
    if (!lastAskedQuestion) {
        createMessage("Ask a question first, then teach the correct answer.", "bot");
        return;
    }

    teachQuestionLabel.textContent = `Question: ${lastAskedQuestion}`;
    teachPanel.removeAttribute("hidden");
    teachAnswerInput.focus();
    closeComposerMenu();
    persistHistory();
}

function closeTeachPanel() {
    teachPanel.setAttribute("hidden", "");
    teachAnswerInput.value = "";
    persistHistory();
}

async function saveTeachAnswer() {
    const answer = teachAnswerInput.value.trim();
    if (!lastAskedQuestion) {
        createMessage("No question found to teach right now.", "bot");
        return;
    }
    if (!answer) {
        createMessage("Please type the correct answer before saving.", "bot");
        return;
    }

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                teach_question: lastAskedQuestion,
                teach_answer: answer,
                language: languageSelect.value
            })
        });

        const data = await response.json();
        createMessage(data.response || "Answer saved.", "bot");
        logActivity("Teach Answer", `${lastAskedQuestion}\n\nSaved Answer: ${answer}`);
        closeTeachPanel();
    } catch (_error) {
        createMessage("Unable to save the taught answer right now.", "bot");
    }
}

function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        createMessage("Voice input is not supported in this browser.", "bot");
        return;
    }

    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
        createMessage("Voice input ke liye app ko localhost ya HTTPS par chalana zaroori hai.", "bot");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = getSpeechLang();
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    const targetInput = chatInput;
    const triggerButton = voiceBtn;
    triggerButton.textContent = "Listening...";
    triggerButton.disabled = true;
    recognition.onstart = () => {
        targetInput.placeholder = "Listening... boliye";
    };

    recognition.onresult = (event) => {
        let transcript = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
            transcript += event.results[index][0].transcript;
        }
        targetInput.value = transcript.trim();
    };

    recognition.onerror = (event) => {
        let message = "Voice input failed. Please try again.";
        if (event.error === "not-allowed") {
            message = "Microphone permission blocked. Browser me mic allow karke phir try karo.";
        } else if (event.error === "service-not-allowed") {
            message = "Browser ne speech service allow nahi ki. Chrome ya Edge me localhost par try karo.";
        } else if (event.error === "no-speech") {
            message = "Koi voice detect nahi hui. Thoda clearly bolkar phir try karo.";
        } else if (event.error === "audio-capture") {
            message = "Microphone detect nahi ho raha. Mic connect ya select karke phir try karo.";
        } else if (event.error === "network") {
            message = "Speech recognition network issue aaya. Internet aur browser access check karo.";
        }
        createMessage(message, "bot");
    };

    recognition.onend = () => {
        triggerButton.textContent = "Voice";
        triggerButton.disabled = false;
        targetInput.placeholder = "Ask your question here";
        targetInput.focus();
    };

    recognition.start();
}

function clearChat() {
    chatBoard.innerHTML = "";
    lastAskedQuestion = "";
    closeTeachPanel();
    createMessage("Chat cleared. Start a new study session anytime.", "bot");
    persistHistory();
}

function toggleBotVoice() {
    botVoiceEnabled = !botVoiceEnabled;
    const label = botVoiceEnabled ? "Voice Reply On" : "Voice Reply Off";
    speakToggleBtn.textContent = label;
    if (!botVoiceEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
    persistHistory();
}

function speakText(text) {
    if (!("speechSynthesis" in window)) {
        return;
    }

    window.speechSynthesis.cancel();
    const simplified = typeof text === "string"
        ? String(text)
        .replace("Teacher Explanation:", "Teacher bol raha hai.")
        .replace("Blackboard Notes:", "Board notes.")
        .replace("Handwritten Steps:", "Handwritten steps.")
        .replace("Answer Styles:", "Answer styles.")
        .replace("3. Key points:", "Key points.")
        .replace("3. मुख्य बिंदु:", "Mukhya bindu.")
        .replace(/\|/g, ". ")
        .replace(/\n+/g, ". ")
        : buildVoiceNarration(text);
    const utterance = new SpeechSynthesisUtterance(simplified);
    utterance.lang = getSpeechLang();
    utterance.rate = 0.92;
    window.speechSynthesis.speak(utterance);
}

function getSpeechLang() {
    if (languageSelect.value === "hindi") {
        return "hi-IN";
    }
    if (languageSelect.value === "english") {
        return "en-US";
    }
    return "en-IN";
}

function formatStructuredText(payload) {
    const parts = [];
    if (payload.title) {
        parts.push(payload.title);
    }
    (payload.steps || []).forEach((item) => {
        parts.push(item.text);
    });
    if ((payload.notes || []).length) {
        parts.push("Notes:");
        payload.notes.forEach((note) => parts.push(`- ${note}`));
    }
    if ((payload.quiz || []).length) {
        parts.push("Quiz:");
        payload.quiz.forEach((item, index) => parts.push(`Q${index + 1}: ${item.question}`));
    }
    if (payload.final_answer) {
        parts.push(`Final Answer: ${payload.final_answer}`);
    }
    return parts.join("\n");
}

function formatChatMessageText(payload) {
    if (payload.final_answer) {
        return payload.final_answer;
    }
    if ((payload.notes || []).length) {
        return ["Key Points:", ...(payload.notes || []).map((note) => `- ${note}`)].join("\n");
    }
    if ((payload.quiz || []).length) {
        return `Quiz ready: ${(payload.quiz || []).length} questions generated.`;
    }
    if ((payload.steps || []).length) {
        const firstStep = payload.steps.find((item) => item.text && !String(item.text).startsWith("Step"));
        return firstStep?.text || payload.steps[0].text;
    }
    return formatStructuredText(payload);
}

function buildVoiceNarration(payload) {
    const voices = (payload.steps || []).map((item) => item.voice).filter(Boolean);
    if (voices.length) {
        return voices.join(". ");
    }
    if (payload.final_answer) {
        return `Final answer ye hai. ${payload.final_answer}`;
    }
    return formatStructuredText(payload);
}

async function generateNotes() {
    const text = notesInput.value.trim();
    if (!text) {
        renderMessageState(notesOutput, "Please paste study content first.");
        return;
    }

    renderMessageState(notesOutput, "Creating proper hand-written style notes...");

    try {
        const response = await fetch("/generate-notes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        latestNotesPayload = data;
        renderNotesPayload(notesOutput, data);
        persistHistory();
        logActivity("Notes", text.slice(0, 120));
    } catch (_error) {
        renderMessageState(notesOutput, "Unable to generate notes right now.");
        persistHistory();
    }
}

async function simplifyPdfNotes() {
    const file = pdfFileInput.files[0];
    if (!file) {
        renderMessageState(notesOutput, "Please choose a PDF file first.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    renderMessageState(notesOutput, "Reading PDF and simplifying complex notes...");

    try {
        const response = await fetch("/simplify-notes", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(notesOutput, data.error || "Could not process the PDF.");
            return;
        }

        latestNotesPayload = data;
        renderNotesPayload(notesOutput, data, `Source: ${data.source}`);
        quizInput.value = data.source_text || "";
        generatedQuiz = data.quiz?.items || [];
        if (generatedQuiz.length) {
            renderQuizPayload(quizOutput, generatedQuiz);
            scoreOutput.textContent = `Score: 0/${generatedQuiz.length}`;
        }
        persistHistory();
        logActivity("PDF Notes", data.source || "PDF upload");
    } catch (_error) {
        renderMessageState(notesOutput, "Unable to process the PDF right now.");
        persistHistory();
    }
}

async function generateQuiz() {
    const text = quizInput.value.trim() || notesInput.value.trim();
    const requestedCount = quizCountInput.value.trim();
    const quizMode = quizModeInput.value;
    const difficulty = quizDifficultyInput.value;
    if (!text) {
        renderMessageState(quizOutput, "Please paste notes or study content first to generate quiz questions.");
        scoreOutput.textContent = "Score: 0/0";
        return;
    }

    if (!quizInput.value.trim()) {
        quizInput.value = text;
    }

    renderMessageState(quizOutput, "Generating quiz...");

    try {
        const response = await fetch("/generate-quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, count: requestedCount, quiz_mode: quizMode, difficulty })
        });
        const data = await response.json();
        generatedQuiz = data.items || [];
        renderQuizPayload(quizOutput, generatedQuiz);
        scoreOutput.textContent = `Score: 0/${generatedQuiz.length}`;
        persistHistory();
        logActivity("Quiz", text.slice(0, 120));
    } catch (_error) {
        renderMessageState(quizOutput, "Unable to generate quiz right now.");
        scoreOutput.textContent = "Score: 0/0";
        persistHistory();
    }
}

async function generateQuizFromPdf() {
    const file = quizPdfFileInput.files[0];
    const requestedCount = quizCountInput.value.trim();
    const quizMode = quizModeInput.value;
    const difficulty = quizDifficultyInput.value;
    if (!file) {
        renderMessageState(quizOutput, "Please choose a PDF file first.");
        scoreOutput.textContent = "Score: 0/0";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("count", requestedCount);
    formData.append("quiz_mode", quizMode);
    formData.append("difficulty", difficulty);
    renderMessageState(quizOutput, "Reading PDF and generating quiz...");

    try {
        const response = await fetch("/generate-quiz-upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(quizOutput, data.error || "Unable to generate quiz from PDF.");
            scoreOutput.textContent = "Score: 0/0";
            return;
        }

        quizInput.value = data.source_text || "";
        generatedQuiz = data.items || [];
        renderQuizPayload(quizOutput, generatedQuiz);
        scoreOutput.textContent = `Score: 0/${generatedQuiz.length}`;
        persistHistory();
        logActivity("PDF Quiz", data.source || "PDF upload");
    } catch (_error) {
        renderMessageState(quizOutput, "Unable to generate quiz from PDF right now.");
        scoreOutput.textContent = "Score: 0/0";
        persistHistory();
    }
}

function clearQuiz() {
    quizInput.value = "";
    quizPdfFileInput.value = "";
    generatedQuiz = [];
    quizCountInput.value = "5";
    quizModeInput.value = "mixed";
    quizDifficultyInput.value = "medium";
    quizOutput.className = "result-panel empty-state";
    quizOutput.innerHTML = "Generated quiz questions will appear here.";
    scoreOutput.textContent = "Score: 0/0";
    persistHistory();
    logActivity("Quiz Cleared", "Quiz input, upload, and output cleared.");
}

async function generateAssignment() {
    const text = assignmentInput.value.trim();
    const level = assignmentLevelInput.value;
    if (!text) {
        renderMessageState(assignmentOutput, "Please paste assignment questions first.");
        return;
    }

    renderMessageState(assignmentOutput, "Generating assignment answers in notebook style...");

    try {
        const response = await fetch("/generate-assignment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, level })
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(assignmentOutput, data.error || "Unable to generate assignment right now.");
            return;
        }

        latestAssignmentPayload = data;
        renderAssignmentPayload(assignmentOutput, data);
        persistHistory();
        logActivity("Assignment", text.slice(0, 120));
    } catch (_error) {
        renderMessageState(assignmentOutput, "Unable to generate assignment right now.");
        persistHistory();
    }
}

async function generateAssignmentQuestionsFromUpload() {
    const file = assignmentSourceFileInput.files[0];
    const level = assignmentLevelInput.value;
    const count = assignmentQuestionCountInput.value.trim() || "5";
    if (!file) {
        renderMessageState(assignmentOutput, "Please upload syllabus or notes first.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("level", level);
    formData.append("count", count);
    renderMessageState(assignmentOutput, "Reading uploaded file and creating assignment questions...");

    try {
        const response = await fetch("/generate-assignment-questions-upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(assignmentOutput, data.error || "Unable to generate assignment questions.");
            return;
        }

        assignmentInput.value = data.formatted_questions || "";
        assignmentOutput.className = "result-panel";
        assignmentOutput.innerHTML = `
            <div class="assignment-preview">
                <article class="assignment-sheet">
                    <div class="assignment-rule assignment-margin"></div>
                    <div class="assignment-lines">
                        <h4>Generated Questions</h4>
                        <p><strong>Source:</strong> ${escapeHTML(data.source || "Uploaded file")}</p>
                        <p><strong>Summary:</strong><br>${escapeHTML(data.summary || "")}</p>
                        ${(data.questions || []).map((question, index) => `
                            <p><strong>Q${index + 1}.</strong> ${escapeHTML(question)}</p>
                        `).join("")}
                    </div>
                </article>
            </div>
        `;
        persistHistory();
        logActivity("Assignment Questions", data.source || "Uploaded syllabus/notes");
    } catch (_error) {
        renderMessageState(assignmentOutput, "Unable to generate assignment questions right now.");
    }
}


function checkAnswers() {
    if (!generatedQuiz.length) {
        scoreOutput.textContent = "Score: 0/0";
        return;
    }

    let score = 0;

    generatedQuiz.forEach((item, index) => {
        const selected = document.querySelector(`input[name="quiz-${index}"]:checked`);
        const answerBox = document.getElementById(`answer-${index}`);
        const isCorrect = selected && selected.value === item.answer;

        if (isCorrect) {
            score += 1;
        }

        answerBox.hidden = false;
        answerBox.textContent = `Correct answer: ${item.answer}`;
        answerBox.style.color = isCorrect ? "var(--success)" : "#d14343";
    });

    scoreOutput.textContent = `Score: ${score}/${generatedQuiz.length}`;
    persistHistory();
    logActivity("Quiz Score", scoreOutput.textContent);
}

async function getYTTranscript() {
    const link = ytLinkInput.value.trim();
    updateVideoCard(link);

    if (!link) {
        renderMessageState(ytOutput, "Please paste a YouTube link first.");
        return;
    }

    renderMessageState(ytOutput, "Fetching transcript from video...");

    try {
        const response = await fetch("/youtube-transcript", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: link })
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(ytOutput, data.error || "Unable to fetch transcript.");
            return;
        }

        ytTranscriptInput.value = data.transcript_text || "";
        ytOutput.classList.remove("empty-state");
        ytOutput.innerHTML = `
            <div class="mindmap-shell">
                <div class="mindmap-meta">
                    <strong>${escapeHTML(data.message || "Transcript fetched successfully.")}</strong>
                </div>
                <div class="video-card">
                    <div class="video-meta">
                        <h4>${escapeHTML(data.title || "YouTube Transcript")}</h4>
                        <p>${escapeHTML(data.source_used === "transcript" ? "Real transcript loaded from the video." : "Transcript unavailable, title and description were used instead.")}</p>
                    </div>
                    <div class="assignment-lines">
                        <p>${escapeHTML(data.transcript_text || "No transcript text found.")}</p>
                    </div>
                </div>
            </div>
        `;
        persistHistory();
        logActivity("YouTube Transcript", link);
    } catch (_error) {
        renderMessageState(ytOutput, "Unable to fetch transcript right now.");
        persistHistory();
    }
}

async function generateYTQuiz() {
    const link = ytLinkInput.value.trim();
    const transcript = ytTranscriptInput.value.trim();
    const count = ytQuizCountInput.value.trim() || "5";
    updateVideoCard(link);

    if (!link && !transcript) {
        renderMessageState(ytOutput, "Please paste a YouTube link or transcript first.");
        return;
    }

    renderMessageState(ytOutput, "Generating video-based quiz...");

    try {
        const response = await fetch("/youtube-study", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link, transcript, mode: "quiz", count })
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(ytOutput, data.error || "Unable to generate YouTube quiz.");
            return;
        }

        renderQuizPayload(ytOutput, data.items || [], true);
        ytOutput.insertAdjacentHTML("afterbegin", `<p><strong>${escapeHTML(`Generated ${data.items?.length || 0} quiz questions from the video content.`)}</strong></p>`);
        persistHistory();
        logActivity("YouTube Quiz", link || transcript.slice(0, 80));
    } catch (_error) {
        renderMessageState(ytOutput, "Unable to generate YouTube quiz right now.");
        persistHistory();
    }
}

async function downloadAssignmentPdf() {
    const text = assignmentInput.value.trim();
    const level = assignmentLevelInput.value;
    if (!latestAssignmentPayload?.items?.length && !text) {
        renderMessageState(assignmentOutput, "Please generate the assignment first.");
        return;
    }

    try {
        const response = await fetch("/download-assignment-pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text,
                items: latestAssignmentPayload?.items || [],
                level
            })
        });

        if (!response.ok) {
            const data = await response.json();
            renderMessageState(assignmentOutput, data.error || "Assignment PDF download failed.");
            return;
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "assignment.pdf";
        anchor.click();
        URL.revokeObjectURL(url);
    } catch (_error) {
        renderMessageState(assignmentOutput, "Assignment PDF download failed. Please try again.");
    }
}

async function uploadLibraryItem() {
    const file = libraryFileInput.files[0];
    if (!file) {
        renderMessageState(libraryList, "Please choose a file before uploading.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", libraryTitleInput.value.trim());
    formData.append("board", libraryBoardInput.value.trim());
    formData.append("class_level", libraryClassInput.value.trim());
    formData.append("subject", librarySubjectInput.value.trim());
    formData.append("material_type", libraryTypeInput.value);

    renderMessageState(libraryList, "Uploading file to library...");

    try {
        const response = await fetch("/library/upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            renderMessageState(libraryList, data.error || "Upload failed.");
            return;
        }

        libraryFileInput.value = "";
        libraryTitleInput.value = "";
        libraryBoardInput.value = "";
        libraryClassInput.value = "";
        librarySubjectInput.value = "";
        libraryTypeInput.value = "Notes";
        await fetchLibraryItems();
        switchLibrarySession("accessSession");
        openLibraryReader(data.item);
        logActivity("Library Upload", `${data.item.title} | ${data.item.subject}`);
    } catch (_error) {
        renderMessageState(libraryList, "Unable to upload file right now.");
    }
}

async function fetchLibraryItems() {
    const params = new URLSearchParams({
        search: librarySearchInput.value.trim(),
        subject: libraryFilterSubject.value.trim(),
        board: libraryFilterBoard.value.trim(),
        class_level: libraryFilterClass.value.trim(),
        material_type: libraryFilterType.value
    });

    try {
        const response = await fetch(`/library/items?${params.toString()}`);
        const data = await response.json();
        latestLibraryItems = data.items || [];
        renderLibraryList(latestLibraryItems);
        persistHistory();
    } catch (_error) {
        renderMessageState(libraryList, "Unable to load library right now.");
    }
}

function resetLibraryFilters() {
    librarySearchInput.value = "";
    libraryFilterSubject.value = "";
    libraryFilterBoard.value = "";
    libraryFilterClass.value = "";
    libraryFilterType.value = "";
    fetchLibraryItems();
}

function switchLibrarySession(sessionId) {
    librarySessionTabs.forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.librarySession === sessionId);
    });
    librarySessions.forEach((section) => {
        section.classList.toggle("active", section.id === sessionId);
    });
    persistHistory();
}

function renderLibraryList(items) {
    if (!items.length) {
        renderMessageState(libraryList, "No files found for the selected board, class, subject, or search.");
        return;
    }

    const html = items.map((item) => `
        <article class="library-card" data-library-id="${escapeAttribute(item.id)}">
            <div class="library-card-top">
                <div>
                    <h4>${escapeHTML(item.title)}</h4>
                    <p>${escapeHTML(item.board)} | ${escapeHTML(item.class_level)} | ${escapeHTML(item.subject)}</p>
                </div>
                <span class="library-badge">${escapeHTML(item.material_type)}</span>
            </div>
            <p>${escapeHTML(item.filename)}</p>
            <div class="library-card-actions">
                <button class="ghost-button compact-button" type="button" data-action="read" data-library-id="${escapeAttribute(item.id)}">Read</button>
                <a class="library-link-button" href="${escapeAttribute(item.download_url)}">Download</a>
            </div>
        </article>
    `).join("");

    libraryList.classList.remove("empty-state");
    libraryList.innerHTML = html;
}

function handleLibraryListClick(event) {
    const actionTarget = event.target.closest("[data-action='read']");
    if (!actionTarget) {
        return;
    }

    const itemId = actionTarget.dataset.libraryId;
    const item = latestLibraryItems.find((entry) => entry.id === itemId);
    if (item) {
        openLibraryReader(item);
    }
}

function openLibraryReader(item) {
    switchLibrarySession("accessSession");
    const extension = String(item.extension || "").toLowerCase();
    let previewHtml = `
        <div class="library-reader-head">
            <div>
                <h4>${escapeHTML(item.title)}</h4>
                <p>${escapeHTML(item.board)} | ${escapeHTML(item.class_level)} | ${escapeHTML(item.subject)} | ${escapeHTML(item.material_type)}</p>
            </div>
            <a class="library-link-button" href="${escapeAttribute(item.download_url)}">Download</a>
        </div>
    `;

    if ([".png", ".jpg", ".jpeg", ".webp"].includes(extension)) {
        previewHtml += `<img class="library-preview-image" src="${escapeAttribute(item.preview_url)}" alt="${escapeAttribute(item.title)}">`;
    } else if ([".pdf", ".txt"].includes(extension)) {
        previewHtml += `<iframe class="library-frame" src="${escapeAttribute(item.preview_url)}" title="${escapeAttribute(item.title)}"></iframe>`;
    } else {
        previewHtml += `
            <div class="library-reader-empty">
                <p>Preview is not available for this file type. You can still download and read it.</p>
            </div>
        `;
    }

    libraryReader.classList.remove("empty-state");
    libraryReader.innerHTML = previewHtml;
    persistHistory();
}

async function downloadNotesPdf(payload) {
    if (!payload || !payload.sections?.length) {
        return;
    }

    try {
        const response = await fetch("/download-notes-pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "quadratutor-notes.pdf";
        anchor.click();
        URL.revokeObjectURL(url);
    } catch (_error) {
        createMessage("PDF download failed. Please try again.", "bot");
    }
}

function renderNotesPayload(element, payload, metaLine = "") {
    const sections = payload.sections || [];
    const html = `
        <h4>${escapeHTML(payload.title || "Notes")}</h4>
        ${metaLine ? `<p><strong>${escapeHTML(metaLine)}</strong></p>` : ""}
        <p>${escapeHTML(payload.overview || "")}</p>
        ${sections.map((section) => `
            <div class="quiz-card">
                <h4>${escapeHTML(section.heading)}</h4>
                <ul class="notes-list">
                    ${(section.bullets || []).map((bullet) => `<li>${escapeHTML(bullet)}</li>`).join("")}
                </ul>
            </div>
        `).join("")}
        <p><strong>Keywords:</strong> ${escapeHTML((payload.keywords || []).join(", ") || "No keywords found")}</p>
    `;

    element.classList.remove("empty-state");
    element.innerHTML = html;
    persistHistory();
}

function renderQuizPayload(element, items, showAnswers = false) {
    if (!items.length) {
        renderMessageState(element, "Not enough content to generate quiz questions.");
        return;
    }

    const html = items.map((item, index) => `
        <div class="quiz-card">
            <h4>Q${index + 1}. ${escapeHTML(item.question)}</h4>
            <p class="quiz-meta-line">${escapeHTML(`${item.type || "MCQ"} | ${item.difficulty || "Medium"}`)}</p>
            ${(item.options || []).map((option) => `
                <label class="quiz-option">
                    <input type="radio" name="quiz-${index}" value="${escapeAttribute(option)}" ${showAnswers ? "disabled" : ""}>
                    ${escapeHTML(option)}
                </label>
            `).join("")}
            <div class="correct-answer" id="answer-${index}" ${showAnswers ? "" : "hidden"}>
                ${showAnswers ? `Correct answer: ${escapeHTML(item.answer)}` : ""}
            </div>
        </div>
    `).join("");

    element.classList.remove("empty-state");
    element.innerHTML = html;
    persistHistory();
}

function renderAssignmentPayload(element, payload) {
    const items = payload.items || [];
    if (!items.length) {
        renderMessageState(element, "No assignment questions found.");
        return;
    }

    const html = `
        <div class="assignment-preview">
            ${(items || []).map((item) => `
                <article class="assignment-sheet">
                    <div class="assignment-rule assignment-margin"></div>
                    <div class="assignment-lines">
                        <h4>${escapeHTML(item.label)}. ${escapeHTML(item.question)}</h4>
                        <h5>${escapeHTML(item.title || "Assignment Answer")}</h5>
                        ${(item.sections || []).map((section) => `
                            <p><strong>${escapeHTML(section.heading || "")}:</strong> ${escapeHTML(section.content || "")}</p>
                        `).join("")}
                        <p><strong>Conclusion:</strong> ${escapeHTML(item.conclusion || "")}</p>
                    </div>
                </article>
            `).join("")}
        </div>
    `;

    element.classList.remove("empty-state");
    element.innerHTML = html;
    persistHistory();
}


function renderYouTubeMindMap(element, payload) {
    const lines = String(payload.mind_map || payload.summary || "")
        .split("\n")
        .map((line) => line.replace(/\t/g, "    "))
        .filter(Boolean);
    const titleLine =
        lines.find((line) => line.trim().startsWith("# ")) ||
        lines.find((line) => line.trim().toLowerCase().startsWith("main topic:")) ||
        lines.find((line) => line.trim().toLowerCase().startsWith("title:")) ||
        "# Video Mind Map";
    const title = titleLine
        .replace(/^#\s*/, "")
        .replace(/^main topic:\s*/i, "")
        .replace(/^title:\s*/i, "")
        .trim();
    const branches = [];
    let currentBranch = null;

    lines.forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed) {
            return;
        }

        if (trimmed.startsWith("## ")) {
            currentBranch = {
                title: trimmed.replace(/^##\s*/, ""),
                points: []
            };
            branches.push(currentBranch);
            return;
        }

        if (trimmed.startsWith("-") && currentBranch) {
            currentBranch.points.push(trimmed.replace(/^-\s*/, ""));
            return;
        }

        if (trimmed.startsWith("-")) {
            currentBranch = {
                title: trimmed.replace(/^-\s*/, ""),
                points: []
            };
            branches.push(currentBranch);
        }
    });

    const visibleBranches = branches.slice(0, 6);
    const nodePositions = ["top-left", "top-right", "right", "bottom-right", "bottom-left", "left"];

    const html = `
        <div class="mindmap-shell">
            <div class="mindmap-meta">
                <strong>${escapeHTML(payload.message || (payload.used_transcript ? "Transcript analyzed" : "Video details analyzed"))}</strong>
            </div>
            <div class="mindmap-stage">
                <div class="mindmap-center">${escapeHTML(title || "Video Mind Map")}</div>
                ${visibleBranches.map((branch, index) => `
                    <div class="mindmap-branch ${nodePositions[index] || "right"}">
                        <span class="mindmap-connector"></span>
                        <div class="mindmap-node">
                            <strong>${escapeHTML(branch.title)}</strong>
                            ${(branch.points || []).length ? `<ul class="mindmap-subpoints">${branch.points.map((point) => `<li>${escapeHTML(point)}</li>`).join("")}</ul>` : ""}
                        </div>
                    </div>
                `).join("")}
            </div>
        </div>
    `;

    element.classList.remove("empty-state");
    element.innerHTML = html;
    persistHistory();
}

function renderMessageState(element, message) {
    element.classList.add("empty-state");
    element.innerHTML = `<p>${escapeHTML(message)}</p>`;
    persistHistory();
}

function updateVideoCard(link) {
    const videoId = extractYouTubeId(link);
    const thumb = videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : "";

    videoCard.innerHTML = `
        <div class="video-thumb" style="${thumb ? `background-image: linear-gradient(rgba(7, 12, 20, 0.35), rgba(7, 12, 20, 0.35)), url('${thumb}'); background-size: cover; background-position: center;` : ""}">
            <span>${videoId ? "Ready to study" : "Video Preview"}</span>
        </div>
        <div class="video-meta">
            <h4>${videoId ? "YouTube transcript card" : "Ready for a YouTube study session"}</h4>
            <p>${videoId ? escapeHTML(link) : "Paste a YouTube link to fetch transcript or generate a quiz."}</p>
        </div>
    `;
    persistHistory();
}

function safeStorage(action, fallback = null) {
    try {
        return action();
    } catch (_error) {
        return fallback;
    }
}

function getActivityLog() {
    return safeStorage(() => JSON.parse(localStorage.getItem(HISTORY_LOG_KEY) || "[]"), []);
}

function buildActivitySnapshot(type, detail) {
    const screenMap = {
        Chat: "chatScreen",
        Teach: "chatScreen",
        "Photo Study": "chatScreen",
        Notes: "notesScreen",
        "PDF Notes": "notesScreen",
        Quiz: "quizScreen",
        "Quiz Score": "quizScreen",
        Assignment: "assignmentScreen",
        "Library Upload": "libraryScreen",
        "YouTube Mind Map": "youtubeScreen",
        "YouTube Notes": "youtubeScreen",
        "YouTube Quiz": "youtubeScreen"
    };

    return {
        screenId: screenMap[type] || document.querySelector(".screen.active")?.id || "chatScreen",
        detail,
        chatHtml: chatBoard.innerHTML,
        notes: {
            input: notesInput.value,
            outputHtml: notesOutput.innerHTML,
            outputClass: notesOutput.className
        },
        quiz: {
            input: quizInput.value,
            mode: quizModeInput.value,
            difficulty: quizDifficultyInput.value,
            outputHtml: quizOutput.innerHTML,
            outputClass: quizOutput.className,
            score: scoreOutput.textContent
        },
        assignment: {
            input: assignmentInput.value,
            outputHtml: assignmentOutput.innerHTML,
            outputClass: assignmentOutput.className
        },
        library: {
            title: libraryTitleInput.value,
            board: libraryBoardInput.value,
            classLevel: libraryClassInput.value,
            subject: librarySubjectInput.value,
            type: libraryTypeInput.value,
            activeSession: document.querySelector(".library-session.active")?.id || "uploadSession",
            search: librarySearchInput.value,
            filterSubject: libraryFilterSubject.value,
            filterBoard: libraryFilterBoard.value,
            filterClass: libraryFilterClass.value,
            filterType: libraryFilterType.value,
            listHtml: libraryList.innerHTML,
            listClass: libraryList.className,
            readerHtml: libraryReader.innerHTML,
            readerClass: libraryReader.className
        },
        youtube: {
            link: ytLinkInput.value,
            quizCount: ytQuizCountInput.value,
            transcript: ytTranscriptInput.value,
            outputHtml: ytOutput.innerHTML,
            outputClass: ytOutput.className,
            videoCardHtml: videoCard.innerHTML
        }
    };
}

function logActivity(type, detail) {
    const log = getActivityLog();
    log.unshift({
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        type,
        detail: String(detail || "").slice(0, 180),
        time: new Date().toLocaleString(),
        snapshot: buildActivitySnapshot(type, detail)
    });
    safeStorage(() => localStorage.setItem(HISTORY_LOG_KEY, JSON.stringify(log.slice(0, 60))));
    renderActivityHistory();
}

function renderActivityHistory() {
    const log = getActivityLog();
    if (!log.length) {
        historyList.innerHTML = '<div class="history-empty">No history saved yet.</div>';
        return;
    }

    historyList.innerHTML = log.map((entry) => `
        <article class="history-card" data-history-id="${escapeAttribute(entry.id || "")}">
            <div class="history-meta">
                <strong>${escapeHTML(entry.type)}</strong>
                <span>${escapeHTML(entry.time)}</span>
            </div>
            <p>${escapeHTML(entry.detail)}</p>
        </article>
    `).join("");
}

function handleHistoryClick(event) {
    const card = event.target.closest(".history-card");
    if (!card) {
        return;
    }

    const entryId = card.dataset.historyId;
    const entry = getActivityLog().find((item) => item.id === entryId);
    if (!entry?.snapshot) {
        return;
    }

    openHistoryEntry(entry.snapshot);
}

function openHistoryEntry(snapshot) {
    if (snapshot.chatHtml) {
        chatBoard.innerHTML = snapshot.chatHtml;
    }

    notesInput.value = snapshot.notes?.input || "";
    notesOutput.className = snapshot.notes?.outputClass || "result-panel empty-state";
    notesOutput.innerHTML = snapshot.notes?.outputHtml || "Notes will appear here as key points, summary, and keywords.";

    quizInput.value = snapshot.quiz?.input || "";
    quizModeInput.value = snapshot.quiz?.mode || "mixed";
    quizDifficultyInput.value = snapshot.quiz?.difficulty || "medium";
    quizOutput.className = snapshot.quiz?.outputClass || "result-panel empty-state";
    quizOutput.innerHTML = snapshot.quiz?.outputHtml || "Generated quiz questions will appear here.";
    scoreOutput.textContent = snapshot.quiz?.score || "Score: 0/0";

    assignmentInput.value = snapshot.assignment?.input || "";
    assignmentOutput.className = snapshot.assignment?.outputClass || "result-panel empty-state";
    assignmentOutput.innerHTML = snapshot.assignment?.outputHtml || "Assignment questions and medium-length answers will appear here in notebook style.";


    libraryTitleInput.value = snapshot.library?.title || "";
    libraryBoardInput.value = snapshot.library?.board || "";
    libraryClassInput.value = snapshot.library?.classLevel || "";
    librarySubjectInput.value = snapshot.library?.subject || "";
    libraryTypeInput.value = snapshot.library?.type || "Notes";
    switchLibrarySession(snapshot.library?.activeSession || "uploadSession");
    librarySearchInput.value = snapshot.library?.search || "";
    libraryFilterSubject.value = snapshot.library?.filterSubject || "";
    libraryFilterBoard.value = snapshot.library?.filterBoard || "";
    libraryFilterClass.value = snapshot.library?.filterClass || "";
    libraryFilterType.value = snapshot.library?.filterType || "";
    libraryList.className = snapshot.library?.listClass || "library-list empty-state";
    libraryList.innerHTML = snapshot.library?.listHtml || "<p>No library files yet. Upload notes or question papers to get started.</p>";
    libraryReader.className = snapshot.library?.readerClass || "library-reader empty-state";
    libraryReader.innerHTML = snapshot.library?.readerHtml || "<p>Select a library file to preview and read it here.</p>";

    ytLinkInput.value = snapshot.youtube?.link || "";
    ytTranscriptInput.value = snapshot.youtube?.transcript || "";
    ytOutput.className = snapshot.youtube?.outputClass || "result-panel empty-state";
    ytOutput.innerHTML = snapshot.youtube?.outputHtml || "YouTube study notes or quiz content will appear here.";
    videoCard.innerHTML = snapshot.youtube?.videoCardHtml || videoCard.innerHTML;

    switchScreen(snapshot.screenId || "historyScreen");
}

function clearActivityHistory() {
    safeStorage(() => localStorage.removeItem(HISTORY_LOG_KEY));
    renderActivityHistory();
}

function serializeMessage(article) {
    return {
        type: article.classList.contains("user") ? "user" : "bot",
        text: article.querySelector("p")?.textContent || ""
    };
}

function persistHistory() {
    const activeScreen = document.querySelector(".screen.active")?.id || "chatScreen";
    const historyState = {
        activeScreen,
        botVoiceEnabled,
        preferences: {
            language: languageSelect.value,
            replyMode: replyModeSelect.value
        },
        chatMessages: Array.from(chatBoard.querySelectorAll(".message")).map(serializeMessage),
        chatState: {
            lastAskedQuestion,
            teachPanelOpen: !teachPanel.hasAttribute("hidden"),
            teachDraft: teachAnswerInput.value || ""
        },
        notes: {
            input: notesInput.value,
            outputHtml: notesOutput.innerHTML,
            outputClass: notesOutput.className,
            payload: latestNotesPayload
        },
        quiz: {
            input: quizInput.value,
            mode: quizModeInput.value,
            difficulty: quizDifficultyInput.value,
            count: quizCountInput.value,
            outputHtml: quizOutput.innerHTML,
            outputClass: quizOutput.className,
            score: scoreOutput.textContent,
            generatedQuiz
        },
        assignment: {
            level: assignmentLevelInput.value,
            questionCount: assignmentQuestionCountInput.value,
            input: assignmentInput.value,
            outputHtml: assignmentOutput.innerHTML,
            outputClass: assignmentOutput.className,
            payload: latestAssignmentPayload
        },
        library: {
            title: libraryTitleInput.value,
            board: libraryBoardInput.value,
            classLevel: libraryClassInput.value,
            subject: librarySubjectInput.value,
            type: libraryTypeInput.value,
            activeSession: document.querySelector(".library-session.active")?.id || "uploadSession",
            search: librarySearchInput.value,
            filterSubject: libraryFilterSubject.value,
            filterBoard: libraryFilterBoard.value,
            filterClass: libraryFilterClass.value,
            filterType: libraryFilterType.value,
            listHtml: libraryList.innerHTML,
            listClass: libraryList.className,
            readerHtml: libraryReader.innerHTML,
            readerClass: libraryReader.className,
            items: latestLibraryItems
        },
        youtube: {
            link: ytLinkInput.value,
            quizCount: ytQuizCountInput.value,
            transcript: ytTranscriptInput.value,
            outputHtml: ytOutput.innerHTML,
            outputClass: ytOutput.className,
            videoCardHtml: videoCard.innerHTML,
            payload: latestYtNotesPayload
        }
    };

    safeStorage(() => localStorage.setItem(HISTORY_KEY, JSON.stringify(historyState)));
}

function restoreHistory() {
    const historyState = safeStorage(() => JSON.parse(localStorage.getItem(HISTORY_KEY) || "null"));
    if (!historyState) {
        return;
    }

    languageSelect.value = historyState.preferences?.language || "hinglish";
    replyModeSelect.value = historyState.preferences?.replyMode || "both";
    botVoiceEnabled = historyState.botVoiceEnabled !== false;
    const label = botVoiceEnabled ? "Voice Reply On" : "Voice Reply Off";
    speakToggleBtn.textContent = label;

    chatBoard.innerHTML = "";
    const messages = historyState.chatMessages || [];
    if (messages.length) {
        messages.forEach((message) => createRestoredMessage(message.text, message.type));
    } else {
        chatBoard.innerHTML = `
            <article class="message bot">
                <span class="message-role">Quadratutor</span>
                <p>Welcome back. Ask any question and get a clear direct answer.</p>
            </article>
        `;
    }
    lastAskedQuestion = historyState.chatState?.lastAskedQuestion || "";
    teachQuestionLabel.textContent = lastAskedQuestion
        ? `Question: ${lastAskedQuestion}`
        : "Ask a question first, then teach the correct answer here.";
    teachAnswerInput.value = historyState.chatState?.teachDraft || "";
    if (historyState.chatState?.teachPanelOpen && lastAskedQuestion) {
        teachPanel.removeAttribute("hidden");
    } else {
        teachPanel.setAttribute("hidden", "");
    }

    notesInput.value = historyState.notes?.input || "";
    notesOutput.className = historyState.notes?.outputClass || "result-panel empty-state";
    notesOutput.innerHTML = historyState.notes?.outputHtml || "Notes will appear here as key points, summary, and keywords.";
    latestNotesPayload = historyState.notes?.payload || null;

    quizInput.value = historyState.quiz?.input || "";
    quizModeInput.value = historyState.quiz?.mode || "mixed";
    quizDifficultyInput.value = historyState.quiz?.difficulty || "medium";
    quizCountInput.value = historyState.quiz?.count || "5";
    quizOutput.className = historyState.quiz?.outputClass || "result-panel empty-state";
    quizOutput.innerHTML = historyState.quiz?.outputHtml || "Generated quiz questions will appear here.";
    scoreOutput.textContent = historyState.quiz?.score || "Score: 0/0";
    generatedQuiz = historyState.quiz?.generatedQuiz || [];

    assignmentLevelInput.value = historyState.assignment?.level || "school";
    assignmentQuestionCountInput.value = historyState.assignment?.questionCount || "5";
    assignmentInput.value = historyState.assignment?.input || "";
    assignmentOutput.className = historyState.assignment?.outputClass || "result-panel empty-state";
    assignmentOutput.innerHTML = historyState.assignment?.outputHtml || "Assignment questions and medium-length answers will appear here in notebook style.";
    latestAssignmentPayload = historyState.assignment?.payload || null;


    libraryTitleInput.value = historyState.library?.title || "";
    libraryBoardInput.value = historyState.library?.board || "";
    libraryClassInput.value = historyState.library?.classLevel || "";
    librarySubjectInput.value = historyState.library?.subject || "";
    libraryTypeInput.value = historyState.library?.type || "Notes";
    switchLibrarySession(historyState.library?.activeSession || "uploadSession");
    librarySearchInput.value = historyState.library?.search || "";
    libraryFilterSubject.value = historyState.library?.filterSubject || "";
    libraryFilterBoard.value = historyState.library?.filterBoard || "";
    libraryFilterClass.value = historyState.library?.filterClass || "";
    libraryFilterType.value = historyState.library?.filterType || "";
    libraryList.className = historyState.library?.listClass || "library-list empty-state";
    libraryList.innerHTML = historyState.library?.listHtml || "<p>No library files yet. Upload notes or question papers to get started.</p>";
    libraryReader.className = historyState.library?.readerClass || "library-reader empty-state";
    libraryReader.innerHTML = historyState.library?.readerHtml || "<p>Select a library file to preview and read it here.</p>";
    latestLibraryItems = historyState.library?.items || [];

    ytLinkInput.value = historyState.youtube?.link || "";
    ytQuizCountInput.value = historyState.youtube?.quizCount || "5";
    ytTranscriptInput.value = historyState.youtube?.transcript || "";
    ytOutput.className = historyState.youtube?.outputClass || "result-panel empty-state";
    ytOutput.innerHTML = historyState.youtube?.outputHtml || "YouTube study notes or quiz content will appear here.";
    videoCard.innerHTML = historyState.youtube?.videoCardHtml || videoCard.innerHTML;
    latestYtNotesPayload = historyState.youtube?.payload || null;

    renderActivityHistory();
    switchScreen(historyState.activeScreen === "teachScreen" ? "chatScreen" : (historyState.activeScreen || "chatScreen"));
}

function createRestoredMessage(text, type) {
    const article = document.createElement("article");
    article.className = `message ${type}`;

    const label = document.createElement("span");
    label.className = "message-role";
    label.textContent = type === "user" ? "You" : "Quadratutor";

    const body = document.createElement("p");
    body.textContent = text;

    article.append(label, body);
    chatBoard.appendChild(article);
    chatBoard.scrollTop = chatBoard.scrollHeight;
}

function extractYouTubeId(link) {
    const shortMatch = link.match(/youtu\.be\/([A-Za-z0-9_-]{6,})/);
    if (shortMatch) {
        return shortMatch[1];
    }

    const watchMatch = link.match(/[?&]v=([A-Za-z0-9_-]{6,})/);
    if (watchMatch) {
        return watchMatch[1];
    }

    const shortsMatch = link.match(/\/shorts\/([A-Za-z0-9_-]{6,})/);
    return shortsMatch ? shortsMatch[1] : "";
}

function escapeHTML(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
    return escapeHTML(value);
}
