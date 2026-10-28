"""
Tests for multi-turn vision memory:
1. js/handlers.js serializeMessagesForApi preserves images in conversation history.
2. run_ui.py handles vision when image is in history without new attachment.
"""
import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def test_serialize_messages_preserves_images_in_handlers_js():
    """Verify serializeMessagesForApi in handlers.js formats image attachments into structured content."""
    handlers_path = os.path.join(PROJECT_ROOT, "js", "handlers.js")
    with open(handlers_path, "r", encoding="utf-8") as f:
        code = f.read()

    func_idx = code.find("function serializeMessagesForApi")
    assert func_idx != -1, "serializeMessagesForApi not found"

    func_block = code[func_idx:func_idx + 600]
    # Function must inspect msg.attachment and retain image in structured content
    assert "attachment" in func_block, "serializeMessagesForApi does not retain attachments in history"
    assert "image" in func_block, "serializeMessagesForApi does not format image in history"


def test_run_ui_detects_vision_in_history_without_new_attachment():
    """Verify run_ui detects vision when image is present in prior messages."""
    import run_ui
    # Check that has_history_images or similar multi-turn detection exists
    run_ui_path = os.path.join(PROJECT_ROOT, "run_ui.py")
    with open(run_ui_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert "has_history_images" in code, "run_ui.py does not check for images in multi-turn history"


def test_multiturn_vision_inference():
    """Verify Qwen handles multi-turn conversation where image was sent in turn 1."""
    import core
    import struct
    import zlib
    import base64

    def make_png(width=16, height=16, r=255, g=0, b=0):
        def chunk(tag, data):
            return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xffffffff)
        raw_data = b""
        for _ in range(height):
            raw_data += b"\x00" + bytes([r, g, b] * width)
        ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_data)) + chunk(b"IEND", b"")

    png_bytes = make_png(16, 16, 255, 0, 0)
    data_url = f"data:image/png;base64,{base64.b64encode(png_bytes).decode()}"
    llm = core.load_local_model("qwen2.5-vl-7b-instruct:latest")
    
    multiturn_messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": data_url},
                {"type": "text", "text": "What color is this? Answer in one word."}
            ]
        },
        {
            "role": "assistant",
            "content": "Red"
        },
        {
            "role": "user",
            "content": "Confirm the color again in one word."
        }
    ]
    
    res = llm.create_chat_completion(messages=multiturn_messages, max_tokens=10)
    text = res["choices"][0]["message"]["content"].lower()
    assert "red" in text, f"Expected 'red' in multi-turn reply, got: {text}"
