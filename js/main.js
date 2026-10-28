import { state, DOM, updateContextUI } from './state.js';
import { handleSend, handleStopOrNew, handleClearChat, handleExport, handleFileChange, clearAttachment, ensureJpegDataUrl } from './handlers.js';
import { initClipboardPasteHandler } from './attachments.js';
import { handleToggleWebSearch } from './search.js';
import { setGenerating, toggleSidebar, appendMessage, requestWakeLock } from './ui.js';

import { savePersona, getHistory, getPersona, logout } from './api.js';

initClipboardPasteHandler();

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

export function renderMessages(messages) {
    DOM.chatWindow.innerHTML = '';
    messages.forEach(msg => {
        const contentText = typeof msg.content === 'string' ? msg.content : '';
        const isImage = contentText.startsWith('Images generated:') || contentText.startsWith('Image generated:');
        let content = msg;
        if (contentText.startsWith('Images generated: ')) content = contentText.replace('Images generated: ', '').split(', ');
        else if (contentText.startsWith('Image generated: ')) content = contentText.replace('Image generated: ', '');
        appendMessage(msg.role === 'user' ? 'user' : 'ai', content, isImage);
    });
}

// Load history
getHistory().then(async history => {
    if (history && history.length > 0) {
        const uniqueHistory = [];
        const seen = new Set();
        for (const msg of history) {
            const key = `${msg.role}:${msg.content}`;
            if (!seen.has(key)) {
                seen.add(key);
                if (msg.attachment && msg.attachment.dataUrl && !msg.attachment.dataUrl.startsWith('data:image/jpeg')) {
                    msg.attachment.dataUrl = await ensureJpegDataUrl(msg.attachment.dataUrl);
                    msg.attachment.type = 'image/jpeg';
                }
                uniqueHistory.push(msg);
            }
        }
        state.messages = uniqueHistory;
        renderMessages(state.messages);
    }
});

getPersona().then(persona => {
    if (persona) {
        DOM.systemPrompt.value = persona;
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

// Attachment listeners
DOM.attachBtn.addEventListener('click', () => DOM.chatAttachment.click());
DOM.chatAttachment.addEventListener('change', handleFileChange);

// Web search toggle listener
if (DOM.webSearchBtn) DOM.webSearchBtn.onclick = handleToggleWebSearch;

function updateSystemPrompt(model) {
    if (model.includes('gemma')) {
         DOM.systemPrompt.value = "You are Gemma, a helpful AI assistant.";
    } else if (model.includes('qwen')) {
         DOM.systemPrompt.value = "You are a helpful and capable AI assistant.";
    } else {
         DOM.systemPrompt.value = "You are a helpful AI assistant.";
    }
}

function updateModelCapabilities(model) {
    const lower = (model || '').toLowerCase();
    const supportsVision = lower.includes('gemma') || lower.includes('-vl') || lower.includes('vl-') || lower.includes('vision');
    DOM.attachBtn.style.display = supportsVision ? 'flex' : 'none';
    if (!supportsVision && (state.attachedFile || (state.attachedFiles && state.attachedFiles.length > 0))) {
        clearAttachment();
    }
}

DOM.modelSelect.onchange = (e) => {
    state.activeModel = e.target.value;
    updateSystemPrompt(e.target.value);
    updateModelCapabilities(e.target.value);
};

// Initial state
updateSystemPrompt(DOM.modelSelect.value);
updateModelCapabilities(DOM.modelSelect.value);

DOM.savePersonaBtn.onclick = async () => {
    const result = await savePersona(DOM.systemPrompt.value);
    if (result) {
        DOM.savePersonaBtn.textContent = 'Saved!';
        setTimeout(() => DOM.savePersonaBtn.textContent = 'Save Persona', 2000);
    }
};

// Initial UI state
updateContextUI();

// Sync state on visibility change (phone unlock / tab reactivation)
document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible') {
        if (state.isGenerating) {
            requestWakeLock();
        } else {
            try {
                // Fetch latest conversation from /api/history
                const history = await getHistory();
                if (Array.isArray(history) && history.length > state.messages.length) {
                    state.messages = history;
                    renderMessages(history);
                }
            } catch (e) {}
        }
    }
});
