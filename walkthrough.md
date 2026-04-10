# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Uncensored: Dolphin Llama 3. Vision: Gemma-4. Image gen: `FastSD CPU`. Persona. Local.

- **Models (`.gguf`)**:
    * Gemma-4 E4B (Latest 2026) + Vision
    * Gemma-4 E4B (Heretic Uncensored) + Vision
    * Dolphin Llama 3 (Uncensored)
    * Gemma-3 12B (Heretic)

## Core
- `run_ui.py`: Main entry. Multi-threaded. Auth. Routes.
- `core.py`: Logic layer. Model load. Vision config. Process management.
- `setup_local_llm.py`: Install deps. Download `.gguf` → `models/`.
- `index.html`: Chat UI. Glassmorphism.
- `login.html`: Auth portal.
- `css/`: Modular styles. `mobile.css` responsive.
- `js/`: Modular logic. State. UI. API.
- `persona.txt`: System prompt. Persistence.
- `history.json`: Chat persistence.
- `sessions.json`: active session tokens.
- `models/`: Weights. `.gguf` + `mmproj`.
- `images/`: Gen + upload storage.
- `logs/errors/`: Daily logs (`error_YYYY-MM-DD.log`).
- `fastsdcpu/`: `FastSD CPU` engine. Venv: `fastsdcpu/env/`.

## Features
- **Local Chat**: Multi-turn. `llama-cpp-python`.
- **Vision**: Image input → description. Req: **Gemma-4 E4B**.
- **Files**: Attach text/doc → context injection.
- **Auth**: Password (`AAaa1111$`) → Session Cookie.
- **Stop**: Kill stream gen.
- **Token Track**: Context status bar. Tokenize → `n_ctx` limit.
- **Persona**: Custom prompt → `persona.txt`. Auto-injection.
- **Auto-Img**: Chat desc → SD prompt. Side-toggle.
- **Upscale**: `aura_sr`. 2x res.
- **Batch**: Multiple images sequential.
- **Theme**: Dark glassmorphism.

## Vision Flow
1. Select **Gemma-4 E4B** model.
2. `core.py` checks `mmproj` projector weight.
3. `GemmaVisionChatHandler` adapts template.
4. UI Upload → Base64 → `attachment` JSON.
5. Server: Role `user` msg → List `[{type: image}, {type: text}]`.
6. `llm.create_chat_completion` process.

## Image Gen Flow
1. Enable **Auto Generate Images**.
2. Prompt → `/generate_image`.
3. Server → `FastSD CPU` (localhost:8001).
4. `use_openvino`: True. Port: 8001.
5. Gen → `images/`. NDJSON stream URLs → UI.
6. "✨ Upscale" → `/api/upscale` → `FastSD`.

## Lifecycle & RAM
- **Startup**: `force_cleanup_port` kills ghost 8000/8001.
- **Switch Model**: `cleanup_llm` calls `del` + `gc.collect()`.
- **Shutdown**: `atexit` + signals (`SIGINT`, `SIGTERM`, `SIGBREAK`).
- **Cleanup**: Force kill `fastsd_process` tree via `taskkill /F /T`.

## Services
- **Web UI / API**: http://localhost:8000
- **FastSD API**: http://localhost:8001

## Env
- **Venv**: Python 3.11. `uv venv`.
- **FastSD**: `fastsdcpu/env/`. OpenVINO libs added to `PATH`.

## Start
Run `LocalAI.bat` or:
```
.venv\Scripts\python.exe run_ui.py
```

## Test
```
python -m pytest tests/ -v
```
- `tests/test_server.py`: API endpoints, auth, logging.
- `tests/test_ui.py`: Chat, context, persona, image gen.
- `tests/test_images.py`: Image UI, upscale.
- `tests/test_vision.py`: Image analysis check.

## Troubleshooting
- **Port Busy**: `netstat -ano | findstr :8000`. `run_ui.py` auto-kills.
- **Vision Fail**: Check `mmproj-google_gemma-4-E4B-it-f16.gguf` in `models/`.
- **Memory**: 16GB RAM recommended. GC triggered on model switch.
