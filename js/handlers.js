import { state, DOM } from './state.js';
import { fetchWithAbort } from './api.js';
import { setGenerating, appendMessage, showProgress, updateImageMessage, scrollToBottom } from './ui.js';
import { updateContextUI } from './state.js';
import { saveHistory } from './api.js';
import { renderMarkdown } from './markdown.js';
import { renderSourcesBadge } from './search.js';
import {
    clearAttachments,
    handleFileChange as handleAttachmentFileChange,
    buildAttachmentsPayload,
    buildUserMessage,
    getDefaultAttachmentPrompt,
    ensureJpegDataUrl
} from './attachments.js';

let activeGenerationId = 0;

export async function handleSend() {
    // Interrupt existing generation if currently thinking
    if (state.isGenerating && state.abortController) {
        state.abortController.abort();
    }

    const text = DOM.userInput.value.trim();
    const attachedFiles = state.attachedFiles ? [...state.attachedFiles] : [];
    if (!text && attachedFiles.length === 0) return;

    // Immediately clear input and UI attachments ("clipboard")
    DOM.userInput.value = '';
    clearAttachments();

    const generationId = ++activeGenerationId;
    setGenerating(true);
    state.abortController = new AbortController();
    const hasImages = attachedFiles.some(f => f.type && f.type.startsWith('image/'));
    const messageText = text || getDefaultAttachmentPrompt(attachedFiles);
    const userMessage = await buildUserMessage(messageText, attachedFiles);

    appendMessage('user', userMessage);
    state.messages.push(userMessage);
    await saveHistory(state.messages);

    // Create AI bubble immediately so user sees bubble and status before network/vision delay
    const aiMsgDiv = appendMessage('ai', '...');
    const tpsLive = document.createElement('div');
    tpsLive.className = 'tps-live';
    tpsLive.textContent = hasImages ? '⏳ preparing vision...' : '⏳ thinking...';
    aiMsgDiv.appendChild(tpsLive);

    await handleLlmGeneration(attachedFiles, aiMsgDiv, tpsLive, generationId);
}

export function handleAttachmentSelect() {
    DOM.chatAttachment.click();
}

export function handleFileChange(e) {
    handleAttachmentFileChange(e);
}

export function clearAttachment() {
    clearAttachments();
}

export { ensureJpegDataUrl };

async function handleLlmGeneration(files = [], aiMsgDiv = null, tpsLive = null, generationId = null) {
    if (!generationId) generationId = ++activeGenerationId;
    if (generationId !== activeGenerationId) return;
    if (!state.abortController) {
        state.abortController = new AbortController();
    }

    if (!aiMsgDiv) {
        aiMsgDiv = appendMessage('ai', '...');
        tpsLive = document.createElement('div');
        tpsLive.className = 'tps-live';
        tpsLive.textContent = '⏳ generating...';
        aiMsgDiv.appendChild(tpsLive);
    }

    try {
        const attachmentsPayload = await buildAttachmentsPayload(files);
        // Backwards compatibility: single attachment object + attachments array
        const primaryAttachment = attachmentsPayload && attachmentsPayload.length > 0 ? attachmentsPayload[0] : null;

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: DOM.modelSelect.value,
                messages: serializeMessagesForApi(state.messages),
                stream: true,
                attachment: primaryAttachment,
                attachments: attachmentsPayload,
                web_search: state.webSearchMode
            }),
            signal: state.abortController.signal
        });

        if (response.status === 401) { window.location.href = '/login.html'; return; }
        if (!response.ok) throw new Error('Generation failed');

        let aiContent = '';
        let streamError = null;
        let liveTps = 0;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let lineBuf = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            lineBuf += decoder.decode(value, { stream: true });
            const parts = lineBuf.split('\n');
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
                if (json.status === 'searching' && tpsLive) {
                    tpsLive.textContent = `🔍 Searching web (${json.query})...`;
                }
                if (json.status === 'sources' && tpsLive) {
                    tpsLive.textContent = `🌐 ${json.count} search results`;
                    renderSourcesBadge(aiMsgDiv, json.sources, json.count);
                }
                if (json.message) {
                    aiContent += json.message.content;
                    let tb = aiMsgDiv.querySelector('.message-text');
                    if (!tb) {
                        tb = document.createElement('div');
                        tb.className = 'message-text';
                        aiMsgDiv.prepend(tb);
                    }
                    tb.innerHTML = formatAiContent(aiContent);
                    scrollToBottom();
                }
                if (typeof json.tps === 'number' && tpsLive) {
                    liveTps = json.tps;
                    tpsLive.textContent = `⚡ ${liveTps} tok/s`;
                }
                if (json.done) {
                    if (tpsLive) tpsLive.remove();

                    if (streamError) {
                        throw new Error(streamError);
                    }
                    state.messages.push({ role: 'assistant', content: aiContent });
                    state.contextSize = json.prompt_eval_count + json.eval_count;
                    state.maxContext = json.context_length || 8192;
                    if (DOM.currentContext) DOM.currentContext.textContent = state.contextSize;
                    if (DOM.maxContext) DOM.maxContext.textContent = state.maxContext;

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
            if (aiContent) {
                state.messages.push({ role: 'assistant', content: aiContent });
                await saveHistory(state.messages);
            }
            if (generationId === activeGenerationId) {
                appendMessage('ai', '[Generation Stopped]', false, true);
            }
        } else {
            appendMessage('ai', 'Error: ' + err.message, false, true);
        }
    } finally {
        if (generationId === activeGenerationId) {
            setGenerating(false);
        }
    }
}

function formatAiContent(content) {
    return renderMarkdown(content);
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
        if (!DOM.chatWindow.innerText.includes('[Generation Stopped]')) {
            appendMessage('ai', '[Generation Stopped]', false, true);
        }
    } else {
        handleClearChat();
    }
}

export function handleExport() {
    if (state.messages.length === 0) {
        appendMessage('ai', 'Chat is empty, nothing to export.', false, true);
        return;
    }

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

function serializeMessagesForApi(messages) {
    return messages.map((msg) => {
        if (Array.isArray(msg.content)) {
            return { role: msg.role, content: msg.content };
        }
        if (msg.role === 'user') {
            const attachments = msg.attachments || (msg.attachment ? [msg.attachment] : []);
            const imageAttachments = attachments.filter(a => a && a.kind === 'image' && a.dataUrl);
            if (imageAttachments.length > 0) {
                const content = imageAttachments.map(a => ({
                    type: 'image_url',
                    image_url: { url: a.dataUrl },
                    image: a.dataUrl
                }));
                content.push({ type: 'text', text: msg.content });
                return { role: msg.role, content };
            }
        }
        return { role: msg.role, content: msg.content };
    });
}
