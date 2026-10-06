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

    // Chat Logic
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');

    // Global reference to the currently streaming message div
    window.window.activeStreamingContentDiv = null;

    // Load persistent chat history on boot
    async function loadChatHistory() {
        try {
            const history = await eel.get_chat_history()();
            if (history && history.length > 0) {
                history.forEach(msg => {
                    // Skip tool calls/responses in the UI to keep it clean, only show user/assistant
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        if (msg.content) {
                            appendMessage(msg.role, msg.content);
                        }
                    }
                });
            }
        } catch (e) {
            console.error("Failed to load chat history:", e);
        }
    }

    setTimeout(loadChatHistory, 500);

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';

        const loadingId = appendLoading();

        // Prepare an empty bubble for the streaming response
        removeMessage(loadingId);
        window.activeStreamingContentDiv = createEmptyMessageBubble('assistant');

        // We do NOT await this call! If LM Studio takes 2 minutes to start generating,
        // Eel's internal WebSocket promise will time out and crash the frontend connection.
        // We fire and forget, and let Python push the tokens back to us async.
        try {
            eel.send_message_to_nova(text)();

            // Start polling the local HTTP queue for tokens
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fetch('http://127.0.0.1:54321/stream');
                    if (response.ok) {
                        const data = await response.json();
                        if (data.tokens && data.tokens.length > 0) {
                            for (let token of data.tokens) {
                                if (token === '[DONE]') {
                                    clearInterval(pollInterval);
                                    window.activeStreamingContentDiv = null;
                                    return;
                                }

                                if (window.activeStreamingContentDiv) {
                                    const textNode = document.createTextNode(token);
                                    window.activeStreamingContentDiv.appendChild(textNode);
                                    if (token.includes('\n')) {
                                        window.activeStreamingContentDiv.innerHTML = window.activeStreamingContentDiv.innerHTML.replace(/\n/g, '<br>');
                                    }
                                    window.scrollToBottom();
                                }
                            }
                        }
                    }
                } catch (e) {
                    console.log("Polling error:", e);
                }
            }, 100);

        } catch (error) {
            removeMessage(loadingId);
            appendMessage('system', 'Error connecting to Bionic Engine: ' + error);
            window.activeStreamingContentDiv = null;
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
        const briefingContainer = document.getElementById('dynamic-tools-container');
        const aiToolsContainer = document.getElementById('ai-tools-container');

        try {
            const availableTools = await eel.get_available_tools()();
            const safeToolsMap = await eel.get_stream_safe_tools()() || {};

            if (availableTools.length === 0) {
                briefingContainer.innerHTML = '<p class="placeholder-text" style="font-size:12px;">No tools found in /tools directory.</p>';
                if (aiToolsContainer) aiToolsContainer.innerHTML = '<p class="placeholder-text" style="font-size:12px;">No tools found in /tools directory.</p>';
                return;
            }

            briefingContainer.innerHTML = ''; // Clear container
            if (aiToolsContainer) aiToolsContainer.innerHTML = '';

            availableTools.forEach(toolName => {
                const displayName = toolName.charAt(0).toUpperCase() + toolName.slice(1).replace('_', ' ');

                // 1. Briefing Checkbox (Settings Tab)
                const briefLabel = document.createElement('label');
                briefLabel.className = "cyber-checkbox-container";

                const briefCheckbox = document.createElement('input');
                briefCheckbox.type = "checkbox";
                briefCheckbox.id = `brief-tool-${toolName}`;

                const briefHexSpan = document.createElement('span');
                briefHexSpan.className = "checkmark-hex";

                const briefTextSpan = document.createElement('span');
                briefTextSpan.innerText = `Include ${displayName} Data`;

                briefLabel.appendChild(briefCheckbox);
                briefLabel.appendChild(briefHexSpan);
                briefLabel.appendChild(briefTextSpan);
                briefingContainer.appendChild(briefLabel);

                const savedBriefVal = localStorage.getItem(`nova_briefing_tool_${toolName}`);
                briefCheckbox.checked = savedBriefVal === null ? true : (savedBriefVal === 'true');

                briefCheckbox.addEventListener('change', () => {
                    localStorage.setItem(`nova_briefing_tool_${toolName}`, briefCheckbox.checked);
                    syncBriefingPrefs(availableTools);
                });

                // 2. AI Tool Checkbox (Tools Tab)
                if (aiToolsContainer) {
                    const toolRow = document.createElement('div');
                    toolRow.style.display = "flex";
                    toolRow.style.alignItems = "center";
                    toolRow.style.justifyContent = "space-between";
                    toolRow.style.background = "rgba(0, 243, 255, 0.05)";
                    toolRow.style.padding = "10px";
                    toolRow.style.border = "1px solid rgba(0, 243, 255, 0.2)";
                    toolRow.style.borderRadius = "5px";

                    // Left Side: Enable Tool Toggle
                    const leftCol = document.createElement('div');
                    const aiLabel = document.createElement('label');
                    aiLabel.className = "cyber-checkbox-container";
                    aiLabel.style.margin = "0";

                    const aiCheckbox = document.createElement('input');
                    aiCheckbox.type = "checkbox";
                    aiCheckbox.id = `ai-tool-${toolName}`;

                    const aiHexSpan = document.createElement('span');
                    aiHexSpan.className = "checkmark-hex";

                    const aiTextSpan = document.createElement('span');
                    aiTextSpan.innerText = `Enable ${displayName}`;

                    aiLabel.appendChild(aiCheckbox);
                    aiLabel.appendChild(aiHexSpan);
                    aiLabel.appendChild(aiTextSpan);
                    leftCol.appendChild(aiLabel);

                    const savedAiVal = localStorage.getItem(`nova_ai_tool_${toolName}`);
                    aiCheckbox.checked = savedAiVal === null ? true : (savedAiVal === 'true');

                    aiCheckbox.addEventListener('change', () => {
                        localStorage.setItem(`nova_ai_tool_${toolName}`, aiCheckbox.checked);
                        syncAIToolsPrefs(availableTools);
                    });

                    // Right Side: Safe for Stream Toggle & Config Button
                    const rightCol = document.createElement('div');
                    rightCol.style.display = "flex";
                    rightCol.style.alignItems = "center";
                    rightCol.style.gap = "20px";

                    // Stream Safe Toggle
                    const safeLabel = document.createElement('label');
                    safeLabel.className = "cyber-checkbox-container";
                    safeLabel.style.margin = "0";

                    const safeCheckbox = document.createElement('input');
                    safeCheckbox.type = "checkbox";

                    // Use backend state instead of localStorage
                    const isSafe = !!safeToolsMap[toolName];
                    safeCheckbox.checked = isSafe;

                    const safeHexSpan = document.createElement('span');
                    safeHexSpan.className = "checkmark-hex";

                    const safeTextSpan = document.createElement('span');
                    safeTextSpan.innerText = "Safe for Stream";
                    safeTextSpan.style.color = "#ff007f"; // Distinct warning color
                    safeTextSpan.style.fontSize = "12px";

                    safeLabel.appendChild(safeCheckbox);
                    safeLabel.appendChild(safeHexSpan);
                    safeLabel.appendChild(safeTextSpan);
                    rightCol.appendChild(safeLabel);

                    safeCheckbox.addEventListener('change', () => {
                        try { eel.set_tool_stream_safe(toolName, safeCheckbox.checked)(); } catch(e) {}
                    });

                    // Config Button Logic
                    const configBtn = document.createElement('button');
                    configBtn.className = "cyber-btn";
                    configBtn.innerText = "CONFIG";
                    configBtn.style.padding = "5px 10px";
                    configBtn.style.fontSize = "12px";
                    configBtn.style.display = "none"; // Hidden until we verify config exists
                    rightCol.appendChild(configBtn);

                    // Check if tool has a config
                    eel.get_tool_config(toolName)().then(configData => {
                        if (configData) {
                            configBtn.style.display = "block";
                            configBtn.onclick = () => openConfigModal(toolName, configData);
                        }
                    });

                    toolRow.appendChild(leftCol);
                    toolRow.appendChild(rightCol);
                    aiToolsContainer.appendChild(toolRow);
                }
            });

            syncBriefingPrefs(availableTools);
            syncAIToolsPrefs(availableTools);

        } catch (e) {
            console.error("Failed to load tools from backend.", e);
        }
    }

    function syncBriefingPrefs(availableTools) {
        const prefs = {};
        availableTools.forEach(toolName => {
            const el = document.getElementById(`brief-tool-${toolName}`);
            if (el) prefs[toolName] = el.checked;
        });

        try {
            eel.update_briefing_prefs(prefs)();
        } catch(e) {}
    }

    function syncAIToolsPrefs(availableTools) {
        const prefs = {};
        availableTools.forEach(toolName => {
            const el = document.getElementById(`ai-tool-${toolName}`);
            if (el) prefs[toolName] = el.checked;
        });

        try {
            eel.update_llm_tools_prefs(prefs)();
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


    async function loadTTSVoices() {
        const voiceSelect = document.getElementById('tts-voice-select');
        try {
            const voices = await eel.get_tts_voices()();
            voiceSelect.innerHTML = '';

            if (voices.length === 0) {
                voiceSelect.innerHTML = '<option value="">No voices found</option>';
                return;
            }

            voices.forEach(voice => {
                const opt = document.createElement('option');
                opt.value = voice.id;
                opt.innerText = voice.name;
                voiceSelect.appendChild(opt);
            });

            let savedPrefs = null;
            try { savedPrefs = await eel.load_tts_prefs()(); } catch(e){}

            const rateSlider = document.getElementById('tts-rate-slider');
            const rateDisplay = document.getElementById('tts-rate-display');
            const volSlider = document.getElementById('tts-volume-slider');
            const volDisplay = document.getElementById('tts-volume-display');
            const effectSelect = document.getElementById('tts-effect-select');

            if (savedPrefs) {
                if (savedPrefs.voice_id) voiceSelect.value = savedPrefs.voice_id;
                if (savedPrefs.rate) {
                    rateSlider.value = savedPrefs.rate;
                    rateDisplay.innerText = `${savedPrefs.rate} WPM`;
                }
                if (savedPrefs.volume !== undefined) {
                    volSlider.value = savedPrefs.volume;
                    volDisplay.innerText = `${Math.round(savedPrefs.volume * 100)}%`;
                }
                if (savedPrefs.effect) effectSelect.value = savedPrefs.effect;

                // apply instantly
                try {
                    eel.set_tts_voice(voiceSelect.value)();
                    eel.set_tts_params(rateSlider.value, volSlider.value)();
                    eel.set_tts_effect(effectSelect.value)();
                } catch(e){}
            } else {
                // Initial defaults fallback
                let bestMatch = voices[0].id;
                for (let v of voices) {
                    if (v.name.toLowerCase().includes('hazel') || v.name.toLowerCase().includes('zira') || v.name.toLowerCase().includes('uk') || v.name.toLowerCase().includes('british')) {
                        bestMatch = v.id;
                        break;
                    }
                }
                voiceSelect.value = bestMatch;
                try {
                    eel.set_tts_voice(bestMatch)();
                    eel.set_tts_params(rateSlider.value, volSlider.value)();
                } catch(e){}
            }

            // Real-time slider updates (visual only)
            rateSlider.addEventListener('input', () => {
                rateDisplay.innerText = `${rateSlider.value} WPM`;
            });
            volSlider.addEventListener('input', () => {
                volDisplay.innerText = `${Math.round(volSlider.value * 100)}%`;
            });

            // Save Button Logic
            const saveBtn = document.getElementById('save-tts-btn');
            if(saveBtn) {
                saveBtn.addEventListener('click', () => {
                    const vid = voiceSelect.value;
                    const r = rateSlider.value;
                    const v = volSlider.value;
                    const ef = effectSelect.value;

                    try {
                        eel.set_tts_voice(vid)();
                        eel.set_tts_params(r, v)();
                        eel.set_tts_effect(ef)();
                        eel.save_tts_prefs(vid, parseInt(r), parseFloat(v), ef)();

                        saveBtn.innerText = "SAVED!";
                        saveBtn.style.color = "#0f0";
                        setTimeout(() => {
                            saveBtn.innerText = "[ SAVE TTS CONFIGURATION ]";
                            saveBtn.style.color = "";
                        }, 2000);
                    } catch(e){}
                });
            }

        } catch(e) {
            console.error("Failed to load TTS voices", e);
            voiceSelect.innerHTML = '<option value="">Error loading voices</option>';
        }
    }

    setTimeout(() => {
        loadAudioDevices();
        initAudioFilters();
        loadTTSVoices();
    }, 500);

    // Helper functions for Chat
    function appendMessage(sender, text) {
        const content = createEmptyMessageBubble(sender);
        const textNode = document.createTextNode(text);
        content.appendChild(textNode);
        content.innerHTML = content.innerHTML.replace(/\n/g, '<br>');
        window.scrollToBottom();
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
        window.scrollToBottom();
        return content;
    }

    // Exposed streaming handler
    window.streamAIToken = function(token) {
        if (window.activeStreamingContentDiv) {
            // Append safely keeping line breaks
            const textNode = document.createTextNode(token);
            window.activeStreamingContentDiv.appendChild(textNode);
            // We periodically update innerHTML to parse newlines into <br>
            // but doing it every token is expensive. Playwright check will verify if we need it.
            if (token.includes('\n')) {
                window.activeStreamingContentDiv.innerHTML = window.activeStreamingContentDiv.innerHTML.replace(/\n/g, '<br>');
            }
            window.scrollToBottom();
        }
    }

    // Called by python when the stream is completely finished
    window.streamAIComplete = function() {
        window.activeStreamingContentDiv = null;
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
        window.scrollToBottom();
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    window.scrollToBottom = function() {
        const chatC = document.getElementById('chat-container');
        if (chatC) chatC.scrollTop = chatC.scrollHeight;
    }
});

// Exposed Functions from Python
eel.expose(triggerBootSequence);
function triggerBootSequence() {
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;

    // Drop a system message indicating boot
    const sysDiv = document.createElement('div');
    sysDiv.classList.add('log-entry', 'system-log');
    sysDiv.style.textAlign = 'center';
    sysDiv.style.color = 'var(--cyan)';
    sysDiv.style.marginBottom = '20px';
    sysDiv.innerHTML = `<em>[ SYSTEM EVENT ] BIONIC ENGINE STARTED. NOVA AI SYSTEMS COMING ONLINE...</em>`;
    chatContainer.appendChild(sysDiv);
    window.scrollToBottom();

    // The python backend will directly capture this hidden command
    eel.send_message_to_nova("[SYSTEM_BOOT_SEQUENCE]");

    // Start polling the local HTTP queue for the response
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch('http://127.0.0.1:54321/stream');
            if (response.ok) {
                const data = await response.json();
                if (data.tokens && data.tokens.length > 0) {
                    for (let token of data.tokens) {
                        if (token === '[DONE]') {
                            clearInterval(pollInterval);
                            window.activeStreamingContentDiv = null;
                            return;
                        }

                        // If this is the first token of the boot sequence, create the bubble
                        if (!window.activeStreamingContentDiv) {
                            // Quick manual creation of the bubble from outside DOMContentLoaded
                            const messageDiv = document.createElement('div');
                            messageDiv.classList.add('message', 'assistant');
                            const avatar = document.createElement('div');
                            avatar.classList.add('hexagon-avatar', 'assistant-avatar');
                            const content = document.createElement('div');
                            content.classList.add('message-content');
                            messageDiv.appendChild(avatar);
                            messageDiv.appendChild(content);
                            chatContainer.appendChild(messageDiv);
                            window.activeStreamingContentDiv = content;
                        }

                        const textNode = document.createTextNode(token);
                        window.activeStreamingContentDiv.appendChild(textNode);
                        if (token.includes('\n')) {
                            window.activeStreamingContentDiv.innerHTML = window.activeStreamingContentDiv.innerHTML.replace(/\n/g, '<br>');
                        }
                        window.scrollToBottom();
                    }
                }
            }
        } catch (e) {}
    }, 100);
}

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

