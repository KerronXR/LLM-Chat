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

export async function getPersona() {
    try {
        const res = await fetch('/persona.txt');
        if (res.status === 401) { window.location.href = '/login.html'; return ''; }
        if (!res.ok) return '';
        return await res.text();
    } catch (err) {
        console.error('Failed to get persona:', err);
        return '';
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


