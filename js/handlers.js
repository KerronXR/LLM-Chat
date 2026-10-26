import { state, DOM } from './state.js';
import { fetchWithAbort } from './api.js';
import { setGenerating, appendMessage, showProgress, updateImageMessage, scrollToBottom } from './ui.js';
import { updateContextUI } from './state.js';
import { saveHistory } from './api.js';


export async function handleSend() {
    if (state.isGenerating) return;
    const text = DOM.userInput.value.trim();
    const attachedFile = state.attachedFile;
    if (!text && !attachedFile) return;

    setGenerating(true);
    const messageText = text || getDefaultAttachmentPrompt(attachedFile);
    const userMessage = await buildUserMessage(messageText, attachedFile);
    
    // Clear input
    DOM.userInput.value = '';
    
    // Add user message
    appendMessage('user', userMessage);
    state.messages.push(userMessage);
    await saveHistory(state.messages);
    
    await handleLlmGeneration(attachedFile);
}

export async function handleAttachmentSelect() {
    DOM.chatAttachment.click();
}

export async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;

    state.attachedFile = file;
    DOM.attachmentPreview.innerHTML = '';
    DOM.attachmentPreview.classList.remove('attachment-preview-hidden');

    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            DOM.attachmentPreview.appendChild(img);
            addRemoveButton();
        };
        reader.readAsDataURL(file);
    } else {
        const chip = document.createElement('div');
        chip.className = 'file-chip';
        chip.innerHTML = `<span>📄 ${file.name}</span>`;
        DOM.attachmentPreview.appendChild(chip);
        addRemoveButton();
    }
}

function addRemoveButton() {
    const removeBtn = document.createElement('span');
    removeBtn.innerHTML = '×';
    removeBtn.style.cursor = 'pointer';
    removeBtn.style.marginLeft = '10px';
    removeBtn.style.fontSize = '1.2rem';
    removeBtn.onclick = clearAttachment;
    DOM.attachmentPreview.appendChild(removeBtn);
}

export function clearAttachment() {
    state.attachedFile = null;
    DOM.chatAttachment.value = '';
    DOM.attachmentPreview.classList.add('attachment-preview-hidden');
    DOM.attachmentPreview.innerHTML = '';
}

async function handleLlmGeneration(file = null) {
    state.abortController = new AbortController();
    
    let fileData = null;
    if (file) {
        if (file.type.startsWith('image/')) {
            fileData = await buildImageAttachmentPayload(file);
        } else {
            fileData = { type: 'file', name: file.name, content: await fileToText(file) };
        }
    }
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: DOM.modelSelect.value,
                messages: serializeMessagesForApi(state.messages),
                stream: true,
                attachment: fileData
            }),
            signal: state.abortController.signal
        });
        
        if (response.status === 401) { window.location.href = '/login.html'; return; }
        if (!response.ok) throw new Error('Generation failed');
        
        clearAttachment();
        
        const aiMsgDiv = appendMessage('ai', '...');
        let aiContent = '';
        let streamError = null;
        let liveTps = 0;

        // Live TPS indicator
        const tpsLive = document.createElement('div');
        tpsLive.className = 'tps-live';
        tpsLive.textContent = '⏳ generating...';
        aiMsgDiv.appendChild(tpsLive);
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let lineBuf = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            lineBuf += decoder.decode(value, { stream: true });
            const parts = lineBuf.split('\n');
            // Last element may be incomplete — keep in buffer
            lineBuf = parts.pop();

            for (let line of parts) {
                line = line.trim();
                if (!line || !line.startsWith('data: ')) continue;
                const jsonStr = line.substring(6).trim();
                if (!jsonStr) continue;
                
                let json;
                try {
                    json = JSON.parse(jsonStr);
                } catch (e) {
                    console.error('Parse error:', e, jsonStr);
                    continue;
                }

                if (json.error) {
                    streamError = json.error;
                }
                if (json.message) {
                    aiContent += json.message.content;
                    // Re-render text portion only
                    const textNode = aiMsgDiv.querySelector('.message-text') || aiMsgDiv;
                    if (textNode === aiMsgDiv) {
                        // First content — rebuild structure
                        aiMsgDiv.innerHTML = '';
                        const tb = document.createElement('div');
                        tb.className = 'message-text';
                        aiMsgDiv.appendChild(tb);
                        aiMsgDiv.appendChild(tpsLive);
                    }
                    const tb = aiMsgDiv.querySelector('.message-text');
                    tb.innerHTML = formatAiContent(aiContent);
                    scrollToBottom();
                }
                if (typeof json.tps === 'number') {
                    liveTps = json.tps;
                    tpsLive.textContent = `⚡ ${liveTps} tok/s`;
                }
                if (json.done) {
                    // Remove live indicator
                    tpsLive.remove();

                    if (streamError) {
                        throw new Error(streamError);
                    }
                    state.messages.push({ role: 'assistant', content: aiContent });
                    state.contextSize = json.prompt_eval_count + json.eval_count;
                    state.maxContext = json.context_length || 8192;
                    document.getElementById('current-context').textContent = state.contextSize;
                    document.getElementById('max-context').textContent = state.maxContext;

                    // Stamp final TPS badge
                    if (typeof json.avg_tps === 'number' && json.avg_tps > 0) {
                        const badge = document.createElement('div');
                        badge.className = 'tps-badge';
                        badge.textContent = `⚡ ${json.avg_tps} tok/s`;
                        aiMsgDiv.appendChild(badge);
                    }
                    
                    await saveHistory(state.messages);
                    try { await reader.cancel(); } catch (e) {}
                    return;
                }
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') {
             appendMessage('ai', '[Generation Stopped]', false, true);
        } else {
             appendMessage('ai', 'Error: ' + err.message, false, true);
        }
    } finally {
        setGenerating(false);
    }
}

