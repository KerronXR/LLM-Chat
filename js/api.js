/**
 * Veloxify Local AI - API Logic
 */
import { state, DOM } from './state.js';

export async function fetchWithAbort(url, options = {}) {
    state.abortController = new AbortController();
    const { signal } = state.abortController;
    
    try {
        const response = await fetch(url, { ...options, signal });
        if (response.status === 401 && !url.includes('/login')) {
            window.location.href = '/login.html';
            return null;
        }
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Fetch aborted');
            return null;
        }
        throw error;
    }
}

export async function getHistory() {
    try {
        const res = await fetch('/api/history');
        if (res.status === 401) { window.location.href = '/login.html'; return []; }
        return await res.json();
    } catch (err) {
        console.error('Failed to get history:', err);
        return [];
    }
}

export async function saveHistory(messages) {
    try {
        await fetch('/api/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(messages)
        });
    } catch (err) {
        console.error('Failed to save history:', err);
    }
}

export async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login.html';
}

export async function savePersona(content) {
    try {
        const response = await fetch('/save_persona', {
            method: 'POST',
            body: content
        });
        if (response.status === 401) { window.location.href = '/login.html'; return false; }
        return response.ok;
    } catch (err) {
        console.error('Failed to save persona:', err);
        return false;
    }
}

export async function generateImage(prompt, options = {}) {
    // Generate image request for batch generation (streaming)
    const response = await fetch('/generate_image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            prompt,
            width: options.width || 512,
            height: options.height || 512,
            batch_size: options.batch_size || 1,
            init_image: options.init_image || null
        }),
        signal: state.abortController?.signal,
        keepalive: true
    });
    
    if (response.status === 401) { 
        window.location.href = '/login.html'; 
        return null; 
    }
    
    // We MUST return the raw response object so that calling code can
    // use response.body.getReader() for streaming.
    return response;
}

export async function upscaleImage(imagePath) {
    try {
        const response = await fetch('/api/upscale', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: imagePath })
        });
        
        if (response.status === 401) { window.location.href = '/login.html'; return null; }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await response.json();
        } else {
            const text = await response.text();
            console.error('Non-JSON response from server during upscale:', text);
            throw new Error(`Server returned non-JSON response (${response.status}): ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
        }
    } catch (err) {
        console.error('Upscale failed:', err);
        return { error: err.message };
    }
}