function addActivityLog(type, message, providedTime = null) {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    const logEntry = document.createElement('div');
    logEntry.classList.add('log-entry', type === 'tool' ? 'tool-log' : 'system-log');

    // Get simple timestamp
    let timeString = providedTime;
    if (!timeString) {
        const now = new Date();
        timeString = now.toLocaleTimeString([], { hour12: false });
    }

    logEntry.innerHTML = `<span class="log-time">[${timeString}]</span> <span class="log-msg">${message}</span>`;
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Load Persistent Activity History
async function loadActivityHistory() {
    try {
        const history = await eel.get_activity_history()();
        if (history && history.length > 0) {
            history.forEach(log => {
                addActivityLog(log.type, log.message, log.time);
            });
        }
    } catch (e) {
        console.error("Failed to load activity history:", e);
    }
}
setTimeout(loadActivityHistory, 500);


// --- Dynamic Config Modal Logic ---
let currentConfigTool = null;
let currentConfigData = null;

// Helper to generate spreadsheet columns A-Z, AA-ZZ
function getSpreadsheetColumns() {
    const cols = [];
    for (let i = 65; i <= 90; i++) cols.push(String.fromCharCode(i));
    for (let i = 65; i <= 90; i++) {
        for (let j = 65; j <= 90; j++) {
            cols.push(String.fromCharCode(i) + String.fromCharCode(j));
        }
    }
    return cols;
}
const spreadsheetColumns = getSpreadsheetColumns();
const dataTypes = ["string", "int", "date", "boolean", "formula"];

// Check if the overall config has File_Type == "Spreadsheet" anywhere at the root
function isSpreadsheetContext() {
    if (!currentConfigData) return false;
    // Search one level deep for File_Type
    for (const key in currentConfigData) {
        if (currentConfigData[key] && typeof currentConfigData[key] === 'object') {
            if (currentConfigData[key]["File_Type"] && currentConfigData[key]["File_Type"].toLowerCase() === "spreadsheet") {
                return true;
            }
        }
    }
    return false;
}

// Creates an individual input field based on smart logic
function createInputForValue(key, value, isSchemaBlock = false) {
    let inputElement;

    const isSpreadsheet = isSpreadsheetContext();

    // Smart Dropdowns
    if (key === "Column" && isSpreadsheet) {
        inputElement = document.createElement('select');
        inputElement.className = "cyber-input config-input-select";
        spreadsheetColumns.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.innerText = col;
            if (col === value) opt.selected = true;
            inputElement.appendChild(opt);
        });
    }
    else if (key === "Type" && isSchemaBlock) {
        inputElement = document.createElement('select');
        inputElement.className = "cyber-input config-input-select";
        dataTypes.forEach(dt => {
            const opt = document.createElement('option');
            opt.value = dt;
            opt.innerText = dt;
            if (dt === value) opt.selected = true;
            inputElement.appendChild(opt);
        });
    }
    else if (key === "Sync_Mode") {
        inputElement = document.createElement('select');
        inputElement.className = "cyber-input config-input-select";
        inputElement.id = "sync-mode-select"; // Used for event listener
        ["Both", "Cloud Only", "Local Only"].forEach(mode => {
            const opt = document.createElement('option');
            opt.value = mode;
            opt.innerText = mode;
            if (mode === value) opt.selected = true;
            inputElement.appendChild(opt);
        });
    }
    else if (key === "Sync_Priority") {
        inputElement = document.createElement('select');
        inputElement.className = "cyber-input config-input-select";
        inputElement.id = "sync-priority-select"; // Used for event listener
        ["Cloud First", "Local First"].forEach(pri => {
            const opt = document.createElement('option');
            opt.value = pri;
            opt.innerText = pri;
            if (pri === value) opt.selected = true;
            inputElement.appendChild(opt);
        });
    }
    else if (key === "Service") {
        inputElement = document.createElement('select');
        inputElement.className = "cyber-input config-input-select";
        inputElement.id = "cloud-service-select"; // Used for event listener
        ["Google Drive", "OneDrive", "Dropbox"].forEach(svc => {
            const opt = document.createElement('option');
            opt.value = svc;
            opt.innerText = svc;
            if (svc === value) opt.selected = true;
            inputElement.appendChild(opt);
        });
    }
    // Standard Inputs
    else if (typeof value === "boolean") {
        inputElement = document.createElement('input');
        inputElement.type = "checkbox";
        inputElement.checked = value;
        inputElement.className = "config-input-boolean";
    } else if (typeof value === "number") {
        inputElement = document.createElement('input');
        inputElement.type = "number";
        inputElement.value = value;
        inputElement.className = "cyber-input config-input-number";
    } else {
        inputElement = document.createElement('input');
        inputElement.type = "text";
        inputElement.value = value || "";
        inputElement.className = "cyber-input config-input-text";
    }

    inputElement.dataset.keyname = key;
    return inputElement;
}

