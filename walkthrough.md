# Local AI Project Walkthrough

## Overview
This project provides a fully localized AI environment using `llama-cpp-python` for LLMs and a premium Python web UI for interaction. It features specialized "Uncensored Mode" for models like Dolphin Llama 3, chat-driven image generation via FastSD CPU, and persistent persona saving. Everything is contained within the project directory.

- **Supported Local LLM Models (`.gguf`)**:
    * Dolphin Llama 3 (Uncensored)
    * Gemma-3 12B (Heretic)

## Core Components
- `run_ui.py`: Main entry point. Starts web server, manages Local LLM inference & FastSD services.
- `setup_local_llm.py`: Setup script to install dependencies and download `.gguf` models to `models/`.
- `remove_ollama.bat`: Script to completely remove the old global Ollama installation.
- `index.html`: Frontend UI structure.
- `css/`: Modular design system including mobile responsiveness (`css/mobile.css`).
- `js/`: Modular frontend logic split into state, UI, API, and event handlers.
- `persona.txt`: Persistent storage for the custom system prompt (auto-created on save).
- `models/`: Directory where downloaded `.gguf` model files are stored.
- `images/`: Generated and uploaded images are stored here and served by the web server.
- `logs/errors/`: Date-based error logs (`error_YYYY-MM-DD.log`) — written on every server run.
- `fastsdcpu/`: FastSD CPU image generation engine (uses its own Python venv).
- `images/`: Generated and uploaded images are stored here and served by the web server.
- `logs/errors/`: Date-based error logs (`error_YYYY-MM-DD.log`) — written on every server run.
- `fastsdcpu/`: FastSD CPU image generation engine (uses its own Python venv in `fastsdcpu/env/`).

## Features
- **Local LLM Chat**: Full multi-turn context support using `llama-cpp-python` directly in Python.
- **Stop Button**: Immediately terminates streaming generation.
- **Token Tracking**: Real-time context window usage in the status bar.
- **Persona Persistence**: Save custom system prompt to `persona.txt`; auto-loads on next visit.
- **Auto-Generate Image Mode**: Toggle the "Auto Generate Images" checkbox in the sidebar. When active, every prompt sent in the chat will trigger image generation instead of a text response. Additional options for `Image Size` and `Batch Size` are available.
- **Image Upscaling**: Click the "✨ Upscale Image" button below generated images to run an SD upscale pipeline, doubling the resolution while preserving details.
- **Batch Image Generation**: When generating images, if a batch size greater than 1 is selected, multiple images will be returned and displayed in the chat.
- **Progress Visibility**: A premium animated progress bar appears at the top of the chat window during both LLM and Image generation requests.
- **Reference Image (img2img)**: Upload a reference image via the sidebar "Upload Reference Image" button and enable "Auto Generate Images". The system automatically includes the image as `init_image` for the generation.
- **Error Display**: Image generation errors appear inline in chat (no alert popups).
- **Dual Logging**: All errors printed to terminal AND written to `logs/errors/error_YYYY-MM-DD.log`.
- **Glassmorphism UI**: Premium dark theme with smooth animations.

## How Image Generation Works
1. Enable the **Auto Generate Images** checkbox in the sidebar.
2. Type your description in the chat input and press Enter/Send.
3. The system routes the request to FastSD CPU on port 8001, including specified `width`, `height`, and `batch_size`.
4. Generated images are saved to `images/` and an array of local URLs is returned.
5. Each image appears as a clickable thumbnail in the chat window with an "✨ Upscale Image" button.
6. Clicking "Upscale Image" triggers the `/api/upscale` endpoint in FastSD CPU using `aura_sr` for rapid and flawless upscaling on CPU without PyTorch interference.

- **Aura SR Upscaling (FastSD CPU)**: Instantly upscale your generated images or user-provided reference images using the integrated AI upscaler directly within the chat! Uses `aura_sr` for rapid and flawless upscaling on CPU without PyTorch interference.


### Using a Reference Image (img2img)
1. Click "Upload Reference Image" in the sidebar to upload a reference
2. Type `Generate Image cyberpunk style` in chat
3. The system automatically attaches the uploaded reference image as `init_image` to FastSD CPU without requiring any extra keywords.

## Services
- **Web UI & Local LLM API (`/api/chat`)**: http://localhost:8000
- **FastSD API**: http://localhost:8001 (started automatically by `run_ui.py`)

## Environment Setup
- **Virtual Environment**: This project requires Python 3.11 to install `llama-cpp-python` successfully using pre-built wheels. Recreate it with `uv` if needed: `uv venv .venv --python 3.11 --seed`
- **Initial Setup**: Run `.venv\Scripts\python.exe setup_local_llm.py` to install dependencies and download `.gguf` models into the `models/` directory.
- **Root Project**: Uses a virtual environment in `.venv/`. Managed via `uv`.
- **FastSD CPU**: Uses a dedicated virtual environment in `fastsdcpu/env/` (Python 3.11).

## Starting the Server
Run `LocalAI.bat` or:
```
.venv\Scripts\python.exe run_ui.py
```
The server stays alive in the terminal until you close it with **Ctrl+C**.  
To see frontend changes, just **reload `http://localhost:8000`** — no restart needed.

## Testing
Run the full functional test suite:
```
python -m pytest tests/ -v
```

### Test Files
- `tests/test_server.py` — Server-side unit tests (endpoints, logging, process helpers)
- `tests/test_ui.py` — Playwright UI tests (chat flow, context, persona, image gen)
- `tests/test_images.py` — Playwright image UI element tests
- `tests/test_image_chat.py` — Playwright tests for chat-driven image generation (keyword detection, Use My Image, error handling, sidebar cleanup)
- `tests/test_mobile_responsiveness.py` — Playwright tests for mobile viewport layout (menu button spacing, sidebar toggle logic)

### Troubleshooting
### WinError 10048 (Address already in use)
```
netstat -ano | findstr :8000
taskkill /F /PID <PID>
```

### FastSD not generating images?
- Make sure `fastsdcpu/env/` exists (run `fastsdcpu/install.bat` if not).
- Check `logs/errors/` for detailed error output.
- FastSD API runs on port 8001 — ensure it's not blocked by another process.

### Model still acting censored?
1. Select **Dolphin Llama 3** from the model dropdown in the sidebar.
2. The UI will automatically switch to the uncensored persona.
3. Restart the server if you want to force a clean reload of the model.

### Failed to load Gemma 3 model?
- Ensure `llama-cpp-python` is updated to version 0.3.15 or newer. This is required for the new Gemma 3 architecture support.
- Run `.venv\Scripts\python.exe setup_local_llm.py` to ensure the correct package versions are installed after any major model updates.

- **Mobile UI Fixes**: Streamlined the status bar on mobile to hide redundant URLs (Server/Ollama) and emphasize the **Context Tracker**, ensuring it is visible even on small screens with bottom toolbars.
- **Improved Context Tracking**: Resolved a bug where token counts were hardcoded to 0. The server now accurately calculates prompt and completion tokens using `llm.tokenize()`, providing real-time accuracy in the UI.
- **Architectural Cleanup**: Refactored `run_ui.py` to move core logic to `core.py`, adhering to the < 300 line project standard while improving maintenance.
- **Stop/New Multi-Purpose Button**: Enhanced the chat input area by replacing the disabled "Stop" button with a "New" button during idle phases. Clicking "New" clears the current conversation, while the button dynamically switches to "Stop" during active generation to allow immediate termination.
