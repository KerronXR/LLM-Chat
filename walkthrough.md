# Local AI

## Overview
Local AI env. `llama-cpp-python` LLM + web UI. Focus: Heretic Gemma-4 with Vision.

- **Models (`.gguf`)**:
    * Gemma-4 E4B (Heretic Uncensored) + Vision

## Core
- `run_ui.py`: Main entry. Multi-threaded. Auth. Routes.
- `core.py`: Logic layer. Model load. Vision config.
- `setup_local_llm.py`: Install deps. Download Heretic Gemma-4 → `../Models/`.
- `index.html`: Chat UI. Glassmorphism.
- `login.html`: Auth portal.
- `css/`: Modular styles.
- `js/`: Modular logic. State. UI. API.
- `persona.txt`: System prompt persistence.
- `history.json`: Chat history.
- `../Models/`: Weights. Project parent folder.
- `images/`: Uploaded image storage.
- `logs/errors/`: Daily logs.

## Features
- **Real-time Streaming**: Response tokens appear instantly. Anti-buffering via TCP_NODELAY.
- **TPS Tracking**: Show generation speed (tok/s) live + final avg badge.
- **Vision**: Image analysis. Req: Heretic Gemma-4.
- **Files**: Attach text/doc for context.
- **Auth**: Password (AAaa1111$).
- **Token Track**: Context status bar.
- **Persona**: Custom persistent system prompt.
- **Theme**: Dark glassmorphism.

## Vision Flow
1. Model: **Heretic Gemma-4**.
2. `core.py` loads `mmproj` projector.
3. UI Upload → Base64 → `attachment` JSON.
4. Server process vision messages.

## Lifecycle & RAM
- **Startup**: `force_cleanup_port` kills ghost 8000.
- **Switch Model**: `cleanup_llm` calls `del` + `gc.collect()`.
- **Shutdown**: Signal handling for clean exit.

## Services
- **Web UI / API**: http://localhost:8000

## Env
- **Venv**: Python 3.11. `uv venv`.

## Start
Run `LocalChat.bat`.

## Test
```
python -m pytest tests/ -v
```

## Troubleshooting
- **Port Busy**: Auto-killed by server.
- **Vision Fail**: Check `mmproj-google_gemma-4-E4B-it-f16.gguf` in `../Models/`.
