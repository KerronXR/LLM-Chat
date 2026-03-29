# 🚀 Local AI: Premium LLM & Image Generation Suite

A high-performance, fully localized AI environment featuring state-of-the-art LLM inference and stable diffusion image generation. This project combines `llama-cpp-python` with a stunning, modern web UI for a seamless local experience.

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Local-Inference](https://img.shields.io/badge/Local-Inference-blue)
![Python](https://img.shields.io/badge/Python-3.11-gold)

---

## ✨ Key Features

- **🛡️ Uncensored LLM Chat**: Full multi-turn support using `llama-cpp-python` (Dolphin Llama 3, Gemma-3 12B).
- **🎨 AI Image Generation**: Integrated **FastSD CPU** for rapid image creation without high-end GPU requirements.
- **✨ Image Upscaling**: Instant SD upscaling with `aura_sr` for flawless, high-resolution results.
- **🧠 Persistent Persona**: Save and auto-load custom system prompts to maintain consistent AI behavior.
- **📱 Responsive Design**: Premium glassmorphism UI optimized for both desktop and mobile devices.
- **⚡ Real-time Token Tracking**: Monitor context window usage live in the status bar.

---

## 🛠️ Architecture

| Component | Description |
| :--- | :--- |
| **`run_ui.py`** | Main server managing LLM inference & frontend services. |
| **`setup_local_llm.py`** | Automated dependency installation and model downloader. |
| **`fastsdcpu/`** | Dedicated backend for CPU-optimized image generation. |
| **`js/` & `css/`** | Modular, fast, and responsive frontend design system. |

---

## 🚀 Quick Start

### 1. Environment Setup
This project requires **Python 3.11**. We recomend using `uv` for lightning-fast environment management:
```bash
uv venv .venv --python 3.11
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
```

### 2. Install Dependencies & Models
Run the setup script to install all core libraries and download the recommended `.gguf` models:
```bash
python setup_local_llm.py
```

### 3. Launch the Application
Start the server and access the UI at `http://localhost:8000`:
```bash
LocalAI.bat
# OR
python run_ui.py
```

---

## 🖼️ Image Generation Workflow

1. Enable **Auto Generate Images** in the sidebar.
2. Type your prompt in the chat.
3. The system routes yours request to FastSD CPU (Port 8001).
4. Click **✨ Upscale Image** underneath any result to increase resolution instantly.

---

## 🧪 Testing

Maintain project stability by running our comprehensive test suite:
```bash
python -m pytest tests/ -v
```

> [!NOTE]
> All errors are dual-logged to the terminal and `logs/errors/` for easier debugging.

---

## 📜 License
*Project local to the user's workspace.*
