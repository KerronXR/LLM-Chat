# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Focus: Gemma-4 with Vision + Multi-Turn Dialogue.

- **Models (`../Models/*.gguf`)**:
    * `gemma-4-e4b-it:latest` -> `google_gemma-4-E4B-it-Q6_K.gguf` [Default]
    * `llama-3.2-3b-instruct-uncensored:latest` -> `Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf`
    * `deepseek-r1-distill-qwen-7b-uncensored:latest` -> `DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf`
- **Vision Projector**:
    * `gemma-4-e4b-it:latest` -> `mmproj-google_gemma-4-E4B-it-f16.gguf`
- **Assistant Model**:
    * `gemma-4-e4b-it:latest` -> `gemma-4-E4B-it-assistant.Q8_0.gguf`

## Core Architecture
- `run_ui.py`: Multi-threaded HTTP server (`PORT = 8000`). Auth cookie (`session_token`). Routes:
    * `GET /`: UI (`index.html`).
    * `GET /login.html`: Auth page.
    * `GET /persona.txt`: Load persistent persona.
    * `GET /api/history`: Load JSON chat history.
    * `POST /api/login`: Validate `password == "AAaa1111$"`.
    * `POST /api/chat`: SSE streaming response (`data: {...}\n\n`).
    * `POST /api/history`: Save JSON chat history. Empty array triggers `reset_chat_session()`.
    * `POST /api/logout`: Expire session.
    * `POST /save_persona`: Save persona text.
- `core.py`: Model loader + vision chat format handler + stateful session tracker.
    * `load_local_model(model_id)`: Singleton cache, `n_ctx=4096`, `n_gpu_layers=0`, `n_threads=max(1, os.cpu_count()-2)`, `flash_attn=True`.
    * `GemmaVisionChatHandler`: Wraps `Llava15ChatHandler`, adapts template `{{- '<|image|>' -}}` -> `{{- item['image'] if 'image' in item else item.get('image_url', '') -}}`.
    * `_chat_session`: Global session state `{"messages": [], "tokens": 0, "model_id": None}`.
    * `is_session_continuation(messages, model_id)`: Validates if request continues previous turn via `_norm_text`.
    * `record_session_turn(messages, assistant_content, tokens_count, model_id)`: Commits turn.
    * `reset_chat_session()`: Clears session cache.
    * `cleanup_llm()`: Releases instance memory via `del` + `gc.collect()`.
    * `force_cleanup_port(port)`: Auto-kills ghost PID listening on port.
- `web_search.py`: Zero-dependency DuckDuckGo Lite search provider with high-priority security hardening:
    * `should_trigger_search(query_text, mode)`: Evaluates `auto`, `on`, `off` with temporal/news regex heuristics.
    * `clean_search_query(text)`: Normalizes query, strips conversational prefixes, clamps to 100 chars.
    * `sanitize_search_result(text)`: Strips HTML tags, neutralizes prompt injection markers (`<system>`, `<|turn>`, `[INST]`, `ignore previous instructions`), unescapes HTML entities.
    * `safe_duckduckgo_search(query, max_results=3, timeout=3.5)`: SSRF-safe request strictly to DuckDuckGo Lite endpoint, decodes redirect links via `uddg`, validates `http`/`https` protocols.
    * `fetch_live_weather(location, timeout=2.5)`: Fetches real-time weather metrics (temp, condition, humidity, wind) for weather queries.
    * `format_search_prompt_context(results, max_chars=1200)`: Formats results into `<web_search_results>` reference boundary with anti-refusal guidance.
- `setup_local_llm.py`: Dependency verification + downloads.
- `index.html`: Dark glassmorphism UI. Model selector, dynamic attach button, web search toggle button, context meter, chat thread.
- `login.html`: Auth portal.
- `css/`: Modular styling (`base.css`, `components.css`, `markdown.css`, `buttons.css`, `utility.css`, `mobile.css`, `login.css`). Includes `.web-search-btn`, `.web-search-badge`, `.search-sources-container`, `.search-source-chip`.
- `js/`: Modular frontend:
    * `state.js`: Global state management (`webSearchMode`).
    * `dom.js`: Cached DOM element references.
    * `search.js`: Web search mode toggler (`auto`/`on`/`off`) and source chip badges renderer.
    * `markdown.js`: Zero-dependency streaming-safe Markdown + table parser (headings, lists, bold, inline/fenced code, dividers, pipe tables).
    * `ui.js`: Message rendering, auto-scroll, image viewer.
    * `handlers.js`: Streaming SSE reader, search status updates, dynamic markdown re-render, live TPS counter, image downscaler.
    * `api.js`: Fetch client wrappers.
    * `main.js`: Initialization, model select listener, attach button toggle, search toggle listener.
- `LocalChat.bat`: Launch wrapper script for Windows.
- `history.json`: Active chat conversation persistence.
- `persona.txt`: System persona persistence.
- `images/`: Local image storage.
- `logs/errors/`: Daily rotating error logs.

## Multi-Turn Vision Flow
1. User attaches image in UI.
2. `js/handlers.js:buildImageAttachmentPayload`: Canvas scales image max 768px JPEG (quality 0.85). Prevents CPU slice explosion and WebP decode errors.
3. Turn 1 (Initial):
   - Server receives base64 payload.
   - `Llava15ChatHandler` tokenizes image + text, runs `mtmd_helper_eval_chunk_single`, evals prompt into KV cache.
   - Streams generation at native speed (~6.5 tok/s).
   - Commits turn into `_chat_session`.
4. Turn 2+ (Follow-up):
   - Client sends full conversation history without re-attaching image.
   - `is_session_continuation` returns `True`.
   - Bypasses `Llava15ChatHandler` context wipe (`kv_cache_clear`).
   - Tokenizes incremental turn: `<turn|>\n<|turn>user\n{user_text}<turn|>\n<|turn>model\n`.
   - Evals only new text tokens into KV cache (`~25 tokens in ~1.8s`).
   - Clamps `max_tokens = min(2048, max(1, 4096 - llm.n_tokens - 1))`.
   - Streams response without image re-encode. Full decode speed (~6.2 - 6.7 tok/s) maintained.

## Memory & Process Lifecycle
- Port 8000 conflicts: Auto-killed by `force_cleanup_port` before server bind.
- Model swap: `cleanup_llm` flushes LLM pointer and runs `gc.collect()`.
- Shutdown: SIGINT, SIGTERM, and SIGBREAK captured for clean exit.

## Environment & Tests
- Python: 3.11 (`..\LLM\.venv\Scripts\python.exe`).
- Run tests:
```bash
..\LLM\.venv\Scripts\python.exe -m pytest tests/test_markdown_ui.py tests/test_stateful_multiturn.py tests/test_vision_and_ui.py tests/test_stream_completion.py tests/test_model_suite.py tests/test_multiturn_vision.py -v
```
- Start server:
```cmd
LocalChat.bat
```

## Troubleshooting
- **Port Busy**: Handled automatically by `force_cleanup_port`.
- **Assertion `GGML_ASSERT(i1 >= 0 && i1 < ne1)` in `ops.cpp`**: Requires `flash_attn=True` in `core.py` to prevent variable V-cache padding overflow on CPU.
- **WebP Bitmap Failure**: Stb image cannot decode WebP. Resolved by client-side canvas JPEG conversion before upload.
- **Turn 2 Speed Drop**: Caused by re-encoding full image on follow-up turns. Resolved by stateful KV reuse in `run_ui.py`.
