import { state, DOM } from './state.js';
import { fetchWithAbort, generateImage } from './api.js';
import { setGenerating, appendMessage, showProgress, updateImageMessage } from './ui.js';
import { updateContextUI } from './state.js';
import { saveHistory } from './api.js';


export async function handleSend() {
    const text = DOM.userInput.value.trim();
    const attachedFile = state.attachedFile;
    if ((!text && !attachedFile) || state.isGenerating) return;

    const messageText = text || getDefaultAttachmentPrompt(attachedFile);
    const userMessage = await buildUserMessage(messageText, attachedFile);
    
    // Clear input
    DOM.userInput.value = '';
    
    // Add user message
    appendMessage('user', userMessage);
    state.messages.push(userMessage);
    await saveHistory(state.messages);
    
    setGenerating(true);
    
    if (DOM.autoImageCheckbox.checked) {
        await handleImageGeneration(messageText);
    } else {
        await handleLlmGeneration(attachedFile);
    }
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

function clearAttachment() {
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
        
        clearAttachment(); // Clear preview on successful send
        
        const aiMsgDiv = appendMessage('ai', '...');
        let aiContent = '';
        let streamError = null;
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.trim()) continue;
                let json;
                try {
                    json = JSON.parse(line);
                } catch (e) {
                    console.error('Parse error:', e, line);
                    continue;
                }

                if (json.error) {
                    streamError = json.error;
                }
                if (json.message) {
                    aiContent += json.message.content;
                    aiMsgDiv.innerHTML = aiContent.replace(/\n/g, '<br>');
                }
                if (json.done) {
                    if (streamError) {
                        throw new Error(streamError);
                    }
                    state.messages.push({ role: 'assistant', content: aiContent });
                    state.contextSize = json.prompt_eval_count + json.eval_count;
                    state.maxContext = json.context_length || 8192;
                    document.getElementById('current-context').textContent = state.contextSize;
                    document.getElementById('max-context').textContent = state.maxContext;
                    
                    // Save history after AI response
                    await saveHistory(state.messages);
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

async function handleImageGeneration(prompt) {
    state.abortController = new AbortController();
    let aiMsgDiv = null;
    let urls = [];
    
    try {
        const resolution = DOM.imageSizeSelect.value.split('x');
        const width = parseInt(resolution[0]);
        const height = parseInt(resolution[1]);
        const batch_size = parseInt(DOM.batchSizeSlider.value);
        const init_image = DOM.imagePreviewContainer.style.display !== 'none' ? DOM.imagePreview.src : null;
        
        const response = await generateImage(prompt, { width, height, batch_size, init_image });
        if (!response) return;
        
        if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(`Server returned error (${response.status}): ${errorBody}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // Handle both \r\n and \n line endings for robustness
            const lines = buffer.split(/\r?\n/);
            buffer = lines.pop(); // Keep the last partial line
            
            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const json = JSON.parse(line);
                    if (json.url) {
                        urls.push(json.url);
                        if (!aiMsgDiv) {
                            aiMsgDiv = appendMessage('ai', urls, true);
                        } else {
                            updateImageMessage(aiMsgDiv, urls);
                        }
                    }
                    if (json.done) {
                        state.messages.push({ role: 'assistant', content: `Images generated: ${urls.join(', ')}` });
                        await saveHistory(state.messages);
                    }
                    if (json.error) throw new Error(json.error);
                } catch (e) {
                    console.error('JSON Parse error in stream:', e, line);
                }
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            appendMessage('ai', '[Generation Stopped]', false, true);
        } else {
            console.error('Image generation error:', err);
            appendMessage('ai', 'Image generation error: ' + err.message, false, true);
        }
    } finally {
        setGenerating(false);
    }
}

export async function handleUpscale(path, btn) {
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ Processing...</span>';
    
    try {
        const { upscaleImage } = await import('./api.js');
        const data = await upscaleImage(path);
        if (data && data.url) {
            appendMessage('ai', data.url, true);
            state.messages.push({ role: 'assistant', content: `Image upscaled: ${data.url}` });
            await saveHistory(state.messages);
        } else {
            throw new Error(data?.error || 'Upscale failed');
        }
    } catch (err) {
        appendMessage('ai', 'Upscale error: ' + err.message, false, true);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
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
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;

    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not prepare image for analysis.');

    // Flatten onto white so transparent PNG/WebP inputs become a stable JPEG.
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    const convertedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
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
        message.attachment.dataUrl = await fileToDataUrl(file);
    }

    return message;
}

function serializeMessagesForApi(messages) {
    return messages.map(({ role, content }) => ({ role, content }));
}

function getDefaultAttachmentPrompt(file) {
    if (!file) return '';
    return file.type.startsWith('image/')
        ? 'Please analyze this attached image.'
        : `Please analyze the attached file: ${file.name}`;
}
