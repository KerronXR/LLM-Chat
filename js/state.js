/**
 * Veloxify Local AI - State Management
 */

export const state = {
    messages: [],
    isGenerating: false,
    abortController: null,
    contextSize: 0,
    maxContext: 8192,
    activeModel: "gemma-4-e4b-it:latest",
    attachedFiles: [],
    get attachedFile() {
        return this.attachedFiles && this.attachedFiles.length > 0 ? this.attachedFiles[0] : null;
    },
    set attachedFile(file) {
        if (!file) this.attachedFiles = [];
        else this.attachedFiles = [file];
    },
    webSearchMode: "auto"
};

export const DOM = {
    chatWindow: document.getElementById('chat-window'),
    userInput: document.getElementById('user-input'),
    sendBtn: document.getElementById('send-btn'),
    stopBtn: document.getElementById('stop-btn'),
    modelSelect: document.getElementById('model-select'),
    clearBtn: document.getElementById('clear-btn'),
    exportBtn: document.getElementById('export-btn'),
    systemPrompt: document.getElementById('system-prompt'),
    savePersonaBtn: document.getElementById('save-persona-btn'),
    progressBar: document.getElementById('progress-container'),
    currentContext: document.getElementById('current-context'),
    maxContext: document.getElementById('max-context'),
    chatAttachment: document.getElementById('chat-attachment'),
    attachBtn: document.getElementById('attach-btn'),
    webSearchBtn: document.getElementById('web-search-btn'),
    webSearchBadge: document.getElementById('web-search-badge'),
    attachmentPreview: document.getElementById('attachment-preview'),
    mobileToggle: null, // Initialized in main
    sidebarBackdrop: null,
    sidebar: document.querySelector('.sidebar')
};

export function updateContextUI() {
    if (DOM.currentContext) DOM.currentContext.textContent = state.contextSize;
    if (DOM.maxContext) DOM.maxContext.textContent = state.maxContext;
}
