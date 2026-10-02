import re

with open("web/main.js", "r") as f:
    js = f.read()

# We need to replace the aiToolsContainer section to add the Stream Safe toggle and Config button.

search_block = """                // 2. AI Tool Checkbox (Tools Tab)
                if (aiToolsContainer) {
                    const aiLabel = document.createElement('label');
                    aiLabel.className = "cyber-checkbox-container";

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
                    aiToolsContainer.appendChild(aiLabel);

                    const savedAiVal = localStorage.getItem(`nova_ai_tool_${toolName}`);
                    aiCheckbox.checked = savedAiVal === null ? true : (savedAiVal === 'true');

                    aiCheckbox.addEventListener('change', () => {
                        localStorage.setItem(`nova_ai_tool_${toolName}`, aiCheckbox.checked);
                        syncAIToolsPrefs(availableTools);
                    });
                }"""

replace_block = """                // 2. AI Tool Checkbox (Tools Tab)
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

                    // Fetch existing lock state from localStorage
                    const isSafe = localStorage.getItem(`nova_stream_safe_${toolName}`) === 'true';
                    safeCheckbox.checked = isSafe;

                    // Sync initial state to backend
                    try { eel.set_tool_stream_safe(toolName, isSafe)(); } catch(e){}

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
                        localStorage.setItem(`nova_stream_safe_${toolName}`, safeCheckbox.checked);
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
                }"""

new_js = js.replace(search_block, replace_block)

modal_logic = """

    // --- Dynamic Config Modal Logic ---
    let currentConfigTool = null;
    let currentConfigData = null;

    function createInputForValue(keyPath, value) {
        const wrapper = document.createElement('div');
        wrapper.className = "form-group";
        wrapper.style.marginBottom = "15px";

        const label = document.createElement('label');
        label.innerText = keyPath.replace(/_/g, ' ');
        label.style.display = "block";
        label.style.marginBottom = "5px";
        label.style.color = "var(--neon-cyan)";
        label.style.fontSize = "12px";
        wrapper.appendChild(label);

        let inputElement;

        if (typeof value === "boolean") {
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

        inputElement.dataset.keypath = keyPath;
        wrapper.appendChild(inputElement);
        return wrapper;
    }

    function renderConfigFields(configObj, parentElement, parentKey = "") {
        for (const key in configObj) {
            const currentPath = parentKey ? `${parentKey}.${key}` : key;
            const value = configObj[key];

            if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
                // It's a nested object (like Cloud_File_Path)
                const sectionHeader = document.createElement('h4');
                sectionHeader.innerText = key.replace(/_/g, ' ').toUpperCase();
                sectionHeader.style.marginTop = "20px";
                sectionHeader.style.marginBottom = "10px";
                sectionHeader.style.borderBottom = "1px solid rgba(255,0,127,0.3)";
                sectionHeader.style.color = "#ff007f";
                parentElement.appendChild(sectionHeader);

                // Recurse
                renderConfigFields(value, parentElement, currentPath);
            } else {
                // Primitive value
                const field = createInputForValue(currentPath, value);
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

        document.getElementById('tool-config-modal').style.display = 'flex';
    }

    // Save button logic for Config Modal
    document.getElementById('save-config-btn').addEventListener('click', async () => {
        if (!currentConfigTool || !currentConfigData) return;

        // Deep copy the original data structure
        let updatedConfig = JSON.parse(JSON.stringify(currentConfigData));

        // Helper to set nested value by dot path
        const setNestedValue = (obj, path, val) => {
            const keys = path.split('.');
            let current = obj;
            for (let i = 0; i < keys.length - 1; i++) {
                current = current[keys[i]];
            }
            current[keys[keys.length - 1]] = val;
        };

        // Gather all inputs
        const body = document.getElementById('tool-config-body');
        const inputs = body.querySelectorAll('input');

        inputs.forEach(input => {
            const path = input.dataset.keypath;
            let val;
            if (input.type === 'checkbox') {
                val = input.checked;
            } else if (input.type === 'number') {
                val = parseFloat(input.value);
            } else {
                val = input.value;
            }
            setNestedValue(updatedConfig, path, val);
        });

        // Send to backend
        const success = await eel.save_tool_config(currentConfigTool, updatedConfig)();
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

"""

# Append modal logic to bottom of DOMContentLoaded block (right before the final closing tag for the event listener if possible)
# A safer way is to just append it to the end of the file.
new_js = new_js + modal_logic

with open("web/main.js", "w") as f:
    f.write(new_js)
