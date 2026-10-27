import { state, DOM } from './state.js';

const MAX_IMAGES = 3;
const MAX_DIM = 768;

export async function fileToDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

export async function fileToText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

export async function loadImageElement(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Unsupported image format.'));
        img.src = src;
    });
}

export async function normalizeImageForModel(file) {
    const sourceDataUrl = typeof file === 'string' ? file : await fileToDataUrl(file);
    const img = await loadImageElement(sourceDataUrl);

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

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(img, 0, 0, width, height);

    return {
        dataUrl: canvas.toDataURL('image/jpeg', 0.85),
        mimeType: 'image/jpeg'
    };
}

export async function ensureJpegDataUrl(dataUrl) {
    if (!dataUrl) return dataUrl;
    try {
        const normalized = await normalizeImageForModel(dataUrl);
        return normalized.dataUrl;
    } catch (e) {
        return dataUrl;
    }
}

export function addFiles(newFiles) {
    if (!newFiles || newFiles.length === 0) return;
    const fileList = Array.from(newFiles);
    const nonImages = fileList.filter(f => !f.type || !f.type.startsWith('image/'));

    if (nonImages.length > 0) {
        // Non-image file takes single attachment slot
        state.attachedFiles = [nonImages[0]];
    } else {
        // Images: filter and append up to MAX_IMAGES
        const existingImages = (state.attachedFiles || []).filter(f => f.type && f.type.startsWith('image/'));
        const combined = [...existingImages, ...fileList.filter(f => f.type && f.type.startsWith('image/'))];
        state.attachedFiles = combined.slice(0, MAX_IMAGES);
    }
    renderAttachmentPreview();
}

export function removeAttachment(index) {
    if (!state.attachedFiles) return;
    state.attachedFiles.splice(index, 1);
    if (state.attachedFiles.length === 0 && DOM.chatAttachment) {
        DOM.chatAttachment.value = '';
    }
    renderAttachmentPreview();
}

export function clearAttachments() {
    state.attachedFiles = [];
    if (DOM.chatAttachment) DOM.chatAttachment.value = '';
    if (DOM.attachmentPreview) {
        DOM.attachmentPreview.classList.add('attachment-preview-hidden');
        DOM.attachmentPreview.innerHTML = '';
    }
}

export function renderAttachmentPreview() {
    if (!DOM.attachmentPreview) return;
    const files = state.attachedFiles || [];

    if (files.length === 0) {
        DOM.attachmentPreview.classList.add('attachment-preview-hidden');
        DOM.attachmentPreview.innerHTML = '';
        return;
    }

    DOM.attachmentPreview.innerHTML = '';
    DOM.attachmentPreview.classList.remove('attachment-preview-hidden');

    files.forEach((file, idx) => {
        if (file.type && file.type.startsWith('image/')) {
            const container = document.createElement('div');
            container.className = 'preview-item';
            container.style.position = 'relative';
            container.style.display = 'inline-flex';
            container.style.alignItems = 'center';

            const img = document.createElement('img');
            const reader = new FileReader();
            reader.onload = (e) => { img.src = e.target.result; };
            reader.readAsDataURL(file);
            container.appendChild(img);

            const removeBtn = document.createElement('span');
            removeBtn.innerHTML = '×';
            removeBtn.className = 'remove-preview-btn';
            removeBtn.style.cursor = 'pointer';
            removeBtn.style.marginLeft = '4px';
            removeBtn.style.fontWeight = 'bold';
            removeBtn.onclick = (e) => {
                e.stopPropagation();
                removeAttachment(idx);
            };
            container.appendChild(removeBtn);
            DOM.attachmentPreview.appendChild(container);
        } else {
            const chip = document.createElement('div');
            chip.className = 'file-chip';
            chip.innerHTML = `<span>📄 ${file.name}</span>`;

            const removeBtn = document.createElement('span');
            removeBtn.innerHTML = '×';
            removeBtn.className = 'remove';
            removeBtn.style.cursor = 'pointer';
            removeBtn.style.marginLeft = '6px';
            removeBtn.onclick = (e) => {
                e.stopPropagation();
                removeAttachment(idx);
            };
            chip.appendChild(removeBtn);
            DOM.attachmentPreview.appendChild(chip);
        }
    });

    if (files.length > 1) {
        const clearAll = document.createElement('span');
        clearAll.textContent = 'Clear all';
        clearAll.style.cursor = 'pointer';
        clearAll.style.fontSize = '0.75rem';
        clearAll.style.opacity = '0.7';
        clearAll.style.marginLeft = '8px';
        clearAll.onclick = clearAttachments;
        DOM.attachmentPreview.appendChild(clearAll);
    }
}

export function handleFileChange(e) {
    if (!e.target.files || e.target.files.length === 0) return;
    addFiles(e.target.files);
}

export function initClipboardPasteHandler() {
    const handlePaste = (e) => {
        const clipboardData = e.clipboardData || window.clipboardData;
        if (!clipboardData || !clipboardData.items) return;

        const imageFiles = [];
        for (const item of clipboardData.items) {
            if (item.kind === 'file' && item.type.startsWith('image/')) {
                const f = item.getAsFile();
                if (f) imageFiles.push(f);
            }
        }

        if (imageFiles.length > 0) {
            e.preventDefault();
            addFiles(imageFiles);
        }
    };

    if (DOM.userInput) {
        DOM.userInput.addEventListener('paste', handlePaste);
    }
    window.addEventListener('paste', (e) => {
        if (e.target === DOM.userInput) return;
        const clipboardData = e.clipboardData;
        if (!clipboardData || !clipboardData.items) return;
        for (const item of clipboardData.items) {
            if (item.kind === 'file' && item.type.startsWith('image/')) {
                handlePaste(e);
                break;
            }
        }
    });
}

export async function buildAttachmentsPayload(files) {
    if (!files || files.length === 0) return null;
    const payload = [];
    for (const file of files) {
        if (file.type && file.type.startsWith('image/')) {
            const normalized = await normalizeImageForModel(file);
            payload.push({
                type: 'image',
                data: normalized.dataUrl.split(',')[1],
                mimeType: normalized.mimeType
            });
        } else {
            payload.push({
                type: 'file',
                name: file.name,
                content: await fileToText(file)
            });
        }
    }
    return payload;
}

export async function buildUserMessage(text, files) {
    const message = { role: 'user', content: text };
    if (!files || files.length === 0) return message;

    const attachments = [];
    for (const file of files) {
        const isImg = file.type && file.type.startsWith('image/');
        const att = {
            name: file.name || 'Image',
            type: file.type || 'application/octet-stream',
            kind: isImg ? 'image' : 'file'
        };
        if (isImg) {
            const normalized = await normalizeImageForModel(file);
            att.dataUrl = normalized.dataUrl;
            att.type = normalized.mimeType;
        }
        attachments.push(att);
    }

    message.attachments = attachments;
    message.attachment = attachments[0];
    return message;
}

export function getDefaultAttachmentPrompt(files) {
    if (!files || files.length === 0) return '';
    const imgCount = files.filter(f => f.type && f.type.startsWith('image/')).length;
    if (imgCount > 1) {
        return `Please analyze these ${imgCount} attached images.`;
    }
    if (imgCount === 1) {
        return 'Please analyze this attached image.';
    }
    return `Please analyze the attached file: ${files[0].name}`;
}
