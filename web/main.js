document.addEventListener("DOMContentLoaded", () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');

    // Handle sending a message
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // Display user message
        appendMessage('user', text);
        userInput.value = '';

        // Display loading indicator
        const loadingId = appendLoading();

        // Call Python function to process the message
        try {
            // Using eel to call python function
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
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    micBtn.addEventListener('click', () => {
        appendMessage('system', 'Voice input module not yet initialized (Phase 2).');
    });

    function appendMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        const avatar = document.createElement('div');
        avatar.classList.add('hexagon-avatar', `${sender}-avatar`);

        const content = document.createElement('div');
        content.classList.add('message-content');

        // Safely set text content and convert newlines to breaks to prevent XSS
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

// Function callable from Python to append messages proactively
eel.expose(appendSystemMessage);
function appendSystemMessage(text) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'system');

    const avatar = document.createElement('div');
    avatar.classList.add('hexagon-avatar', `system-avatar`);

    const content = document.createElement('div');
    content.classList.add('message-content');

    // Safely set text content
    const textNode = document.createTextNode(text);
    content.appendChild(textNode);
    content.innerHTML = content.innerHTML.replace(/\n/g, '<br>');

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
