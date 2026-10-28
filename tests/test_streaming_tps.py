"""
Backend tests for TPS (tokens-per-second) data in NDJSON / SSE stream.
Tests timing injection in handle_chat without loading actual LLM.
"""
import io
import json
import os
import sys
import tempfile
import shutil
import threading
import time
from unittest.mock import patch, MagicMock

import requests
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import run_ui


def _start_server(tmp, port):
    orig = run_ui.DIRECTORY
    run_ui.DIRECTORY = tmp
    run_ui.sessions.clear()
    server = run_ui.ThreadedHTTPServer(("127.0.0.1", port), run_ui.Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)
    return server, orig


def _stop_server(server, orig):
    server.shutdown()
    server.server_close()
    run_ui.DIRECTORY = orig


def _auth():
    token = "tps-test-token"
    run_ui.sessions[token] = int(time.time())
    return {"session_token": token}


def _fake_stream_output(tokens):
    """Build list of fake llama_cpp stream chunks."""
    for tok in tokens:
        yield {"choices": [{"delta": {"content": tok}}]}


def _parse_sse(resp_text):
    parsed = []
    for line in resp_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                parsed.append(json.loads(line[6:]))
            except Exception:
                pass
        elif line and not line.startswith(":"):
            try:
                parsed.append(json.loads(line))
            except Exception:
                pass
    return parsed


class TestStreamChunksTps:
    """Verify each streaming chunk includes live tps field."""

    def test_stream_chunks_contain_tps(self):
        tmp = tempfile.mkdtemp()
        port = 19200
        server, orig = _start_server(tmp, port)
        try:
            fake_llm = MagicMock()
            fake_llm.tokenize.return_value = [1, 2, 3]
            fake_llm.create_chat_completion.return_value = _fake_stream_output(["Hello", " world"])

            with patch("run_ui.load_local_model", return_value=fake_llm):
                resp = requests.post(
                    f"http://127.0.0.1:{port}/api/chat",
                    json={"model": "qwen2.5-vl-7b-instruct:latest", "messages": [{"role": "user", "content": "hi"}]},
                    cookies=_auth(), stream=True, timeout=10,
                )

            assert resp.status_code == 200
            parsed = _parse_sse(resp.text)

            streaming = [c for c in parsed if not c.get("done")]
            assert len(streaming) >= 2
            for c in streaming:
                assert "tps" in c, f"Missing tps in streaming chunk: {c}"
                assert isinstance(c["tps"], (int, float))
        finally:
            _stop_server(server, orig)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_final_chunk_contains_avg_tps(self):
        tmp = tempfile.mkdtemp()
        port = 19201
        server, orig = _start_server(tmp, port)
        try:
            fake_llm = MagicMock()
            fake_llm.tokenize.return_value = [1]
            fake_llm.create_chat_completion.return_value = _fake_stream_output(["A", "B", "C"])

            with patch("run_ui.load_local_model", return_value=fake_llm):
                resp = requests.post(
                    f"http://127.0.0.1:{port}/api/chat",
                    json={"model": "qwen2.5-vl-7b-instruct:latest", "messages": [{"role": "user", "content": "test"}]},
                    cookies=_auth(), stream=True, timeout=10,
                )

            parsed = _parse_sse(resp.text)
            final = [c for c in parsed if c.get("done")]
            assert len(final) == 1
            assert "avg_tps" in final[0]
            assert isinstance(final[0]["avg_tps"], (int, float))
            assert final[0]["avg_tps"] > 0
        finally:
            _stop_server(server, orig)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_tps_calculation_accuracy(self):
        tmp = tempfile.mkdtemp()
        port = 19202
        server, orig = _start_server(tmp, port)
        try:
            def slow_stream():
                for tok in ["a", "b", "c", "d", "e"]:
                    time.sleep(0.1)
                    yield {"choices": [{"delta": {"content": tok}}]}

            fake_llm = MagicMock()
            fake_llm.tokenize.return_value = [1]
            fake_llm.create_chat_completion.return_value = slow_stream()

            with patch("run_ui.load_local_model", return_value=fake_llm):
                resp = requests.post(
                    f"http://127.0.0.1:{port}/api/chat",
                    json={"model": "qwen2.5-vl-7b-instruct:latest", "messages": [{"role": "user", "content": "slow"}]},
                    cookies=_auth(), stream=True, timeout=15,
                )

            parsed = _parse_sse(resp.text)
            final = [c for c in parsed if c.get("done")][0]

            assert 3 < final["avg_tps"] < 30, f"avg_tps {final['avg_tps']} out of expected range"
        finally:
            _stop_server(server, orig)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_vision_error_response_no_tps(self):
        tmp = tempfile.mkdtemp()
        port = 19203
        server, orig = _start_server(tmp, port)
        try:
            fake_llm = MagicMock()

            with patch("run_ui.load_local_model", return_value=fake_llm), \
                 patch("run_ui.model_supports_vision", return_value=False):
                resp = requests.post(
                    f"http://127.0.0.1:{port}/api/chat",
                    json={
                        "model": "deepseek-r1-distill-qwen-7b-uncensored:latest",
                        "messages": [{"role": "user", "content": "describe"}],
                        "attachment": {"type": "image", "data": "abc", "mimeType": "image/png"},
                    },
                    cookies=_auth(), stream=True, timeout=10,
                )

            parsed = _parse_sse(resp.text)
            for c in parsed:
                assert "tps" not in c, "tps should not appear in vision-error response"
                assert "avg_tps" not in c, "avg_tps should not appear in vision-error response"
        finally:
            _stop_server(server, orig)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_image_attachment_stream_has_tps(self):
        """Vision-capable model + image -> stream still contains tps fields."""
        tmp = tempfile.mkdtemp()
        port = 19204
        server, orig = _start_server(tmp, port)
        try:
            fake_llm = MagicMock()
            fake_llm.tokenize.return_value = [1]
            fake_llm.create_chat_completion.return_value = _fake_stream_output(["desc"])
            fake_llm.metadata = {"tokenizer.chat_template": "dummy"}

            with patch("run_ui.load_local_model", return_value=fake_llm), \
                 patch("run_ui.model_supports_vision", return_value=True):
                resp = requests.post(
                    f"http://127.0.0.1:{port}/api/chat",
                    json={
                        "model": "qwen2.5-vl-7b-instruct:latest",
                        "messages": [{"role": "user", "content": "describe this"}],
                        "attachment": {"type": "image", "data": "abc123", "mimeType": "image/jpeg"},
                    },
                    cookies=_auth(), stream=True, timeout=10,
                )

            parsed = _parse_sse(resp.text)
            streaming = [c for c in parsed if not c.get("done")]
            assert len(streaming) >= 1
            assert "tps" in streaming[0]

            final = [c for c in parsed if c.get("done")]
            assert "avg_tps" in final[0]
        finally:
            _stop_server(server, orig)
            shutil.rmtree(tmp, ignore_errors=True)
