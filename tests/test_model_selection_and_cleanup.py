"""
Tests verifying Gemma and Llama removal, Qwen2.5-VL and DeepSeek-R1 exclusivity,
and Qwen2.5-VL as default UI choice.
"""
import os
import sys
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core
import run_ui


def test_models_mapping_only_has_qwen_and_deepseek():
    """Verify MODELS_MAPPING in core.py contains only Qwen and DeepSeek."""
    expected = {
        "qwen2.5-vl-7b-instruct:latest",
        "deepseek-r1-distill-qwen-7b-uncensored:latest",
    }
    assert set(core.MODELS_MAPPING.keys()) == expected
    assert "gemma-4-e4b-it:latest" not in core.MODELS_MAPPING
    assert "llama-3.2-3b-instruct-uncensored:latest" not in core.MODELS_MAPPING


def test_vision_projector_mapping_only_has_qwen():
    """Verify VISION_PROJECTOR_MAPPING in core.py contains only Qwen2.5-VL."""
    assert list(core.VISION_PROJECTOR_MAPPING.keys()) == ["qwen2.5-vl-7b-instruct:latest"]
    assert "gemma-4-e4b-it:latest" not in core.VISION_PROJECTOR_MAPPING


def test_index_html_dropdown_default_is_qwen():
    """Verify index.html has only Qwen and DeepSeek, with Qwen selected by default."""
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Must select Qwen by default
    assert 'value="qwen2.5-vl-7b-instruct:latest" selected' in html
    # Must NOT have Gemma or Llama options
    assert 'value="gemma-4-e4b-it:latest"' not in html
    assert 'value="llama-3.2-3b-instruct-uncensored:latest"' not in html
    # Must contain DeepSeek
    assert 'value="deepseek-r1-distill-qwen-7b-uncensored:latest"' in html
    # Greeting in chat window introduces Qwen
    assert "Qwen2.5-VL" in html


def test_state_js_defaults_to_qwen():
    """Verify activeModel in js/state.js defaults to Qwen2.5-VL."""
    state_path = os.path.join(PROJECT_ROOT, "js", "state.js")
    with open(state_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "activeModel: 'qwen2.5-vl-7b-instruct:latest'" in js or 'activeModel: "qwen2.5-vl-7b-instruct:latest"' in js


def test_run_ui_defaults_to_qwen():
    """Verify run_ui.py defaults fallback model to Qwen2.5-VL."""
    import inspect
    src = inspect.getsource(run_ui.Handler.handle_chat)
    assert "'model', 'qwen2.5-vl-7b-instruct:latest'" in src
