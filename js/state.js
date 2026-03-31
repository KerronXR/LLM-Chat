/**
 * Veloxify Local AI - State Management
 */

export const state = {
    messages: [],
    isGenerating: false,
    abortController: null,
    contextSize: 0,
    maxContext: 8192,
    activeModel: "gemma-3-12b-it:latest"
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
    imageUpload: document.getElementById('image-upload'),
    uploadBtn: document.getElementById('upload-btn'),
    imagePreview: document.getElementById('image-preview'),
    imagePreviewContainer: document.getElementById('image-preview-container'),
    removeImageBtn: document.getElementById('remove-image-btn'),
    autoImageCheckbox: document.getElementById('auto-image-checkbox'),
    imageSizeSelect: document.getElementById('image-size-select'),
    batchSizeSlider: document.getElementById('batch-size-slider'),
    batchSizeValue: document.getElementById('batch-size-value'),
    mobileToggle: null, // Initialized in main
    sidebarBackdrop: null,
    sidebar: document.querySelector('.sidebar')
};

export function updateContextUI() {
    DOM.currentContext.textContent = state.contextSize;
    DOM.maxContext.textContent = state.maxContext;
}
