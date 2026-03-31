import { state, DOM } from './state.js';

export function showProgress(show = true) {
    if (show) DOM.progressBar.classList.remove('progress-hidden');
    else DOM.progressBar.classList.add('progress-hidden');
}

export function scrollToBottom() {
    DOM.chatWindow.scrollTo({
        top: DOM.chatWindow.scrollHeight,
        behavior: 'smooth'
    });
}

export function appendMessage(role, content, isImage = false, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message ${isImage ? 'image-msg' : ''} ${isError ? 'error-msg' : ''}`;
    
    if (isImage) {
        msgDiv.innerHTML = `<img src="${content}" alt="Generated Image" style="width: 100%; border-radius: 12px; border: 1px solid var(--glass-border); margin-top: 10px; cursor: pointer;">`;
        msgDiv.onclick = () => window.open(content, '_blank');
    } else {
        // Simple Markdown-ish escaping for now, but handle code blocks similarly to before
        msgDiv.textContent = content;
        if (content.includes('```')) {
             const parts = content.split('```');
             let formatted = '';
             for (let i = 0; i < parts.length; i++) {
                 if (i % 2 === 1) formatted += `<pre><code>${parts[i]}</code></pre>`;
                 else formatted += parts[i].replace(/\n/g, '<br>');
             }
             msgDiv.innerHTML = formatted;
        } else {
             msgDiv.innerHTML = content.replace(/\n/g, '<br>');
        }
    }
    
    DOM.chatWindow.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

export function setGenerating(generating = true) {
    state.isGenerating = generating;
    DOM.sendBtn.disabled = generating;
    DOM.stopBtn.textContent = generating ? 'Stop' : 'New';
    // Ensure stop button is never disabled as it now doubles as 'New'
    DOM.stopBtn.disabled = false;
    showProgress(generating);
    if (!generating) DOM.userInput.focus();
}

/**
 * Mobile Sidebar Toggle Logic
 */
export function toggleSidebar(force = null) {
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    
    const active = force !== null ? force : !sidebar.classList.contains('active');
    
    if (active) {
        sidebar.classList.add('active');
        backdrop.classList.add('active');
    } else {
        sidebar.classList.remove('active');
        backdrop.classList.remove('active');
    }
}
