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
    state.webSearchMode = mode;
    if (!DOM.webSearchBtn) return;
    DOM.webSearchBtn.classList.remove('web-search-auto', 'web-search-on', 'web-search-off');
    DOM.webSearchBtn.classList.add(`web-search-${mode}`);
    if (DOM.webSearchBadge) {
        DOM.webSearchBadge.textContent = mode.toUpperCase();
    }
    const titles = {
        auto: 'Web Search: Auto (Auto-searches temporal/news queries)',
        on: 'Web Search: ON (Always search web)',
        off: 'Web Search: OFF (Never search web)'
    };
    DOM.webSearchBtn.title = titles[mode] || 'Web Search';
}

export function renderSourcesBadge(aiMsgDiv, sources) {
    if (!sources || !sources.length) return;
    let container = aiMsgDiv.querySelector('.search-sources-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'search-sources-container';
        const title = document.createElement('div');
        title.className = 'search-sources-title';
        title.innerHTML = '<span>🌐 Sources:</span>';
        container.appendChild(title);
        const list = document.createElement('div');
        list.className = 'search-sources-list';
        container.appendChild(list);
        aiMsgDiv.appendChild(container);
    }
    const list = container.querySelector('.search-sources-list');
    list.innerHTML = '';
    sources.forEach((s, idx) => {
        const a = document.createElement('a');
        a.className = 'search-source-chip';
        a.href = s.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.title = s.title;
        let label = s.title.length > 25 ? s.title.substring(0, 25) + '...' : s.title;
        a.textContent = `[${idx + 1}] ${label}`;
        list.appendChild(a);
    });
}
