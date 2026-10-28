/**
 * Web Search UI Controller: Mode toggling, state badge sync, and source chip rendering
 */
import { state, DOM } from './state.js';

export function handleToggleWebSearch() {
    const modes = ['auto', 'on', 'off'];
    const currentIdx = modes.indexOf(state.webSearchMode);
    const nextMode = modes[(currentIdx + 1) % modes.length];
    setWebSearchMode(nextMode);
}

export function setWebSearchMode(mode) {
    const validMode = ['auto', 'on', 'off'].includes(mode) ? mode : 'auto';
    state.webSearchMode = validMode;
    try {
        localStorage.setItem('webSearchMode', validMode);
    } catch (e) {}
    if (!DOM.webSearchBtn) return;
    DOM.webSearchBtn.classList.remove('web-search-auto', 'web-search-on', 'web-search-off');
    DOM.webSearchBtn.classList.add(`web-search-${validMode}`);
    if (DOM.webSearchBadge) {
        DOM.webSearchBadge.textContent = validMode.toUpperCase();
    }
    const titles = {
        auto: 'Web Search: Auto (Auto-searches temporal/news queries)',
        on: 'Web Search: ON (Always search web)',
        off: 'Web Search: OFF (Never search web)'
    };
    DOM.webSearchBtn.title = titles[validMode] || 'Web Search';
}

export function initWebSearchMode() {
    let saved = 'auto';
    try {
        saved = localStorage.getItem('webSearchMode') || 'auto';
    } catch (e) {}
    setWebSearchMode(saved);
}

export function renderSourcesBadge(aiMsgDiv, sources, count) {
    const total = count || (sources ? sources.length : 0);
    if (!total) return;
    let container = aiMsgDiv.querySelector('.search-sources-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'search-sources-container';
        aiMsgDiv.appendChild(container);
    }
    container.innerHTML = `<span class="search-sources-summary">🌐 ${total} search results</span>`;
}
