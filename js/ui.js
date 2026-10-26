import { state, DOM } from './state.js';
import { renderMarkdown } from './markdown.js';

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

export function updateImageMessage(msgDiv, urls) {
    let html = '<div class="image-grid">';
    urls.forEach(url => {
        html += `
            <div class="image-container">
                <img src="${url}" alt="Generated Image">
                <button class="upscale-btn" data-url="${url}">
                    <span>✨ Upscale</span>
                </button>
            </div>`;
    });
    html += '</div>';
    msgDiv.innerHTML = html;

    // Add event listeners for images and upscale buttons
    msgDiv.querySelectorAll('.image-container img').forEach(img => {
        img.onclick = () => window.open(img.src, '_blank');
    });
    
    msgDiv.querySelectorAll('.upscale-btn').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            const path = btn.getAttribute('data-url');
            const event = new CustomEvent('upscale-request', { detail: { path, btn } });
            window.dispatchEvent(event);
        };
    });
}

export function appendMessage(role, content, isImage = false, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message ${isImage ? 'image-msg' : ''} ${isError ? 'error-msg' : ''}`;
    
    if (isImage) {
        const urls = Array.isArray(content) ? content : [content];
        updateImageMessage(msgDiv, urls);
    } else {
        renderMessageContent(msgDiv, content);
    }
    
    DOM.chatWindow.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function renderMessageContent(container, content) {
    const normalized = typeof content === 'object' && content !== null
        ? content
        : { content: String(content ?? '') };

    if (normalized.content) {
        const textBlock = document.createElement('div');
        textBlock.className = 'message-text';
        textBlock.innerHTML = renderMarkdown(normalized.content);
        container.appendChild(textBlock);
    }

    if (normalized.attachment) {
        container.appendChild(buildAttachmentNode(normalized.attachment));
    }
}

function formatMessageText(content) {
    return renderMarkdown(content);
}

function buildAttachmentNode(attachment) {
    if (attachment.kind === 'image' && attachment.dataUrl) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-attachment message-attachment-image';

        const img = document.createElement('img');
        img.src = attachment.dataUrl;
        img.alt = attachment.name || 'Attached image';
        img.onclick = () => window.open(attachment.dataUrl, '_blank');
        wrapper.appendChild(img);
        return wrapper;
    }

    const fileChip = document.createElement('div');
    fileChip.className = 'message-attachment message-attachment-file';
    fileChip.textContent = `Attached: ${attachment.name || 'File'}`;
    return fileChip;
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
