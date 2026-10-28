"""
Tests for DeepSeek-R1-Distill-Qwen-7B-Uncensored integration.
TDD verification for model registration, chat format, and UI options.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core
import setup_local_llm

MODEL_ID = "deepseek-r1-distill-qwen-7b-uncensored:latest"
MODEL_FILENAME = "DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf"
REPO_ID = "mradermacher/DeepSeek-R1-Distill-Qwen-7B-Uncensored-GGUF"


def test_deepseek_registered_in_core_models_mapping():
    """Verify model ID is in core.MODELS_MAPPING."""
    assert MODEL_ID in core.MODELS_MAPPING, f"{MODEL_ID} missing from core.MODELS_MAPPING"
    assert core.MODELS_MAPPING[MODEL_ID] == MODEL_FILENAME


def test_deepseek_registered_in_setup_downloads():
    """Verify setup_local_llm has repo and filename for downloading."""
    assert MODEL_ID in setup_local_llm.MODELS_TO_DOWNLOAD, f"{MODEL_ID} missing from setup_local_llm"
    info = setup_local_llm.MODELS_TO_DOWNLOAD[MODEL_ID]
    assert info["repo"] == REPO_ID
    assert info["filename"] == MODEL_FILENAME


def test_deepseek_chat_format_determination():
    """Verify chat_format helper returns chatml for deepseek / qwen."""
    format_r1 = core.get_chat_format(MODEL_ID)
    assert format_r1 == "chatml", f"Expected 'chatml' for DeepSeek-R1, got '{format_r1}'"

    format_qwen = core.get_chat_format("qwen2.5-vl-7b-instruct:latest")
    assert format_qwen == "chatml", f"Expected 'chatml' for Qwen2.5-VL, got '{format_qwen}'"


def test_index_html_has_deepseek_option():
    """Verify index.html model selector contains deepseek option."""
    html_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    expected_snippet = f'value="{MODEL_ID}"'
    assert expected_snippet in html, f"index.html missing option with {expected_snippet}"