// Renders a generic object (like Cloud_File_Path)
function renderGenericObject(obj, parentElement, isSchemaBlock = false) {
    const container = document.createElement('div');
    container.className = "generic-obj-container";
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "10px";

    for (const key in obj) {
        const wrapper = document.createElement('div');
        wrapper.className = "form-group";
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.gap = "15px";

        const label = document.createElement('label');
        label.innerText = key.replace(/_/g, ' ');
        label.style.color = "var(--neon-cyan)";
        label.style.fontSize = "12px";
        label.style.width = "150px"; // Fixed width for alignment

        const input = createInputForValue(key, obj[key], isSchemaBlock);

        wrapper.appendChild(label);

        // Wrap the input and potential button together to fix flexbox squishing
        const inputWrapper = document.createElement('div');
        inputWrapper.style.display = "flex";
        inputWrapper.style.width = "100%";
        inputWrapper.style.gap = "10px";

        input.style.width = "100%"; // Take up all available space in the new wrapper
        inputWrapper.appendChild(input);

        // Add File Browser Button if it's a file path or credential file
        if (key === "Credentials_File" || key === "File_Path") {
            const browseBtn = document.createElement('button');
            browseBtn.innerText = "BROWSE";
            browseBtn.className = "cyber-btn";
            browseBtn.style.padding = "2px 10px";
            browseBtn.style.fontSize = "10px";
            browseBtn.style.whiteSpace = "nowrap"; // Keep the text on one line so it doesn't break layout

            browseBtn.onclick = async () => {
                try {
                    const selectedFile = await eel.open_file_dialog()();
                    if (selectedFile) {
                        // If it's a credentials file, just extract the filename to keep it clean, otherwise use full path
                        if (key === "Credentials_File") {
                            input.value = selectedFile.split('\\').pop().split('/').pop();
                        } else {
                            input.value = selectedFile;
                        }

                        // Visual confirmation
                        const originalText = browseBtn.innerText;
                        browseBtn.innerText = "[ SELECTED ]";
                        browseBtn.style.color = "#0f0";
                        setTimeout(() => {
                            browseBtn.innerText = originalText;
                            browseBtn.style.color = "";
                        }, 2000);
                    }
                } catch(e) {
                    console.error("File dialog failed", e);
                }
            };
            inputWrapper.appendChild(browseBtn);
        }

        wrapper.appendChild(inputWrapper);
        container.appendChild(wrapper);
    }
    parentElement.appendChild(container);
}

