"""
Tests for Markdown & Table rendering in UI:
1. Heading rendering (## Heading -> <h2>)
2. Bold and inline code formatting
3. Unordered and ordered lists
4. Markdown tables -> <table><tr><th><td>
5. Horizontal rules (---)
6. Fenced code blocks (```)
7. Streaming partial markdown safety
"""
import os
import subprocess
import json
import pytest

from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKDOWN_JS_PATH = os.path.join(PROJECT_ROOT, "js", "markdown.js")


def eval_markdown(md_text):
    """Evaluate renderMarkdown(md_text) using Node.js."""
    file_uri = Path(MARKDOWN_JS_PATH).as_uri()
    script = f"""
    import {{ renderMarkdown }} from '{file_uri}';
    const input = {json.dumps(md_text)};
    console.log(renderMarkdown(input));
    """
    res = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
    return res.stdout.strip()


def test_markdown_file_exists():
    assert os.path.exists(MARKDOWN_JS_PATH), "js/markdown.js must exist"


def test_markdown_headings():
    output = eval_markdown("## 🛡️ 3. Data Encryption (The Underlying Lock)")
    assert "<h2>🛡️ 3. Data Encryption (The Underlying Lock)</h2>" in output


def test_markdown_formatting():
    output = eval_markdown("**File-Level Encryption:** `unique key`")
    assert "<strong>File-Level Encryption:</strong>" in output
    assert "<code>unique key</code>" in output


def test_markdown_lists():
    md = """* Item 1\n* Item 2"""
    output = eval_markdown(md)
    assert "<ul>" in output
    assert "<li>Item 1</li>" in output
    assert "<li>Item 2</li>" in output
    assert "</ul>" in output


def test_markdown_dividers():
    output = eval_markdown("Before\n---\nAfter")
    assert "<hr" in output


def test_markdown_tables():
    md = """| Lock Feature | What it Prevents | Where it Lives |
| :--- | :--- | :--- |
| **Activation Lock** | Theft | Apple Servers |
| **Secure Enclave** | Biometric breach | Hardware Chip |"""
    output = eval_markdown(md)
    assert "<table" in output
    assert "<th>Lock Feature</th>" in output
    assert "<th>What it Prevents</th>" in output
    assert "<td><strong>Activation Lock</strong></td>" in output
    assert "<td>Theft</td>" in output
    assert "<td>Apple Servers</td>" in output
    assert "</table>" in output


def test_markdown_code_blocks():
    md = "```python\nprint('hello')\n```"
    output = eval_markdown(md)
    assert "<pre><code" in output
    assert "print('hello')" in output


def test_markdown_user_exact_example():
    user_example = """## 🛡️ 3. Data Encryption (The Underlying Lock)

This is the fundamental security layer that makes the hardware locks effective.

**How it works:**

* **File-Level Encryption:** Nearly all data on modern Apple devices is encrypted by default.
* **The Key Chain:** Protected by Secure Enclave.

---

## ⚙️ Summary Table

| Lock Feature | What it Prevents | Where it Lives | How it Works |
| :--- | :--- | :--- | :--- |
| **Activation Lock** | Unauthorized use after theft/loss. | iCloud/Apple Servers | Requires the original Apple ID to bypass setup. |
| **Secure Enclave** | Unauthorized access to biometric data/keys. | Dedicated Hardware Chip | Isolates cryptographic operations from the main OS. |
| **Data Encryption** | Reading data if the device is physically stolen. | Hardware | Encryption key locked. |"""
    html = eval_markdown(user_example)
    assert "<h2>🛡️ 3. Data Encryption (The Underlying Lock)</h2>" in html
    assert "<strong>How it works:</strong>" in html
    assert "<ul>" in html
    assert "<li><strong>File-Level Encryption:</strong>" in html
    assert "<hr class=\"markdown-divider\">" in html
    assert "<h2>⚙️ Summary Table</h2>" in html
    assert "<table class=\"markdown-table\">" in html
    assert "<th>Lock Feature</th>" in html
    assert "<th>What it Prevents</th>" in html
    assert "<td><strong>Activation Lock</strong></td>" in html
    assert "<td>iCloud/Apple Servers</td>" in html
    assert "</table>" in html

