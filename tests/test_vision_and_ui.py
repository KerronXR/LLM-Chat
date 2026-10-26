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
    """Verify Gemma chat template replaces {{- '<|image|>' -}} with item image."""
    handler = core.GemmaVisionChatHandler(
        clip_model_path=os.path.join(core.MODELS_DIR, PROJECTOR_FILE),
        chat_template="{{- '<|image|>' -}}Hello"
    )
    assert "item['image']" in handler.handler.CHAT_FORMAT