// Renders the highly dynamic "schema" array/object where keys are column names
function renderSchemaBlock(schemaObj, parentElement) {
    const listContainer = document.createElement('div');
    listContainer.className = "schema-list-container";
    listContainer.style.display = "flex";
    listContainer.style.flexDirection = "column";
    listContainer.style.gap = "15px";

    for (const columnName in schemaObj) {
        listContainer.appendChild(createSchemaRow(columnName, schemaObj[columnName]));
    }

    parentElement.appendChild(listContainer);

    // Add New Row Button
    const addBtn = document.createElement('button');
    addBtn.className = "cyber-btn";
    addBtn.innerText = "+ ADD COLUMN DEFINITION";
    addBtn.style.marginTop = "15px";
    addBtn.style.alignSelf = "flex-start";
    addBtn.onclick = () => {
        const newRow = createSchemaRow("New_Column", { "Column": "A", "Type": "string" });
        listContainer.appendChild(newRow);
    };
    parentElement.appendChild(addBtn);
}

function createSchemaRow(columnName, columnData) {
    const row = document.createElement('div');
    row.className = "schema-row";
    row.style.border = "1px solid rgba(255, 0, 127, 0.4)";
    row.style.padding = "10px";
    row.style.borderRadius = "5px";
    row.style.background = "rgba(0,0,0,0.5)";

    // Title Row (Editable Key Name)
    const headerRow = document.createElement('div');
    headerRow.style.display = "flex";
    headerRow.style.justifyContent = "space-between";
    headerRow.style.marginBottom = "10px";

    const nameInput = document.createElement('input');
    nameInput.type = "text";
    nameInput.value = columnName;
    nameInput.className = "cyber-input schema-key-name";
    nameInput.style.fontWeight = "bold";
    nameInput.style.color = "#ff007f";

    const deleteBtn = document.createElement('button');
    deleteBtn.innerText = "X";
    deleteBtn.style.background = "#ff0000";
    deleteBtn.style.color = "#fff";
    deleteBtn.style.border = "none";
    deleteBtn.style.cursor = "pointer";
    deleteBtn.style.padding = "2px 8px";
    deleteBtn.onclick = () => row.remove();

    headerRow.appendChild(nameInput);
    headerRow.appendChild(deleteBtn);
    row.appendChild(headerRow);

    // Data Row
    const dataContainer = document.createElement('div');
    dataContainer.className = "schema-data-container";
    renderGenericObject(columnData, dataContainer, true);
    row.appendChild(dataContainer);

    return row;
}