function formatAiContent(content) {
    if (content.includes('```')) {
        const parts = content.split('```');
        let formatted = '';
        for (let i = 0; i < parts.length; i++) {
            if (i % 2 === 1) formatted += `<pre><code>${parts[i]}</code></pre>`;
            else formatted += parts[i].replace(/\n/g, '<br>');
        }
        return formatted;
    }
    return content.replace(/\n/g, '<br>');
}



export async function handleClearChat() {
    DOM.chatWindow.innerHTML = '';
    state.messages = [];
    state.contextSize = 0;
    updateContextUI();
    appendMessage('ai', 'Chat cleared.');
    await saveHistory(state.messages);
}

export function handleStopOrNew() {
    if (state.isGenerating) {
        if (state.abortController) {
            state.abortController.abort();
        }
        setGenerating(false);
    } else {
        handleClearChat();
    }
}

export function handleExport() {
    if (state.messages.length === 0) {
        appendMessage('ai', 'Chat is empty, nothing to export.', false, true);
        return;
    }
    
    // Format messages as human-readable text
    let exportText = "--- Veloxify AI Conversation Export ---\n";
    exportText += `Date: ${new Date().toLocaleString()}\n\n`;
    
    state.messages.forEach(msg => {
        const role = msg.role === 'user' ? 'User' : 'AI';
        exportText += `${role}: ${msg.content}\n\n`;
    });
    
    const blob = new Blob([exportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `veloxify_conversation_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
async function fileToB64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function fileToText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

async function fileToDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function buildImageAttachmentPayload(file) {
    const normalized = await normalizeImageForModel(file);
    return {
        type: 'image',
        data: normalized.dataUrl.split(',')[1],
        mimeType: normalized.mimeType
    };
}

async function normalizeImageForModel(file) {
    const sourceDataUrl = await fileToDataUrl(file);
    const img = await loadImageElement(sourceDataUrl);
    
    // Scale down to max 768px to prevent CPU vision overload
    const MAX_DIM = 768;
    let width = img.naturalWidth || img.width;
    let height = img.naturalHeight || img.height;
    if (width > MAX_DIM || height > MAX_DIM) {
        if (width > height) {
            height = Math.round((height * MAX_DIM) / width);
            width = MAX_DIM;
        } else {
            width = Math.round((width * MAX_DIM) / height);
            height = MAX_DIM;
        }
    }

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not prepare image for analysis.');

    // Flatten onto white so transparent PNG/WebP inputs become a stable JPEG.
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(img, 0, 0, width, height);

    const convertedDataUrl = canvas.toDataURL('image/jpeg', 0.85);
    return {
        dataUrl: convertedDataUrl,
        mimeType: 'image/jpeg'
    };
}

async function loadImageElement(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Unsupported image format.'));
        img.src = src;
    });
}

async function buildUserMessage(text, file) {
    const message = { role: 'user', content: text };
    if (!file) return message;

    message.attachment = {
        name: file.name,
        type: file.type || 'application/octet-stream',
        kind: file.type.startsWith('image/') ? 'image' : 'file'
    };

    if (message.attachment.kind === 'image') {
        const normalized = await normalizeImageForModel(file);
        message.attachment.dataUrl = normalized.dataUrl;
        message.attachment.type = normalized.mimeType;
    }

    return message;
}

export async function ensureJpegDataUrl(dataUrl) {
    if (!dataUrl) return dataUrl;
    try {
        const img = await loadImageElement(dataUrl);
        const MAX_DIM = 768;
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;
        if (width > MAX_DIM || height > MAX_DIM) {
            if (width > height) {
                height = Math.round((height * MAX_DIM) / width);
                width = MAX_DIM;
            } else {
                width = Math.round((width * MAX_DIM) / height);
                height = MAX_DIM;
            }
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return dataUrl;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);
        return canvas.toDataURL('image/jpeg', 0.85);
    } catch (e) {
        return dataUrl;
    }
}

function serializeMessagesForApi(messages) {
    return messages.map((msg) => {
        if (Array.isArray(msg.content)) {
            return { role: msg.role, content: msg.content };
        }
        if (msg.role === 'user' && msg.attachment && msg.attachment.kind === 'image' && msg.attachment.dataUrl) {
            return {
                role: msg.role,
                content: [
                    { type: 'image', image: msg.attachment.dataUrl },
                    { type: 'text', text: msg.content }
                ]
            };
        }
        return { role: msg.role, content: msg.content };
    });
}

function getDefaultAttachmentPrompt(file) {
    if (!file) return '';
    return file.type.startsWith('image/')
        ? 'Please analyze this attached image.'
        : `Please analyze the attached file: ${file.name}`;
}
