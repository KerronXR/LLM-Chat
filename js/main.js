import { state, DOM, updateContextUI } from './state.js';
import { handleSend, handleStopOrNew, handleClearChat, handleExport, handleFileChange } from './handlers.js';
import { setGenerating, toggleSidebar, appendMessage } from './ui.js';

import { savePersona, getHistory, getPersona, logout } from './api.js';

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
        // Deduplicate history by comparing roles and content
        const uniqueHistory = [];
        const seen = new Set();
        history.forEach(msg => {
            const key = `${msg.role}:${msg.content}`;
            if (!seen.has(key)) {
                seen.add(key);
                uniqueHistory.push(msg);
            }
        });
        
        state.messages = uniqueHistory;
        DOM.chatWindow.innerHTML = '';
        state.messages.forEach(msg => {
            const contentText = typeof msg.content === 'string' ? msg.content : '';
            const isImage = contentText.startsWith('Images generated:') || contentText.startsWith('Image generated:');
            
            let content = msg;
            if (contentText.startsWith('Images generated: ')) content = contentText.replace('Images generated: ', '').split(', ');
            else if (contentText.startsWith('Image generated: ')) content = contentText.replace('Image generated: ', '');
            
            appendMessage(msg.role === 'user' ? 'user' : 'ai', content, isImage);
        });
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

function updateSystemPrompt(model) {
    if (model.includes('gemma')) {
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

// Initial UI state
updateContextUI();