function renderConfigFields(configObj, parentElement) {
    for (const key in configObj) {
        const value = configObj[key];

        const sectionHeader = document.createElement('h4');
        sectionHeader.innerText = key.replace(/_/g, ' ').toUpperCase();
        sectionHeader.style.marginTop = "20px";
        sectionHeader.style.marginBottom = "10px";
        sectionHeader.style.borderBottom = "1px solid rgba(0, 243, 255, 0.3)";
        sectionHeader.style.color = "var(--neon-cyan)";
        parentElement.appendChild(sectionHeader);

        if (key.toLowerCase() === "schema") {
            renderSchemaBlock(value, parentElement);
        } else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
            renderGenericObject(value, parentElement);
        } else {
            // Root level primitives (fallback)
            const field = document.createElement('div');
            field.className = "root-primitive-container";
            const wrapper = document.createElement('div');
            wrapper.className = "form-group";
            wrapper.style.display = "flex";
            wrapper.style.alignItems = "center";
            wrapper.style.gap = "15px";
            const label = document.createElement('label');
            label.innerText = key;
            label.style.color = "var(--neon-cyan)";
            label.style.width = "150px";
            const input = createInputForValue(key, value);
            wrapper.appendChild(label);
            wrapper.appendChild(input);
            field.appendChild(wrapper);
            parentElement.appendChild(field);
        }
    }
}

