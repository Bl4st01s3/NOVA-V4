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

    // Global reference to the currently streaming message div
    let activeStreamingContentDiv = null;

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';

        const loadingId = appendLoading();

        try {
            // Prepare an empty bubble for the streaming response
            removeMessage(loadingId);
            activeStreamingContentDiv = createEmptyMessageBubble('assistant');

            // The python backend will now fire eel.streamAIToken multiple times before returning
            await eel.send_message_to_nova(text)();

            // Clear the active reference once done
            activeStreamingContentDiv = null;
        } catch (error) {
            removeMessage(loadingId);
            appendMessage('system', 'Error connecting to Bionic Engine: ' + error);
            activeStreamingContentDiv = null;
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    micBtn.addEventListener('click', () => {
        appendMessage('system', 'Voice input module not yet initialized (Phase 2).');
    });

    // --- Voice Profile Management Logic ---
    const vpDashboard = document.getElementById('vp-card-dashboard');
    const vpWizard = document.getElementById('vp-card-wizard');
    const vpListContainer = document.getElementById('vp-list-container');
    const enrollBtn = document.getElementById('enroll-voice-btn');

    // Load profiles from persistent Python backend storage
    let voiceProfiles = [];

    async function loadVoiceProfiles() {
        try {
            voiceProfiles = await eel.get_voice_profiles()();
            renderProfiles();
        } catch(e) {
            console.error("Failed to load voice profiles", e);
        }
    }

    function renderProfiles() {
        vpListContainer.innerHTML = '';
        if (!voiceProfiles || voiceProfiles.length === 0) {
            vpListContainer.innerHTML = '<p class="placeholder-text" style="font-size:12px;">No voice profiles enrolled.</p>';
            return;
        }

        voiceProfiles.forEach((profile, index) => {
            const row = document.createElement('div');
            row.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(0,0,0,0.5); border: 1px solid var(--purple); margin-bottom: 10px;";

            const info = document.createElement('div');
            info.innerHTML = `<strong style="color: var(--cyan);">${profile.name}</strong> <span style="color:#888; font-size: 12px;">(${profile.title})</span>`;

            const btns = document.createElement('div');
            btns.style.display = "flex";
            btns.style.gap = "10px";

            const retrainBtn = document.createElement('button');
            retrainBtn.innerText = "[ RETRAIN ]";
            retrainBtn.className = "cyber-btn";
            retrainBtn.style.cssText = "width: auto; padding: 5px 10px; font-size: 10px; margin: 0; border-color: var(--cyan); color: var(--cyan);";
            retrainBtn.onclick = () => startEnrollmentWizard(profile.name, profile.title, index);

            const removeBtn = document.createElement('button');
            removeBtn.innerText = "[ REMOVE ]";
            removeBtn.className = "cyber-btn";
            removeBtn.style.cssText = "width: auto; padding: 5px 10px; font-size: 10px; margin: 0; border-color: red; color: red;";
            removeBtn.onclick = () => {
                if(confirm(`Remove profile for ${profile.name}?`)) {
                    voiceProfiles.splice(index, 1);
                    try { eel.update_voice_profiles(voiceProfiles)(); } catch(e){}
                    renderProfiles();
                }
            };

            btns.appendChild(retrainBtn);
            btns.appendChild(removeBtn);
            row.appendChild(info);
            row.appendChild(btns);
            vpListContainer.appendChild(row);
        });
    }

    // Load profiles shortly after init
    setTimeout(loadVoiceProfiles, 500);

    // Start New Enrollment
    enrollBtn.addEventListener('click', () => {
        const nameInput = document.getElementById('vp-name');
        const titleInput = document.getElementById('vp-title');
        const name = nameInput.value.trim();
        const title = titleInput.value.trim();

        if(!name || !title) {
            alert("Please enter a name and title before enrolling.");
            return;
        }

        nameInput.value = '';
        titleInput.value = '';
        startEnrollmentWizard(name, title, -1); // -1 means new profile
    });

    // --- Enrollment Wizard Logic ---
    const pangrams = [
        "The quick brown fox jumps over the lazy dog.",
        "Pack my box with five dozen liquor jugs.",
        "Sphinx of black quartz, judge my vow."
    ];

    let currentWizardState = {
        name: '',
        title: '',
        index: -1,
        phraseIndex: 0
    };

    const wTitle = document.getElementById('vp-wizard-name');
    const wNum = document.getElementById('vp-phrase-num');
    const wText = document.getElementById('vp-phrase-text');

    const btnRecord = document.getElementById('vp-btn-record');
    const btnAccept = document.getElementById('vp-btn-accept');
    const btnRerecord = document.getElementById('vp-btn-rerecord');
    const btnCancel = document.getElementById('vp-btn-cancel');
    const dot = btnRecord.querySelector('.dot');

    function startEnrollmentWizard(name, title, profileIndex) {
        currentWizardState = { name, title, index: profileIndex, phraseIndex: 0 };

        wTitle.innerText = name;
        updateWizardUI();

        vpDashboard.style.display = 'none';
        vpWizard.style.display = 'block';
    }

    function updateWizardUI() {
        wNum.innerText = currentWizardState.phraseIndex + 1;
        wText.innerText = `"${pangrams[currentWizardState.phraseIndex]}"`;

        btnRecord.style.display = 'block';
        btnRecord.innerHTML = `<span class="dot" style="display:inline-block; background-color: red; box-shadow: 0 0 10px red; animation: none;"></span> [ RECORD ]`;
        btnRecord.disabled = false;

        btnAccept.style.display = 'none';
        btnRerecord.style.display = 'none';
        document.getElementById('vu-meter-container').style.display = 'none';
    }

    let isCurrentlyRecording = false;
    let vuInterval = null;

    btnRecord.addEventListener('click', () => {
        if (!isCurrentlyRecording) {
            // Start real audio recording
            isCurrentlyRecording = true;
            try { eel.start_recording(currentWizardState.name, currentWizardState.phraseIndex)(); } catch(e){}

            btnRecord.innerHTML = `<span class="dot" style="display:inline-block; background-color: red; box-shadow: 0 0 10px red; animation: blink 1s infinite;"></span> [ STOP RECORDING ]`;

            // Show VU Meter and start polling
            const vuContainer = document.getElementById('vu-meter-container');
            const vuLevel = document.getElementById('vu-level');
            vuContainer.style.display = 'block';

            // Adjust background-size dynamically so the gradient spans the full width of the parent container
            // regardless of the child's current width percentage
            const parentWidth = vuContainer.clientWidth;
            vuLevel.style.backgroundSize = `${parentWidth}px 10px`;

            vuInterval = setInterval(async () => {
                try {
                    // We will now receive a normalized 0-100 value from the backend
                    let percent = await eel.get_current_volume()();
                    vuLevel.style.width = `${percent}%`;
                } catch(e) {}
            }, 50);

        } else {
            // Stop recording
            isCurrentlyRecording = false;
            if(vuInterval) clearInterval(vuInterval);
            document.getElementById('vu-meter-container').style.display = 'none';

            try { eel.stop_recording()(); } catch(e){}

            btnRecord.style.display = 'none';
            btnAccept.style.display = 'block';
            btnRerecord.style.display = 'block';
        }
    });

    btnRerecord.addEventListener('click', () => {
        try { eel.cancel_recording()(); } catch(e){}
        updateWizardUI();
    });

    btnAccept.addEventListener('click', () => {
        currentWizardState.phraseIndex++;

        if (currentWizardState.phraseIndex >= pangrams.length) {
            // Finished!
            alert(`Voice profile for ${currentWizardState.name} successfully built!`);

            if (currentWizardState.index === -1) {
                // Add new
                voiceProfiles.push({ name: currentWizardState.name, title: currentWizardState.title });
            } else {
                // Update existing
                voiceProfiles[currentWizardState.index] = { name: currentWizardState.name, title: currentWizardState.title };
            }

            try { eel.update_voice_profiles(voiceProfiles)(); } catch(e){}
            renderProfiles();

            vpWizard.style.display = 'none';
            vpDashboard.style.display = 'block';
        } else {
            // Next phrase
            updateWizardUI();
        }
    });

    btnCancel.addEventListener('click', () => {
        vpWizard.style.display = 'none';
        vpDashboard.style.display = 'block';
    });

    // OBS URL Logic & Registration
    const obsUrlInput = document.getElementById('obs-url');
    const obsCopyBtn = document.getElementById('copy-obs-btn');

    // Tell the backend webhook server what our dynamic port is
    const currentPort = window.location.port;
    fetch('http://127.0.0.1:54321/register_port', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' }, // Use text/plain to bypass CORS preflight
        body: JSON.stringify({ port: currentPort })
    }).catch(e => console.log("Failed to register port with backend:", e));

    // Display the static URL in the UI instead of the random one
    obsUrlInput.value = "http://127.0.0.1:54321/obs";

    obsCopyBtn.addEventListener('click', () => {
        obsUrlInput.select();
        document.execCommand('copy');

        const originalText = obsCopyBtn.innerText;
        obsCopyBtn.innerText = "[ COPIED! ]";
        setTimeout(() => {
            obsCopyBtn.innerText = originalText;
        }, 2000);
    });

    // Briefing Preferences Logic (Dynamic Tools)
    async function loadDynamicTools() {
        const toolsContainer = document.getElementById('dynamic-tools-container');
        try {
            const availableTools = await eel.get_available_tools()();

            if (availableTools.length === 0) {
                toolsContainer.innerHTML = '<p class="placeholder-text" style="font-size:12px;">No tools found in /tools directory.</p>';
                return;
            }

            toolsContainer.innerHTML = ''; // Clear container

            availableTools.forEach(toolName => {
                const label = document.createElement('label');
                label.style.cssText = "display: flex; align-items: center; gap: 10px; cursor: pointer;";

                const checkbox = document.createElement('input');
                checkbox.type = "checkbox";
                checkbox.id = `brief-tool-${toolName}`;

                // Capitalize first letter for display
                const displayName = toolName.charAt(0).toUpperCase() + toolName.slice(1);

                const span = document.createElement('span');
                span.innerText = `Include ${displayName} Data`;

                label.appendChild(checkbox);
                label.appendChild(span);
                toolsContainer.appendChild(label);

                // Load saved state or default to true
                const savedVal = localStorage.getItem(`nova_tool_${toolName}`);
                checkbox.checked = savedVal === null ? true : (savedVal === 'true');

                // Event listener
                checkbox.addEventListener('change', () => {
                    localStorage.setItem(`nova_tool_${toolName}`, checkbox.checked);
                    syncBriefingPrefs(availableTools);
                });
            });

            syncBriefingPrefs(availableTools);

        } catch (e) {
            console.error("Failed to load tools from backend.", e);
        }
    }

    function syncBriefingPrefs(availableTools) {
        const prefs = {};
        availableTools.forEach(toolName => {
            prefs[toolName] = document.getElementById(`brief-tool-${toolName}`).checked;
        });

        try {
            eel.update_briefing_prefs(prefs)();
        } catch(e) {}
    }

    // Load dynamic tools after a small delay to ensure Eel is ready
    setTimeout(loadDynamicTools, 500);

    // Audio Device Selection Logic
    async function loadAudioDevices() {
        const deviceSelect = document.getElementById('audio-device-select');
        try {
            const devices = await eel.get_audio_devices()();
            deviceSelect.innerHTML = ''; // clear loading text

            if (devices.length === 0) {
                deviceSelect.innerHTML = '<option value="">No microphones found</option>';
                return;
            }

            devices.forEach(dev => {
                const opt = document.createElement('option');
                opt.value = dev.id;
                opt.innerText = dev.name;
                deviceSelect.appendChild(opt);
            });

            // Load saved preference or default to first
            const savedDevice = localStorage.getItem('nova_audio_device_id');
            if (savedDevice !== null) {
                deviceSelect.value = savedDevice;
                eel.set_audio_device(savedDevice)();
            } else {
                eel.set_audio_device(devices[0].id)();
            }

            // Handle changes
            deviceSelect.addEventListener('change', () => {
                const selectedId = deviceSelect.value;
                localStorage.setItem('nova_audio_device_id', selectedId);
                eel.set_audio_device(selectedId)();
            });

        } catch(e) {
            console.error("Failed to load audio devices", e);
            deviceSelect.innerHTML = '<option value="">Error loading devices</option>';
        }
    }

    // Audio Filter Sliders Logic
    function initAudioFilters() {
        // Gain
        const gainSlider = document.getElementById('audio-gain-slider');
        const gainDisplay = document.getElementById('gain-value-display');

        const savedGain = localStorage.getItem('nova_audio_gain') || "1.0";
        gainSlider.value = savedGain;
        gainDisplay.innerText = `${parseFloat(savedGain).toFixed(1)}x`;
        try { eel.set_mic_gain(savedGain)(); } catch(e){}

        gainSlider.addEventListener('input', () => {
            const val = parseFloat(gainSlider.value).toFixed(1);
            gainDisplay.innerText = `${val}x`;
            localStorage.setItem('nova_audio_gain', val);
            try { eel.set_mic_gain(val)(); } catch(e){}
        });

        // Noise Gate
        const gateSlider = document.getElementById('audio-gate-slider');
        const gateDisplay = document.getElementById('gate-value-display');

        const savedGate = localStorage.getItem('nova_audio_gate') || "-40";
        gateSlider.value = savedGate;
        gateDisplay.innerText = `${savedGate} dB`;
        try { eel.set_noise_gate(savedGate)(); } catch(e){}

        gateSlider.addEventListener('input', () => {
            const val = gateSlider.value;
            gateDisplay.innerText = `${val} dB`;
            localStorage.setItem('nova_audio_gate', val);
            try { eel.set_noise_gate(val)(); } catch(e){}
        });

        // Spectral Noise Reduction
        const spectralCheckbox = document.getElementById('audio-spectral-nr');
        const savedSpectral = localStorage.getItem('nova_audio_spectral');
        if (savedSpectral !== null) {
            spectralCheckbox.checked = (savedSpectral === 'true');
        }
        try { eel.set_spectral_nr(spectralCheckbox.checked)(); } catch(e){}

        spectralCheckbox.addEventListener('change', () => {
            localStorage.setItem('nova_audio_spectral', spectralCheckbox.checked);
            try { eel.set_spectral_nr(spectralCheckbox.checked)(); } catch(e){}
        });
    }

    setTimeout(() => {
        loadAudioDevices();
        initAudioFilters();
    }, 500);

    // Helper functions for Chat
    function appendMessage(sender, text) {
        const content = createEmptyMessageBubble(sender);
        const textNode = document.createTextNode(text);
        content.appendChild(textNode);
        content.innerHTML = content.innerHTML.replace(/\n/g, '<br>');
        scrollToBottom();
    }

    function createEmptyMessageBubble(sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        const avatar = document.createElement('div');
        avatar.classList.add('hexagon-avatar', `${sender}-avatar`);

        const content = document.createElement('div');
        content.classList.add('message-content');

        if (sender === 'user') {
            messageDiv.appendChild(content);
            messageDiv.appendChild(avatar);
        } else {
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
        }

        chatContainer.appendChild(messageDiv);
        scrollToBottom();
        return content;
    }

    // Exposed streaming handler
    window.streamAIToken = function(token) {
        if (activeStreamingContentDiv) {
            // Append safely keeping line breaks
            const textNode = document.createTextNode(token);
            activeStreamingContentDiv.appendChild(textNode);
            // We periodically update innerHTML to parse newlines into <br>
            // but doing it every token is expensive. Playwright check will verify if we need it.
            if (token.includes('\n')) {
                activeStreamingContentDiv.innerHTML = activeStreamingContentDiv.innerHTML.replace(/\n/g, '<br>');
            }
            scrollToBottom();
        }
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

eel.expose(pushAIMessage);
function pushAIMessage(text) {
    // Re-use the logic from inside DOMContentLoaded
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'assistant');

    const avatar = document.createElement('div');
    avatar.classList.add('hexagon-avatar', 'assistant-avatar');

    const content = document.createElement('div');
    content.classList.add('message-content');

    const textNode = document.createTextNode(text);
    content.appendChild(textNode);
    content.innerHTML = content.innerHTML.replace(/\n/g, '<br>');

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
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
eel.expose(window.streamAIToken, "streamAIToken");
