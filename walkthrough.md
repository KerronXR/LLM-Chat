# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Focus: Qwen2.5-VL (Default, Vision + OCR) + DeepSeek-R1 Distill Qwen (Text Reasoning) + Multi-Turn Dialogue + Web Search.

- **Models (`../Models/*.gguf`)**:
    * `qwen2.5-vl-7b-instruct:latest` -> `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` [Default]
    * `deepseek-r1-distill-qwen-7b-uncensored:latest` -> `DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf`
- **Vision Projectors**:
    * `qwen2.5-vl-7b-instruct:latest` -> `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf`
- **Assistant Model**:
    * None (Gemma / Llama retired to Recycle Bin).

## Core Architecture
- `run_ui.py`: Multi-threaded HTTP server (`PORT = 8000`). Auth cookie (`session_token`). Routes:
    * `GET /`: UI (`index.html`).
    * `GET /login.html`: Auth page.
    * `GET /persona.txt`: Load persistent persona.
    * `GET /api/history`: Load JSON chat history.
    * `POST /api/login`: Validate `password == "AAaa1111$"`.
    * `POST /api/chat`: SSE streaming response (`data: {...}\n\n`). Serialized under `_model_lock` preventing concurrent inference crashes. New request signals `_active_abort` to previous generation. Background heartbeat daemon sends `: ping\n\n` every 5.0s during prompt eval and generation preventing reverse proxy and browser idle timeouts. Executes web search if triggered; isolates search context by stripping `<web_search_results>` via `_strip_ctx` before committing to `history.json` and `record_session_turn` so continuation KV-cache and history stay unpolluted. Supports web search when `web_search == 'on'` even with attachments.
    * `POST /api/history`: Save JSON chat history. Empty array triggers `reset_chat_session()`.
    * `POST /api/logout`: Expire session.
    * `POST /save_persona`: Save persona text.
    * `normalize_incoming_attachments(data)`: Normalizes up to 3 attachments supporting `type: 'image'`, `kind: 'image'`, and MIME types (`image/*`), preserving `dataUrl`.
    * `build_continuation_turn(model_id, user_text)`: Formats turn tokens and stop sequences using ChatML tags (`<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n`, stops `["<|im_end|>"]`).
    * Disconnect resilience: Catches `(ConnectionResetError, ConnectionAbortedError, BrokenPipeError)`, logs at INFO, commits partial/completed turn to `record_session_turn` and auto-persists to `history.json` preserving continuation state. General exceptions call `reset_chat_session()`.
- `core.py`: Model loader + vision chat format handler + stateful session tracker.
    * `load_local_model(model_id)`: Singleton cache, `n_ctx=get_model_context_length(model_id)`, `n_gpu_layers=0`, `n_threads=max(1, os.cpu_count()-2)`, `flash_attn=True`.
    * `get_model_context_length(model_id)`: Allocates `8192` context window for vision model (`qwen2.5-vl-7b-instruct:latest`), `4096` for text model (`deepseek-r1-distill-qwen-7b-uncensored:latest`).
    * `_configure_chat_handler(llm, model_id)`:
        - Qwen-VL: `_Qwen25VisionHandler` wrapping `Qwen25VLChatHandler`, supports both `image_url` and `image` formats in `get_image_urls` and `CHAT_FORMAT` Jinja template.
    * `_chat_session`: Global session state `{"messages": [], "tokens": 0, "model_id": None}`.
    * `is_session_continuation(messages, model_id)`: Validates if request continues previous turn via `_norm_text`, stripping `<web_search_results>` tags.
    * `record_session_turn(messages, assistant_content, tokens_count, model_id)`: Commits turn.
    * `reset_chat_session()`: Clears session cache.
    * `cleanup_llm()`: Releases instance memory via `del` + `gc.collect()`.
    * `force_cleanup_port(port)`: Auto-kills ghost PID listening on port.
- `web_search.py`: Zero-dependency DuckDuckGo Lite search provider with concurrent live metrics:
    * `should_trigger_search(query_text, mode)`: Evaluates `auto`, `on`, `off` with temporal, news, stock, price, research heuristics and action prefix detection.
    * `clean_search_query(text)`: Normalizes query, strips conversational prefixes, clamps to 100 chars. Single source of truth.
    * `sanitize_search_result(text)`: Neutralizes prompt injection markers (`<system>`, `<|turn>`, `[INST]`, `</?web_search_results>`, `ignore previous instructions`), strips HTML tags, unescapes HTML entities.
    * `safe_duckduckgo_search(query, max_results=5, timeout=3.5)`: Concurrent execution via `ThreadPoolExecutor(max_workers=3)` running DuckDuckGo Lite search alongside `fetch_live_stock` and `fetch_live_weather`. Full browser headers prevent 202 bot challenges; filters `/y.js` ads and parses all rows until collecting `max_results` organic results.
    * `format_search_prompt_context(results, max_chars=1500)`: Formats results into `<web_search_results>` reference boundary with anti-refusal guidance.
