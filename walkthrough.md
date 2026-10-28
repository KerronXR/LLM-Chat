# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Focus: Gemma-4 and Qwen2.5-VL with Vision + Multi-Turn Dialogue + Web Search.

- **Models (`../Models/*.gguf`)**:
    * `gemma-4-e4b-it:latest` -> `google_gemma-4-E4B-it-Q6_K.gguf` [Default]
    * `qwen2.5-vl-7b-instruct:latest` -> `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
    * `llama-3.2-3b-instruct-uncensored:latest` -> `Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf`
    * `deepseek-r1-distill-qwen-7b-uncensored:latest` -> `DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf`
- **Vision Projectors**:
    * `gemma-4-e4b-it:latest` -> `mmproj-google_gemma-4-E4B-it-f16.gguf`
    * `qwen2.5-vl-7b-instruct:latest` -> `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf`
- **Assistant Model**:
    * `gemma-4-e4b-it:latest` -> `gemma-4-E4B-it-assistant.Q8_0.gguf`

## Core Architecture
- `run_ui.py`: Multi-threaded HTTP server (`PORT = 8000`). Auth cookie (`session_token`). Routes:
    * `GET /`: UI (`index.html`).
    * `GET /login.html`: Auth page.
    * `GET /persona.txt`: Load persistent persona.
    * `GET /api/history`: Load JSON chat history.
    * `POST /api/login`: Validate `password == "AAaa1111$"`.
    * `POST /api/chat`: SSE streaming response (`data: {...}\n\n`). Background heartbeat daemon sends `: ping\n\n` every 5.0s during prompt eval and generation preventing reverse proxy and browser idle timeouts.
    * `POST /api/history`: Save JSON chat history. Empty array triggers `reset_chat_session()`.
    * `POST /api/logout`: Expire session.
    * `POST /save_persona`: Save persona text.
    * `normalize_incoming_attachments(data)`: Normalizes up to 3 attachments supporting `type: 'image'`, `kind: 'image'`, and MIME types (`image/*`), preserving `dataUrl`.
    * `build_continuation_turn(model_id, user_text)`: Formats turn tokens and stop sequences by model family (Gemma `<start_of_turn>`, Qwen/DeepSeek `<|im_start|>`, Llama-3 `<|start_header_id|>`).
    * Disconnect resilience: Catches `(ConnectionResetError, ConnectionAbortedError, BrokenPipeError)`, logs at INFO, commits partial/completed turn to `record_session_turn` and auto-persists to `history.json` preserving continuation state. General exceptions call `reset_chat_session()`.
- `core.py`: Model loader + vision chat format handler + stateful session tracker.
    * `load_local_model(model_id)`: Singleton cache, `n_ctx=get_model_context_length(model_id)`, `n_gpu_layers=0`, `n_threads=max(1, os.cpu_count()-2)`, `flash_attn=True`.
    * `get_model_context_length(model_id)`: Allocates `8192` context window for vision models (`gemma-4-e4b-it:latest`, `qwen2.5-vl-7b-instruct:latest`), `4096` for text models.
    * `_configure_chat_handler(llm, model_id)`:
        - Gemma: `GemmaVisionChatHandler` wrapping `Llava15ChatHandler`, adapts template `item['type'] == 'image'` -> `item['type'] in ('image', 'image_url')`, maps `{{- '<|image|>' -}}` -> `{{- item['image'] if 'image' in item else (item['image_url']['url'] if item['image_url'] is mapping else item['image_url']) -}}`.
        - Qwen-VL: `_Qwen25VisionHandler` wrapping `Qwen25VLChatHandler`, supports both `image_url` and `image` formats in `get_image_urls` and `CHAT_FORMAT` Jinja template.
    * `_chat_session`: Global session state `{"messages": [], "tokens": 0, "model_id": None}`.
    * `is_session_continuation(messages, model_id)`: Validates if request continues previous turn via `_norm_text`.
    * `record_session_turn(messages, assistant_content, tokens_count, model_id)`: Commits turn.
    * `reset_chat_session()`: Clears session cache.
    * `cleanup_llm()`: Releases instance memory via `del` + `gc.collect()`.
    * `force_cleanup_port(port)`: Auto-kills ghost PID listening on port.
- `web_search.py`: Zero-dependency DuckDuckGo Lite search provider:
    * `should_trigger_search(query_text, mode)`: Evaluates `auto`, `on`, `off` with temporal, news, stock, price, research heuristics and action prefix detection.
    * `clean_search_query(text)`: Normalizes query, strips conversational prefixes, clamps to 100 chars.
    * `sanitize_search_result(text)`: Strips HTML tags, neutralizes prompt injection markers (`<system>`, `<|turn>`, `[INST]`, `ignore previous instructions`), unescapes HTML entities.
    * `safe_duckduckgo_search(query, max_results=5, timeout=3.5)`: SSRF-safe request to DuckDuckGo Lite with full browser headers (`Origin`, `Referer`, `Sec-Fetch-*`) preventing 202 captcha bot challenges, filters sponsored `/y.js` ads, decodes redirect links via `uddg`.
    * `format_search_prompt_context(results, max_chars=1200)`: Formats results into `<web_search_results>` reference boundary with anti-refusal guidance.
- `live_data.py`: Zero-dependency real-time metrics providers:
    * `fetch_live_stock(ticker, timeout=2.5)`: Yahoo Finance chart API price, currency, day high/low.
    * `extract_stock_ticker(query)`: Resolves company names and symbol patterns.
    * `fetch_live_weather(location, timeout=2.5)`: Real-time weather from `wttr.in`.
- `search_context.py`: Multi-turn context-aware search query resolver:
    * `resolve_contextual_query(messages)`: Two-pass extraction. Resolves pronouns, action directives, dependent queries, expanding price lookups with `retail price MSRP`.
    * `extract_subject_from_history(messages)`: High-confidence search targets, product patterns, and quoted titles first; falls back to bold/capitalized entities while filtering structural phrases (`providing the best next step`, `typical listings`, `whether it is new or used`) and store names (`Amazon`, `Target`, `Walmart`, `eBay`).
    * `should_trigger_search_from_history(messages, mode)`: Detects auto search intent across conversation turns.
- `index.html`: Gemini Light UI. Model selector (including Qwen2.5-VL), multiple file upload input, dynamic attach button, web search toggle, context meter, chat thread, pill input area.
- `login.html`: Auth portal with Gemini Light card and button styles.
- `css/`: Modular styling (all files <= 300 LOC):
    * `base.css`: Gemini Light palette (`--bg-canvas: #f8fafd`, `--bg-surface: #f0f4f9`, `--bg-card: #ffffff`, `--text-main: #1f1f1f`, `--accent-primary: #0b57d0`).
    * `components.css`: Sidebar, chat container, user bubble (`#f0f4f9`), AI message (`#ffffff`), pill input, live TPS indicator.
    * `media.css`: Multi-image attachment preview thumbnails with remove buttons, image grid.
    * `search.css`: `.web-search-btn`, `.web-search-badge`, `.search-sources-summary`.
    * `buttons.css`: Send, stop, secondary, accent buttons.
    * `utility.css`: Status bar, minimal scrollbar, progress bar.
    * `markdown.css`: Light table styling, inline code formatting, typography.
    * `mobile.css`: `#mobile-toggle`, responsive drawer sidebar, mobile status bar.
- `js/`: Modular frontend (all files <= 300 LOC):
    * `attachments.js`: Staged attachments controller. Up to 3 images, preview rendering with `×` remove buttons, `Ctrl+V` clipboard paste listener, canvas JPEG normalization (768px max dim, 0.85 quality), payload preparation (`buildAttachmentsPayload`, `buildUserMessage`).
    * `state.js`: Global state management (`webSearchMode`, `attachedFiles`, `activeModel`).
    * `dom.js`: Cached DOM element references.
    * `search.js`: Web search mode toggler (`auto`/`on`/`off`) and compact sources summary badge (`🌐 {count} search results`).
    * `markdown.js`: Streaming-safe Markdown + table parser.
    * `ui.js`: Message rendering, auto-scroll, image viewer, Screen Wake Lock API management (`requestWakeLock`/`releaseWakeLock`) keeping mobile display active during generation.
    * `handlers.js`: Streaming SSE reader, instant thinking bubble creation, immediate UI clipboard clearing on send, mid-turn interruption support, search status updates, dynamic markdown render, live TPS counter.
    * `api.js`: Fetch client wrappers.
    * `main.js`: Initialization, model select listener, attach button toggle based on `isVisionModel` (Gemma and Qwen-VL), search toggle listener, `visibilitychange` handler resyncing history from `/api/history` on phone screen unlock.
- `LocalChat.bat`: Launch wrapper script for Windows.
- `history.json`: Active chat conversation persistence.
- `persona.txt`: System persona persistence.
- `logs/errors/`: Daily rotating error logs.

## Multi-Turn Vision Flow
1. User attaches up to 3 images in UI via file picker or clipboard paste.
2. `js/attachments.js`: Canvas downscales images to max 768px JPEG (quality 0.85).
3. On send:
   - UI preview immediately clears.
   - AI thinking bubble immediately renders.
   - Payload sends both standard `image_url` and `image` format.
4. Turn 1 (Initial):
   - Server receives base64 payloads.
   - `Llava15ChatHandler` or `_Qwen25VisionHandler` tokenizes images + text, evals prompt into KV cache.
   - Streams generation at native speed (~6.5 tok/s).
   - Commits turn into `_chat_session`.
5. Turn 2+ (Follow-up):
   - Client sends conversation history without re-attaching image.
   - `is_session_continuation` returns `True`.
   - Bypasses handler context wipe (`kv_cache_clear`).
   - Tokenizes incremental turn using model-specific tags (Gemma `<start_of_turn>`, Qwen `<|im_start|>`).
   - Evals only new text tokens into active KV cache.
   - Clamps `max_tokens = min(2048, max(1, 4096 - llm.n_tokens - 1))`.
   - Streams response without image re-encode at full decode speed.

## Environment & Tests
- Python: 3.11 (`..\LLM\.venv\Scripts\python.exe`).
- Run backend tests:
```bash
..\LLM\.venv\Scripts\python.exe -m pytest tests/test_multi_image_backend.py tests/test_vision_and_ui.py tests/test_web_search.py tests/test_web_search_context.py tests/test_stateful_multiturn.py tests/test_web_search_ui.py -v
```
- Run Playwright UI tests:
```bash
..\LLM\.venv\Scripts\python.exe -m pytest tests/test_multi_image_chat.py -v
```
- Start server:
```cmd
LocalChat.bat
```
