/**
 * Lightweight, streaming-safe Markdown and Table parser.
 * Handles headings, tables, code blocks, lists, bold, italic, dividers.
 */

function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function formatInline(text) {
    if (!text) return '';
    return text
        // Inline code
        .replace(/`([^`]+)`/g, (_, code) => `<code>${escapeHtml(code)}</code>`)
        // Bold
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/__([^_]+)__/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>');
}

function isTableSeparator(line) {
    const trimmed = line.trim();
    if (!trimmed.includes('-')) return false;
    const parts = trimmed.split('|').map(s => s.trim()).filter(Boolean);
    return parts.length > 0 && parts.every(p => /^:?-+:?$/.test(p));
}

function parseTableRow(line) {
    const trimmed = line.trim();
    const clean = trimmed.replace(/^\|/, '').replace(/\|$/, '');
    return clean.split('|').map(c => c.trim());
}

export function renderMarkdown(md) {
    if (!md) return '';

    // 1. Extract and preserve code blocks
    const codeBlocks = [];
    const textWithoutCode = md.replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
        const idx = codeBlocks.length;
        const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : '';
        codeBlocks.push(`<pre><code${langClass}>${escapeHtml(code.trimEnd())}</code></pre>`);
        return `__CODE_BLOCK_${idx}__`;
    });

    const lines = textWithoutCode.split('\n');
    const output = [];

    let inList = null; // 'ul' or 'ol'
    let tableRows = [];

    function flushList() {
        if (inList) {
            output.push(`</${inList}>`);
            inList = null;
        }
    }

    function flushTable() {
        if (tableRows.length === 0) return;
        if (tableRows.length === 1 && !isTableSeparator(lines[0] || '')) {
            // Incomplete/single line table
            output.push(`<p>${formatInline(tableRows[0])}</p>`);
            tableRows = [];
            return;
        }

        let html = '<div class="table-container"><table class="markdown-table">';
        const headers = parseTableRow(tableRows[0]);
        html += '<thead><tr>';
        headers.forEach(h => {
            html += `<th>${formatInline(h)}</th>`;
        });
        html += '</tr></thead><tbody>';

        // Skip separator row at index 1 if present
        const startIdx = tableRows.length > 1 && isTableSeparator(tableRows[1]) ? 2 : 1;
        for (let r = startIdx; r < tableRows.length; r++) {
            const cells = parseTableRow(tableRows[r]);
            html += '<tr>';
            for (let c = 0; c < headers.length; c++) {
                const cellText = cells[c] !== undefined ? cells[c] : '';
                html += `<td>${formatInline(cellText)}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        output.push(html);
        tableRows = [];
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Check if table row
        if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 1) {
            flushList();
            tableRows.push(trimmed);
            continue;
        } else if (tableRows.length > 0) {
            flushTable();
        }

        // Code block placeholder
        if (trimmed.startsWith('__CODE_BLOCK_') && trimmed.endsWith('__')) {
            flushList();
            output.push(trimmed);
            continue;
        }

        // Horizontal dividers
        if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
            flushList();
            output.push('<hr class="markdown-divider">');
            continue;
        }

        // Headings
        const hMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
        if (hMatch) {
            flushList();
            const level = hMatch[1].length;
            const title = formatInline(hMatch[2]);
            output.push(`<h${level}>${title}</h${level}>`);
            continue;
        }

        // Unordered lists (* or -)
        const ulMatch = trimmed.match(/^[*+-]\s+(.*)$/);
        if (ulMatch) {
            if (inList !== 'ul') {
                flushList();
                output.push('<ul>');
                inList = 'ul';
            }
            output.push(`<li>${formatInline(ulMatch[1])}</li>`);
            continue;
        }

        // Ordered lists (1. )
        const olMatch = trimmed.match(/^\d+\.\s+(.*)$/);
        if (olMatch) {
            if (inList !== 'ol') {
                flushList();
                output.push('<ol>');
                inList = 'ol';
            }
            output.push(`<li>${formatInline(olMatch[1])}</li>`);
            continue;
        }

        // Regular line or empty
        flushList();
        if (trimmed === '') {
            output.push('');
        } else {
            output.push(formatInline(line));
        }
    }

    flushList();
    flushTable();

    // Reassemble with clean paragraph breaks
    let result = '';
    let inP = false;

    for (let j = 0; j < output.length; j++) {
        const item = output[j];
        if (!item) {
            if (inP) {
                result += '</p>';
                inP = false;
            }
            continue;
        }

        // Block elements don't wrap in <p>
        if (/^<(h[1-6]|ul|ol|div|table|pre|hr|li)/i.test(item) || item.startsWith('__CODE_BLOCK_')) {
            if (inP) {
                result += '</p>';
                inP = false;
            }
            result += item;
        } else {
            if (!inP) {
                result += '<p>' + item;
                inP = true;
            } else {
                result += '<br>' + item;
            }
        }
    }
    if (inP) result += '</p>';

    // Restore code blocks
    return result.replace(/__CODE_BLOCK_(\d+)__/g, (_, idx) => codeBlocks[Number(idx)] || '');
}
