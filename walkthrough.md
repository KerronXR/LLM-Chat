# Local AI Project

## Overview
Local AI env. `llama-cpp-python` LLM + web UI interaction. Uncensored mode: Dolphin Llama 3. Chat-driven image gen: `FastSD CPU`. Persistent persona. All local.

- **Models (`.gguf`)**:
    * Gemma-4 E4B (Latest 2026) - [NEW]
    * Gemma-4 E4B (Heretic Uncensored) - [NEW]
    * Dolphin Llama 3 (Uncensored)
    * Gemma-3 12B (Heretic)

## Core
- `run_ui.py`: Main entry. Start web server. Manage LLM + `FastSD`.
- `setup_local_llm.py`: Setup. Install deps. Download `.gguf` → `models/`.
- `remove_ollama.bat`: Kill global Ollama.
- `index.html`: UI structure.
- `css/`: Modular design. Mobile responsive: `css/mobile.css`.
- `js/`: Modular logic (state/UI/API/handlers).
- `persona.txt`: Custom system prompt storage. Auto-create.
- `models/`: `.gguf` storage.
- `images/`: Gen + upload storage.
- `logs/errors/`: Date-based logs (`error_YYYY-MM-DD.log`). Write on run.
- `fastsdcpu/`: `FastSD CPU` engine. Dedicated venv: `fastsdcpu/env/`.

## Features
- **Local Chat**: Multi-turn context. `llama-cpp-python`.
- **Stop**: Kill stream gen.
- **Token Track**: Context usage status bar.
- **Persona**: Save prompt → `persona.txt`. Auto-load.
- **Auto-Img**: Toggle sidebar check. Input text → Image gen. `Size` + `Batch` options.
- **Upscale**: "✨ Upscale Image" button. `SD upscale` pipeline. 2x res.
- **Batch**: Batch size > 1 → Multiple images in chat.
- **Progress**: Animated bar top of chat. Gen start → bar visible.
- **Ref Img (img2img)**: Sidebar "Upload Reference Image" + "Auto Generate Images". Use as `init_image`.
- **Errors**: Inline chat display.
- **Logging**: Terminal + `logs/errors/error_YYYY-MM-DD.log`.
- **Theme**: Dark glassmorphism.

## Image Gen Flow
1. Enable **Auto Generate Images**.
2. Chat input description → Enter.
3. Req → `FastSD CPU` port 8001. Params: `width`, `height`, `batch_size`.
4. Gen → `images/`. Return local URLs.
5. Thumbnail in chat. "✨ Upscale Image" button.
6. Upscale → `/api/upscale` in `FastSD CPU`. `aura_sr` used.

- **Aura SR**: CPU upscale. Rapid. No PyTorch interference.

### img2img
1. Upload reference.
2. Type `Generate Image style X`.
3. Auto-attach `init_image` → `FastSD CPU`.

## Services
- **Web UI / LLM API (`/api/chat`)**: http://localhost:8000
- **FastSD API**: http://localhost:8001 (auto-start via `run_ui.py`)

## Env
- **Venv**: Python 3.11 req for `llama-cpp-python` wheels. `uv venv .venv --python 3.11 --seed`.
- **Setup**: `.venv\Scripts\python.exe setup_local_llm.py`.
- **Root**: `.venv/`. Managed via `uv`.
- **FastSD CPU**: `fastsdcpu/env/` (Python 3.11).

## Start
Run `LocalAI.bat` or:
```
.venv\Scripts\python.exe run_ui.py
```
Ctrl+C stop. Reload `http://localhost:8000` for UI changes.

## Test
Full suite:
```
python -m pytest tests/ -v
```

### Files
- `tests/test_server.py`: API endpoints / logging / process helpers.
- `tests/test_ui.py`: Chat / context / persona / image gen.
- `tests/test_images.py`: Image UI elements.
- `tests/test_image_chat.py`: Keywords / Ref image / errors.
- `tests/test_mobile_responsiveness.py`: Viewport / sidebar toggle.
- `tests/test_process_lifecycle.py`: Background services cleanup.
- `tests/test_slider_limits.py`: Batch UI updates.
- `tests/test_export.py`: Conversation export.

## Troubleshooting
- **Port 8000 In Use**: `netstat -ano | findstr :8000` → `taskkill /F /PID <PID>`.
- **No Images**: `fastsdcpu/env/` check. Port 8001 check. `logs/errors/` check.
- **Censored?**: Select **Dolphin Llama 3**. Restart server if needed.
- **Gemma 4 fail**: Update `llama-cpp-python` >= 0.3.20. Run `setup_local_llm.py`.

## Recent
- **Mobile UI**: Status bar slimmed. Context Tracker priority.
- **Context Track**: Fixed hardcoded 0. Real tokens: `llm.tokenize()`.
- **Cleanup**: `run_ui.py` logic → `core.py`.
- **Stop/New**: UI toggle. "New" clears chat. "Stop" kills gen.
- **Timeout**: `FastSD` req 10m. Upscale 5m. `Content-Length` headers added.
- **Export**: Sidebar button → `.txt` history download.
- **Streaming Batch**: Images appear one-by-one. No timeouts.
- **Clean Shutdown**: `atexit` + signals (SIGINT/SIGTERM/SIGBREAK).
- **RAM Manage**: LLM release + GC on exit. Startup port purge.
- **Robust Stream**: NDJSON fix. `\r\n` support. `response.ok` check.
