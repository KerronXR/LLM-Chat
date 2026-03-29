import { state, DOM } from './state.js';
import { fetchWithAbort, generateImage } from './api.js';
import { setGenerating, appendMessage, showProgress } from './ui.js';

export async function handleSend() {
    const text = DOM.userInput.value.trim();
    if (!text || state.isGenerating) return;
    
    // Clear input
    DOM.userInput.value = '';
    
    // Add user message
    appendMessage('user', text);
    state.messages.push({ role: 'user', content: text });
    import('./api.js').then(m => m.saveHistory(state.messages));
    
    setGenerating(true);
    
    if (DOM.autoImageCheckbox.checked) {
        await handleImageGeneration(text);
    } else {
        await handleLlmGeneration(text);
    }
}

async function handleLlmGeneration() {
    state.abortController = new AbortController();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: DOM.modelSelect.value,
                messages: state.messages,
                stream: true
            }),
            signal: state.abortController.signal
        });
        
        if (response.status === 401) { window.location.href = '/login.html'; return; }
        if (!response.ok) throw new Error('Ollama connection failed');
        
        const aiMsgDiv = appendMessage('ai', '...');
        let aiContent = '';
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const json = JSON.parse(line);
                    if (json.message) {
                        aiContent += json.message.content;
                        aiMsgDiv.innerHTML = aiContent.replace(/\n/g, '<br>');
                    }
                if (json.done) {
                    state.messages.push({ role: 'assistant', content: aiContent });
                    state.contextSize = json.prompt_eval_count + json.eval_count;
                    state.maxContext = json.context_length || 8192;
                    document.getElementById('current-context').textContent = state.contextSize;
                    document.getElementById('max-context').textContent = state.maxContext;
                    
                    // Save history after AI response
                    import('./api.js').then(m => m.saveHistory(state.messages));
                }
                } catch (e) { console.error('Parse error:', e); }
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
    try {
        const resolution = DOM.imageSizeSelect.value.split('x');
        const width = parseInt(resolution[0]);
        const height = parseInt(resolution[1]);
        const batch_size = parseInt(DOM.batchSizeSlider.value);
        const init_image = DOM.imagePreview.src.startsWith('data:') ? DOM.imagePreview.src : null;
        
        const data = await generateImage(prompt, { width, height, batch_size, init_image });
        
        if (data && data.url) {
            appendMessage('ai', data.url, true);
            state.messages.push({ role: 'assistant', content: `Image generated: ${data.url}` });
            import('./api.js').then(m => m.saveHistory(state.messages));
        } else if (data && data.error) {
            appendMessage('ai', data.error, false, true);
        }
    } catch (err) {
        appendMessage('ai', 'Image generation error: ' + err.message, false, true);
    } finally {
        setGenerating(false);
    }
}
