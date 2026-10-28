"""
Tests for model configuration updates:
- Qwen2.5-VL and DeepSeek-R1 registered
- Gemma and Llama removed from active models
- Chat format returns 'chatml'
- UI dropdown options update
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core
import setup_local_llm

QWEN_VL = "qwen2.5-vl-7b-instruct:latest"
DEEPSEEK_7B = "deepseek-r1-distill-qwen-7b-uncensored:latest"
LLAMA_3B = "llama-3.2-3b-instruct-uncensored:latest"
OFFICIAL_GEMMA = "gemma-4-e4b-it:latest"


def test_models_mapping_contents():
    assert QWEN_VL in core.MODELS_MAPPING
    assert DEEPSEEK_7B in core.MODELS_MAPPING
    assert LLAMA_3B not in core.MODELS_MAPPING
    assert OFFICIAL_GEMMA not in core.MODELS_MAPPING


def test_chat_format_returns_chatml():
    assert core.get_chat_format(QWEN_VL) == "chatml"
    assert core.get_chat_format(DEEPSEEK_7B) == "chatml"


def test_setup_downloads_has_active_models():
    assert QWEN_VL in setup_local_llm.MODELS_TO_DOWNLOAD
    assert DEEPSEEK_7B in setup_local_llm.MODELS_TO_DOWNLOAD
    assert LLAMA_3B not in setup_local_llm.MODELS_TO_DOWNLOAD
    assert OFFICIAL_GEMMA not in setup_local_llm.MODELS_TO_DOWNLOAD


def test_index_html_options():
    html_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert f'value="{QWEN_VL}"' in html
    assert f'value="{DEEPSEEK_7B}"' in html
    assert f'value="{LLAMA_3B}"' not in html
    assert f'value="{OFFICIAL_GEMMA}"' not in html