- `live_data.py`: Zero-dependency real-time metrics providers:
    * `fetch_live_stock(ticker, timeout=2.5)`: Yahoo Finance chart API price, currency, day high/low.
    * `extract_stock_ticker(query)`: Resolves company names and symbol patterns only when financial intent (`stock`, `share`, `quote`, `ticker`, `market`, `trading`, `$TICKER`) is present.
    * `extract_weather_location(query)`: Extracts city/location from `<city> weather/forecast`, `temperature in <city>`, and `raining in <city>`.
    * `fetch_live_weather(location, timeout=2.5)`: Real-time weather from `wttr.in`.
- `search_context.py`: Multi-turn context-aware search query resolver:
    * `resolve_contextual_query(messages)`: Two-pass extraction. Resolves pronouns, action directives, dependent queries, expanding price lookups with `retail price MSRP`. Imports `clean_search_query` from `web_search.py`.
    * `extract_subject_from_history(messages)`: High-confidence search targets, product patterns, and quoted titles first; falls back to bold/capitalized entities while filtering structural phrases and store names.
    * `should_trigger_search_from_history(messages, mode)`: Detects auto search intent across conversation turns.
- `index.html`: Gemini Light UI. Model selector (Qwen2.5-VL default, DeepSeek-R1), multiple file upload input, dynamic attach button, web search toggle, context meter, chat thread, pill input area.
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
    * `state.js`: Global state management (`webSearchMode`, `attachedFiles`, `activeModel` defaults to `qwen2.5-vl-7b-instruct:latest`).
    * `dom.js`: Cached DOM element references.
    * `search.js`: Web search mode toggler (`auto`/`on`/`off`), `localStorage` persistence (`initWebSearchMode`), and compact sources summary badge (`🌐 {count} search results`).
    * `markdown.js`: Streaming-safe Markdown + table parser.
    * `ui.js`: Message rendering, auto-scroll, image viewer, Screen Wake Lock API management (`requestWakeLock`/`releaseWakeLock`) keeping mobile display active during generation.
    * `handlers.js`: Streaming SSE reader, instant thinking bubble creation, immediate UI clipboard clearing on send, mid-turn interruption support, search status updates, dynamic markdown render, live TPS counter, non-destructive streaming text injection preserving sources badge.
    * `api.js`: Fetch client wrappers.
    * `main.js`: Initialization, model select listener, attach button toggle based on `supportsVision` (active on Qwen-VL, hidden on DeepSeek), search toggle listener, `initWebSearchMode()`, `visibilitychange` handler resyncing history from `/api/history` on phone screen unlock.
- `LocalChat.bat`: Launch wrapper script for Windows.
- `history.json`: Active chat conversation persistence.
- `persona.txt`: System persona persistence.
- `logs/errors/`: Daily rotating error logs.
- `logs/audit/`: Audit deletion logs.

## Multi-Turn Vision Flow
1. User attaches up to 3 images in UI via file picker or clipboard paste.
2. `js/attachments.js`: Canvas downscales images to max 768px JPEG (quality 0.85).
3. On send:
   - UI preview immediately clears.
   - AI thinking bubble immediately renders.
   - Payload sends both standard `image_url` and `image` format.
4. Turn 1 (Initial):
   - Server receives base64 payloads.
   - `_Qwen25VisionHandler` tokenizes images + text, evals prompt into KV cache.
   - Streams generation at native speed.
   - Commits turn into `_chat_session`.
5. Turn 2+ (Follow-up):
   - Client sends conversation history without re-attaching image.
   - `is_session_continuation` returns `True`.
   - Bypasses handler context wipe (`kv_cache_clear`).
   - Tokenizes incremental turn using ChatML `<|im_start|>` tags.
   - Evals only new text tokens into active KV cache.
   - Clamps `max_tokens = min(2048, max(1, 4096 - llm.n_tokens - 1))`.
   - Streams response without image re-encode at full decode speed.

## Environment & Tests
- Python: 3.11 (`..\LLM\.venv\Scripts\python.exe`).
- Run backend & Playwright tests:
```bash
..\LLM\.venv\Scripts\python.exe -m pytest
```
- Start server:
```cmd
LocalChat.bat
```
