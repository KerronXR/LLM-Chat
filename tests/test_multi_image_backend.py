import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import core


def test_core_get_image_urls_handles_multiple_images():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": "data:image/jpeg;base64,abc1"},
                {"type": "image", "image": "data:image/jpeg;base64,abc2"},
                {"type": "image", "image": "data:image/jpeg;base64,abc3"},
                {"type": "text", "text": "Compare these images."}
            ]
        }
    ]
    urls = core.GemmaVisionChatHandler.get_image_urls(messages)
    assert len(urls) == 3
    assert urls[0] == "data:image/jpeg;base64,abc1"
    assert urls[1] == "data:image/jpeg;base64,abc2"
    assert urls[2] == "data:image/jpeg;base64,abc3"


def test_core_get_image_urls_handles_instance_call():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": "data:image/jpeg;base64,abc1"}
            ]
        }
    ]
    # llama_cpp calls self.get_image_urls(messages) which passes self and messages
    urls = core.GemmaVisionChatHandler.get_image_urls(object(), messages)
    assert urls == ["data:image/jpeg;base64,abc1"]


def test_core_extract_attachments_helper():
    import run_ui
    data = {
        "messages": [{"role": "user", "content": "hello"}],
        "attachments": [
            {"type": "image", "data": "img1", "mimeType": "image/jpeg"},
            {"type": "image", "data": "img2", "mimeType": "image/jpeg"}
        ]
    }
    attachments = run_ui.normalize_incoming_attachments(data)
    assert len(attachments) == 2
    assert attachments[0]["data"] == "img1"
    assert attachments[1]["data"] == "img2"


def test_core_extract_attachments_caps_at_three():
    import run_ui
    data = {
        "messages": [{"role": "user", "content": "hello"}],
        "attachments": [
            {"type": "image", "data": f"img{i}", "mimeType": "image/jpeg"}
            for i in range(5)
        ]
    }
    attachments = run_ui.normalize_incoming_attachments(data)
    assert len(attachments) == 3


def test_core_extract_attachments_single_fallback():
    import run_ui
    data = {
        "messages": [{"role": "user", "content": "hello"}],
        "attachment": {"type": "image", "data": "img_single", "mimeType": "image/png"}
    }
    attachments = run_ui.normalize_incoming_attachments(data)
    assert len(attachments) == 1
    assert attachments[0]["data"] == "img_single"


def test_run_ui_handle_chat_no_unbound_attachment():
    import run_ui
    import inspect
    source = inspect.getsource(run_ui.Handler.handle_chat)
    # Ensure there is no raw 'attachment and' or 'not attachment' in handle_chat
    import re
    assert not re.search(r"\bnot\s+attachment\b", source), "Found unbound 'not attachment' in handle_chat"
    assert not re.search(r"\bif\s+attachment\b", source), "Found unbound 'if attachment' in handle_chat"


def test_run_ui_continuation_tokens_and_stop():
    import run_ui
    import inspect
    source = inspect.getsource(run_ui)
    # Must not contain bogus '<turn|>' or '<|turn>' tags
    assert "<turn|>" not in source
    assert "<|turn>" not in source
    # Must use ChatML tags for Qwen / DeepSeek
    assert "<|im_start|>" in source
    assert "<|im_end|>" in source


def test_run_ui_handles_connection_aborted():
    import run_ui
    import inspect
    source = inspect.getsource(run_ui.Handler.handle_chat)
    # Must catch ConnectionAbortedError specifically and reset session
    assert "ConnectionAbortedError" in source
    assert "reset_chat_session" in source


def test_core_qwen25_vl_mapping_and_handler():
    import core
    model_id = "qwen2.5-vl-7b-instruct:latest"
    assert model_id in core.MODELS_MAPPING
    assert "Qwen2.5-VL-7B-Instruct" in core.MODELS_MAPPING[model_id]
    assert model_id in core.VISION_PROJECTOR_MAPPING
    assert "mmproj-Qwen2.5-VL-7B-Instruct" in core.VISION_PROJECTOR_MAPPING[model_id]
    assert core.get_chat_format(model_id) == "chatml"


def test_continuation_tags_format_aware():
    import run_ui
    # Qwen2.5-VL / ChatML format
    qwen_prompt, qwen_stops = run_ui.build_continuation_turn("qwen2.5-vl-7b-instruct:latest", "what is this")
    assert "<|im_start|>user\nwhat is this<|im_end|>\n<|im_start|>assistant\n" == qwen_prompt
    assert "<|im_end|>" in qwen_stops


def test_vision_model_context_length():
    import core
    assert core.get_model_context_length("qwen2.5-vl-7b-instruct:latest") == 8192
    assert core.get_model_context_length("deepseek-r1-distill-qwen-7b-uncensored:latest") == 4096


def test_qwen25_vl_chat_handler_supports_both_image_formats():
    import core
    llm = core.load_local_model("qwen2.5-vl-7b-instruct:latest")

    # 1. Standard OpenAI image_url format
    msg_openai = [
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,1234"}},
            {"type": "text", "text": "test"}
        ]}
    ]
    assert llm.chat_handler.get_image_urls(msg_openai) == ["data:image/jpeg;base64,1234"]

    # 2. Legacy/custom image format
    msg_custom = [
        {"role": "user", "content": [
            {"type": "image", "image": "data:image/jpeg;base64,5678"},
            {"type": "text", "text": "test"}
        ]}
    ]
    assert llm.chat_handler.get_image_urls(msg_custom) == ["data:image/jpeg;base64,5678"]