function openConfigModal(toolName, configData) {
    currentConfigTool = toolName;
    currentConfigData = configData;

    document.getElementById('tool-config-title').innerText = `Configure Tool: ${toolName.toUpperCase()}`;
    const body = document.getElementById('tool-config-body');
    body.innerHTML = ''; // clear old

    renderConfigFields(configData, body);

    // Add logic specifically for the Order Tracker dropdown links
    const syncModeSelect = document.getElementById('sync-mode-select');
    const syncPrioritySelect = document.getElementById('sync-priority-select');
    const serviceSelect = document.getElementById('cloud-service-select');

    // Auto-fill logic for Google Drive
    if (serviceSelect) {
        serviceSelect.addEventListener('change', (e) => {
            const inputs = body.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                if (input.dataset.keyname === 'File_ID_or_Path') {
                    if (e.target.value === 'Google Drive') {
                        if(input.value === '') input.value = "[Enter Google Sheet ID here]";
                    }
                }
            });
        });
    }

    if (syncModeSelect && syncPrioritySelect) {
        const updateSyncDisabledState = () => {
            const mode = syncModeSelect.value;
            if (mode === "Both") {
                syncPrioritySelect.disabled = false;
                syncPrioritySelect.style.opacity = "1";
                if(serviceSelect) {
                    serviceSelect.disabled = false;
                    serviceSelect.style.opacity = "1";
                }
            } else if (mode === "Cloud Only") {
                syncPrioritySelect.disabled = true;
                syncPrioritySelect.style.opacity = "0.5";
                if(serviceSelect) {
                    serviceSelect.disabled = false;
                    serviceSelect.style.opacity = "1";
                }
            } else if (mode === "Local Only") {
                syncPrioritySelect.disabled = true;
                syncPrioritySelect.style.opacity = "0.5";
                if(serviceSelect) {
                    serviceSelect.disabled = true;
                    serviceSelect.style.opacity = "0.5";
                }
            }
        };
        syncModeSelect.addEventListener('change', updateSyncDisabledState);
        updateSyncDisabledState(); // initial evaluation
    }

    document.getElementById('tool-config-modal').style.display = 'flex';
}

