document.addEventListener("DOMContentLoaded", () => {
    // Tab Navigation Logic
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and panes
            navBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            // Add active class to clicked button and corresponding pane
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Chat Logic
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';

        const loadingId = appendLoading();

        try {
            const response = await eel.send_message_to_nova(text)();
            removeMessage(loadingId);
            appendMessage('assistant', response);
        } catch (error) {
            removeMessage(loadingId);
            appendMessage('system', 'Error connecting to Bionic Engine: ' + error);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    micBtn.addEventListener('click', () => {
        appendMessage('system', 'Voice input module not yet initialized (Phase 2).');
    });

    // Settings / Enrollment Logic (Placeholder)
    const enrollBtn = document.getElementById('enroll-voice-btn');
    enrollBtn.addEventListener('click', () => {
        const name = document.getElementById('vp-name').value;
        const title = document.getElementById('vp-title').value;
        if(!name || !title) {
            alert("Please enter a name and title before enrolling.");
            return;
        }
        alert(`Voice enrollment initialized for ${name} (${title}).\nWaiting for Phase 2 audio engine integration...`);
    });

    // OBS URL Logic
    const obsUrlInput = document.getElementById('obs-url');
    const obsCopyBtn = document.getElementById('copy-obs-btn');

    // Set the input value to the current host + obs_overlay.html
    const currentUrl = window.location.href.split('index.html')[0];
    obsUrlInput.value = currentUrl + "obs_overlay.html";

    obsCopyBtn.addEventListener('click', () => {
        obsUrlInput.select();
        document.execCommand('copy');

        const originalText = obsCopyBtn.innerText;
        obsCopyBtn.innerText = "[ COPIED! ]";
        setTimeout(() => {
            obsCopyBtn.innerText = originalText;
        }, 2000);
    });

    // Helper functions for Chat
    function appendMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        const avatar = document.createElement('div');
        avatar.classList.add('hexagon-avatar', `${sender}-avatar`);

        const content = document.createElement('div');
        content.classList.add('message-content');

        const textNode = document.createTextNode(text);
        content.appendChild(textNode);
        content.innerHTML = content.innerHTML.replace(/\n/g, '<br>');

        if (sender === 'user') {
            messageDiv.appendChild(content);
            messageDiv.appendChild(avatar);
        } else {
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
        }

        chatContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    function appendLoading() {
        const id = 'loading-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'assistant');
        messageDiv.id = id;

        const avatar = document.createElement('div');
        avatar.classList.add('hexagon-avatar', `system-avatar`);

        const content = document.createElement('div');
        content.classList.add('message-content');
        content.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        chatContainer.appendChild(messageDiv);
        scrollToBottom();
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});

// Exposed Functions from Python
eel.expose(appendSystemMessage);
function appendSystemMessage(text) {
    // Keeping for backwards compatibility
    console.log("System Message:", text);
}

eel.expose(addActivityLog);
function addActivityLog(type, message) {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    const logEntry = document.createElement('div');
    logEntry.classList.add('log-entry', type === 'tool' ? 'tool-log' : 'system-log');

    // Get simple timestamp
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour12: false });

    // Format the text
    logEntry.innerHTML = `<span class="log-time">[${timeString}]</span> ${message}`;

    logContainer.appendChild(logEntry);

    // Auto scroll log to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}
