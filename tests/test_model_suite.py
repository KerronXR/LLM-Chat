"""
Tests for model configuration updates:
- Llama 3.2 3B Uncensored registered
- DeepSeek 1.5B removed from active models
- Chat format for Llama-3 returns 'llama-3'
- UI dropdown options update
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core
import setup_local_llm

LLAMA_3B = "llama-3.2-3b-instruct-uncensored:latest"
LLAMA_3B_FILE = "Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf"
LLAMA_3B_REPO = "bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF"

DEEPSEEK_7B = "deepseek-r1-distill-qwen-7b-uncensored:latest"
OFFICIAL_GEMMA = "gemma-4-e4b-it:latest"
DEEPSEEK_1_5B = "deepseek-r1-distill-qwen-1.5b-uncensored:latest"


def test_llama_3b_in_models_mapping():
    assert LLAMA_3B in core.MODELS_MAPPING
    assert core.MODELS_MAPPING[LLAMA_3B] == LLAMA_3B_FILE


def test_1_5b_removed_from_models_mapping():
    assert DEEPSEEK_1_5B not in core.MODELS_MAPPING


def test_llama_3b_chat_format():
    fmt = core.get_chat_format(LLAMA_3B)
    assert fmt == "llama-3"


def test_setup_downloads_has_llama_3b():
    assert LLAMA_3B in setup_local_llm.MODELS_TO_DOWNLOAD
    info = setup_local_llm.MODELS_TO_DOWNLOAD[LLAMA_3B]
    assert info["filename"] == LLAMA_3B_FILE
    assert info["repo"] == LLAMA_3B_REPO


def test_index_html_options():
    html_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert f'value="{LLAMA_3B}"' in html
    assert f'value="{DEEPSEEK_7B}"' in html
    assert f'value="{OFFICIAL_GEMMA}"' in html
    assert f'value="{DEEPSEEK_1_5B}"' not in html
