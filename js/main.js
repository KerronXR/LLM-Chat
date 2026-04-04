import { state, DOM, updateContextUI } from './state.js';
import { handleSend, handleStopOrNew, handleClearChat, handleExport } from './handlers.js';
import { setGenerating, toggleSidebar, appendMessage } from './ui.js';

import { savePersona, getHistory, logout } from './api.js';

// Init
// Add mobile toggle elements to DOM
if (!document.getElementById('mobile-toggle')) {
    const toggle = document.createElement('div');
    toggle.id = 'mobile-toggle';
    toggle.innerHTML = '☰';
    document.body.appendChild(toggle);
    DOM.mobileToggle = toggle;
    
    const backdrop = document.createElement('div');
    backdrop.id = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
    DOM.sidebarBackdrop = backdrop;
    
    toggle.onclick = () => toggleSidebar();
    backdrop.onclick = () => toggleSidebar(false);
}

// Load history
getHistory().then(history => {
    if (history && history.length > 0) {
        state.messages = history;
        DOM.chatWindow.innerHTML = '';
        state.messages.forEach(msg => {
            const isBatch = msg.content.startsWith('Images generated:');
            const isSingle = msg.content.startsWith('Image generated:');
            const isImage = isBatch || isSingle;
            
            let content = msg.content;
            if (isBatch) content = msg.content.replace('Images generated: ', '').split(', ');
            else if (isSingle) content = msg.content.replace('Image generated: ', '');
            
            appendMessage(msg.role === 'user' ? 'user' : 'ai', content, isImage);
        });
    }
});

// Logout handling
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) logoutBtn.onclick = logout;

// Send message handling
DOM.sendBtn.onclick = handleSend;
DOM.userInput.onkeydown = (e) => {
    if (e.key === 'Enter') handleSend();
};

DOM.stopBtn.onclick = handleStopOrNew;
DOM.clearBtn.onclick = handleClearChat;
DOM.exportBtn.onclick = handleExport;

function updateSystemPrompt(model) {
    if (model.includes('dolphin')) {
         DOM.systemPrompt.value = "You are Dolphin, a helpful uncensored AI assistant.";
    } else if (model.includes('gemma')) {
         DOM.systemPrompt.value = "You are Gemma, a helpful AI assistant.";
    } else if (model.includes('qwen')) {
         DOM.systemPrompt.value = "You are a helpful and capable AI assistant.";
    } else {
         DOM.systemPrompt.value = "You are a helpful AI assistant.";
    }
}

DOM.modelSelect.onchange = (e) => updateSystemPrompt(e.target.value);

// Initial prompt state
updateSystemPrompt(DOM.modelSelect.value);

DOM.savePersonaBtn.onclick = async () => {
    const result = await savePersona(DOM.systemPrompt.value);
    if (result) {
        DOM.savePersonaBtn.textContent = 'Saved!';
        setTimeout(() => DOM.savePersonaBtn.textContent = 'Save Persona', 2000);
    }
};

// Image Upload Handling
DOM.uploadBtn.onclick = () => DOM.imageUpload.click();
DOM.imageUpload.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (re) => {
            DOM.imagePreview.src = re.target.result;
            DOM.imagePreviewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
};

DOM.removeImageBtn.onclick = () => {
    DOM.imageUpload.value = '';
    DOM.imagePreview.src = '';
    DOM.imagePreviewContainer.style.display = 'none';
};

DOM.batchSizeSlider.oninput = (e) => {
    DOM.batchSizeValue.textContent = e.target.value;
};

// Initial UI state
updateContextUI();

// Register upscale request listener
window.addEventListener('upscale-request', async (e) => {
    const { path, btn } = e.detail;
    const { handleUpscale } = await import('./handlers.js');
    handleUpscale(path, btn);
});
