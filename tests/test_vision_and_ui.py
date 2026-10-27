"""
Tests for:
1. Gemma vision projector reactivation in core.py.
2. model_supports_vision correctly identifying vision-capable models.
3. index.html default model selection is Gemma.
4. js/main.js toggles attach button visibility.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core

GEMMA_ID = "gemma-4-e4b-it:latest"
LLAMA_ID = "llama-3.2-3b-instruct-uncensored:latest"
PROJECTOR_FILE = "mmproj-google_gemma-4-E4B-it-f16.gguf"


def test_gemma_projector_mapped_in_core():
    """Verify Gemma Official is mapped to restored vision projector."""
    assert GEMMA_ID in core.VISION_PROJECTOR_MAPPING
    assert core.VISION_PROJECTOR_MAPPING[GEMMA_ID] == PROJECTOR_FILE


def test_model_supports_vision_gemma():
    """Verify model_supports_vision returns True for Gemma, False for Llama."""
    assert core.model_supports_vision(GEMMA_ID) is True
    assert core.model_supports_vision(LLAMA_ID) is False


def test_model_supports_vision_qwen_vl(monkeypatch):
    """Verify model_supports_vision returns True for Qwen2.5-VL when projector exists."""
    assert "qwen2.5-vl-7b-instruct:latest" in core.VISION_PROJECTOR_MAPPING
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    assert core.model_supports_vision("qwen2.5-vl-7b-instruct:latest") is True


def test_index_html_default_selected_is_gemma():
    """Verify index.html selects Gemma by default."""
    html_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    expected_selected = f'value="{GEMMA_ID}" selected'
    assert expected_selected in html, f"index.html must mark {GEMMA_ID} as selected"


def test_main_js_controls_attach_btn_display():
    """Verify main.js hides attach button for models without vision."""
    js_path = os.path.join(PROJECT_ROOT, "js", "main.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "attachBtn.style.display" in js


def test_gemma_chat_template_adaptation():
    """Verify Gemma chat template supports image and image_url types."""
    handler = core.GemmaVisionChatHandler(
        clip_model_path=os.path.join(core.MODELS_DIR, PROJECTOR_FILE),
        chat_template="{% elif item['type'] == 'image' %}{{- '<|image|>' -}}{% endif %}"
    )
    fmt = handler.handler.CHAT_FORMAT
    assert "item['type'] in ('image', 'image_url')" in fmt
    assert "item['image']" in fmt
    assert "image_url" in fmt


def test_normalize_incoming_attachments_mime_and_data_url():
    """Verify normalize_incoming_attachments accepts kind=image and MIME types."""
    import run_ui
    data = {
        "attachments": [
            {"name": "test.jpg", "type": "image/jpeg", "kind": "image", "dataUrl": "data:image/jpeg;base64,abc"},
            {"name": "notes.txt", "type": "file", "content": "hello"}
        ]
    }
    normalized = run_ui.normalize_incoming_attachments(data)
    assert len(normalized) == 2
    assert normalized[0]["kind"] == "image"
    assert normalized[0]["dataUrl"] == "data:image/jpeg;base64,abc"


