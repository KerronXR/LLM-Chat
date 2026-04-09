# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Uncensored: Dolphin Llama 3. Image gen: `FastSD CPU`. Persona. Local.

- **Models (`.gguf`)**:
    * Gemma-4 E4B (Latest 2026)
    * Gemma-4 E4B (Heretic Uncensored)
    * Dolphin Llama 3 (Uncensored)
    * Gemma-3 12B (Heretic)

## Core
- `run_ui.py`: Main entry. Start server. Manage LLM, `FastSD`.
- `setup_local_llm.py`: Install deps. Download `.gguf` → `models/`.
- `remove_ollama.bat`: Kill Ollama.
- `index.html`: UI.
- `css/`: Modular design. Mobile: `css/mobile.css`.
- `js/`: Modular logic (state, UI, API, handlers).
- `persona.txt`: System prompt. Auto-create.
- `models/`: `.gguf` storage.
- `images/`: Gen + upload storage.
- `logs/errors/`: Date logs (`error_YYYY-MM-DD.log`).
- `fastsdcpu/`: `FastSD CPU` engine. Venv: `fastsdcpu/env/`.

## Features
- **Local Chat**: Multi-turn. `llama-cpp-python`.
- **Stop**: Kill stream gen.
- **Token Track**: Context status bar.
- **Persona**: Save prompt → `persona.txt`. Auto-load.
- **Auto-Img**: Sidebar toggle. Input → Image gen. `Size`, `Batch` options.
- **Upscale**: "✨ Upscale Image" button. `SD upscale`. 2x res.
- **Batch**: Batch size > 1 → Multiple images.
- **Progress**: Animated bar.
- **Ref Img (img2img)**: Upload reference. Use as `init_image`.
- **Errors**: Chat display.
- **Logging**: Terminal + `logs/errors/`.
- **Theme**: Dark glassmorphism.

## Image Gen Flow
1. Enable **Auto Generate Images**.
2. Chat description → Enter.
3. Req → `FastSD CPU` port 8001. Params: `width`, `height`, `batch_size`.
4. Gen → `images/`. Return local URLs.
5. Thumbnail in chat. "✨ Upscale Image".
6. Upscale → `/api/upscale` in `FastSD CPU`. `aura_sr`.

- **Aura SR**: CPU upscale. Rapid.

### img2img
1. Upload reference.
2. Type `Generate Image style X`.
3. Auto-attach `init_image` → `FastSD CPU`.

## Services
- **Web UI / LLM API (`/api/chat`)**: http://localhost:8000
- **FastSD API**: http://localhost:8001 (auto-start `run_ui.py`)

## Env
- **Venv**: Python 3.11 req. `uv venv .venv --python 3.11 --seed`.
- **Setup**: `.venv\Scripts\python.exe setup_local_llm.py`.
- **Root**: `.venv/`. Managed `uv`.
- **FastSD CPU**: `fastsdcpu/env/` (Python 3.11).

## Start
Run `LocalAI.bat` or:
```
.venv\Scripts\python.exe run_ui.py
```
Ctrl+C stop. Reload `http://localhost:8000` for UI.

## Test
Full suite:
```
python -m pytest tests/ -v
```

### Files
- `tests/test_server.py`: API endpoints, logging, process helpers.
- `tests/test_ui.py`: Chat, context, persona, image gen.
- `tests/test_images.py`: Image UI.
- `tests/test_image_chat.py`: Keywords, Ref image, errors.
- `tests/test_mobile_responsiveness.py`: Viewport, sidebar.
- `tests/test_process_lifecycle.py`: Background services cleanup.
- `tests/test_slider_limits.py`: Batch UI.
- `tests/test_export.py`: Conversation export.

## Troubleshooting
- **Port 8000 In Use**: `netstat -ano | findstr :8000` → `taskkill /F /PID <PID>`.
- **No Images**: `fastsdcpu/env/` check. Port 8001 check. `logs/errors/` check.
- **Censored?**: Select **Dolphin Llama 3**. Restart server.
- **Gemma 4 fail**: Update `llama-cpp-python` >= 0.3.20. Run `setup_local_llm.py`.

## Recent
- **Mobile UI**: Status bar slimmed. Context Tracker priority.
- **Context Track**: Fixed hardcoded 0. Real tokens: `llm.tokenize()`.
- **Cleanup**: `run_ui.py` logic → `core.py`.
- **Stop/New**: UI toggle. "New" clears chat. "Stop" kills gen.
- **Timeout Fix**: `Content-Length` added persona/history. (Test pass).
- **Export**: Sidebar button → `.txt` download.
- **Streaming Batch**: Images appear one-by-one.
- **Clean Shutdown**: `atexit` + signals (SIGINT/SIGTERM/SIGBREAK).
- **RAM Manage**: LLM release + GC on exit. Port purge.
- **Default Model**: Gemma-4 Heretic main model.
- **Robust Stream**: NDJSON fix. `\r\n` support. `response.ok` check.