// Ensure the UI has access to it globally
window.openConfigModal = openConfigModal;

// Save button logic for Config Modal
document.getElementById('save-config-btn').addEventListener('click', async () => {
    if (!currentConfigTool || !currentConfigData) return;

    let newConfig = {};

    // Reconstruction from DOM
    const body = document.getElementById('tool-config-body');

    // Loop through all major sections (h4 tags denote sections)
    const sections = body.querySelectorAll('h4');
    let currentSectionNode = body.firstElementChild;

    while (currentSectionNode) {
        if (currentSectionNode.tagName === 'H4') {
            // Find original key by case-insensitive matching
            const displayKey = currentSectionNode.innerText.toLowerCase().replace(/ /g, '_');
            let realKey = Object.keys(currentConfigData).find(k => k.toLowerCase() === displayKey) || currentSectionNode.innerText.replace(/ /g, '_');

            const dataContainer = currentSectionNode.nextElementSibling;

            if (dataContainer.classList.contains('schema-list-container')) {
                // It's a schema block
                newConfig[realKey] = {};
                const rows = dataContainer.querySelectorAll('.schema-row');
                rows.forEach(row => {
                    const keyName = row.querySelector('.schema-key-name').value.trim();
                    if (!keyName) return; // Skip empty keys

                    const rowData = {};
                    const inputs = row.querySelectorAll('.schema-data-container input, .schema-data-container select');
                    inputs.forEach(input => {
                        const subKey = input.dataset.keyname;
                        let val = input.value;
                        if (input.type === 'checkbox') val = input.checked;
                        if (input.type === 'number') val = parseFloat(input.value);
                        rowData[subKey] = val;
                    });
                    newConfig[realKey][keyName] = rowData;
                });
            } else if (dataContainer.classList.contains('generic-obj-container')) {
                // It's a standard object block
                newConfig[realKey] = {};
                const inputs = dataContainer.querySelectorAll('input, select');
                inputs.forEach(input => {
                    const subKey = input.dataset.keyname;
                    let val = input.value;
                    if (input.type === 'checkbox') val = input.checked;
                    if (input.type === 'number') val = parseFloat(input.value);
                    newConfig[realKey][subKey] = val;
                });
            } else if (dataContainer.classList.contains('root-primitive-container')) {
                 // It's a root primitive
                 const input = dataContainer.querySelector('input, select');
                 if(input) {
                     let val = input.value;
                     if (input.type === 'checkbox') val = input.checked;
                     if (input.type === 'number') val = parseFloat(input.value);
                     newConfig[realKey] = val;
                 }
            } else {
                 // Fallback
                 if(dataContainer.classList.contains('form-group')){
                     const input = dataContainer.querySelector('input, select');
                     if(input) {
                         let val = input.value;
                         if (input.type === 'checkbox') val = input.checked;
                         if (input.type === 'number') val = parseFloat(input.value);
                         newConfig[realKey] = val;
                     }
                 }
            }
        }
        currentSectionNode = currentSectionNode.nextElementSibling;
    }

    // Deep merge with currentConfigData to preserve fields that weren't rendered (just in case)
    const finalConfig = Object.assign({}, currentConfigData, newConfig);

    // Send to backend
    const success = await eel.save_tool_config(currentConfigTool, finalConfig)();
    if (success) {
        document.getElementById('tool-config-modal').style.display = 'none';
        // Alert user visually
        const btn = document.getElementById('save-config-btn');
        const originalText = btn.innerText;
        btn.innerText = "SAVED!";
        btn.style.color = "#0f0";
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.color = "";
        }, 2000);
    } else {
        alert("Failed to save configuration.");
    }
});

});


eel.expose(streamAIToken);
function streamAIToken(token) {
    const aiMessages = document.querySelectorAll('.ai-message');
    if (aiMessages.length > 0) {
        const lastMessage = aiMessages[aiMessages.length - 1];
        lastMessage.innerHTML += token.replace(/\n/g, '<br>');
        const chatBox = document.getElementById('chat-history');
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

eel.expose(streamAIComplete);
function streamAIComplete() {
    isProcessing = false;
    document.getElementById('input-text').disabled = false;
    document.getElementById('input-text').focus();
}

eel.expose(syncStreamerModeUI, "sync_streamer_mode_ui");
function syncStreamerModeUI(isEnabled, safeTools) {
    const checkbox = document.getElementById('streamer-mode-toggle');
    if (checkbox) checkbox.checked = isEnabled;

    // safeTools is a list of tool names that are safe
    // If we have a list of tools rendered, we should update their checkboxes
    const toolItems = document.querySelectorAll('.tool-item');
    toolItems.forEach(item => {
        const toolName = item.dataset.toolname;
        const toggle = item.querySelector('.stream-safe-toggle');
        if (toggle && toolName) {
            toggle.checked = safeTools.includes(toolName);
        }
    });
}

eel.expose(setSystemStatus);
function setSystemStatus(status) {
    const orb = document.querySelector('.nova-orb');
    if (!orb) return;

    if (status === "idle") {
        orb.style.boxShadow = "0 0 20px var(--neon-cyan), inset 0 0 20px var(--neon-cyan)";
    } else if (status === "thinking" || status === "talking") {
        orb.style.boxShadow = "0 0 30px var(--neon-purple), inset 0 0 30px var(--neon-purple)";
    } else if (status === "error") {
        orb.style.boxShadow = "0 0 20px #ff0000, inset 0 0 20px #ff0000";
    }
}
