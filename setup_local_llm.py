import os
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Models"))

# We map the UI model identifiers to HuggingFace repo and filename.
MODELS_TO_DOWNLOAD = {
    "llama-3.2-3b-instruct-uncensored:latest": {
        "repo": "bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF",
        "filename": "Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf"
    },
    "deepseek-r1-distill-qwen-7b-uncensored:latest": {
        "repo": "mradermacher/DeepSeek-R1-Distill-Qwen-7B-Uncensored-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf"
    },
    "gemma-4-e4b-it:latest": {
        "repo": "bartowski/google_gemma-4-E4B-it-GGUF",
        "filename": "google_gemma-4-E4B-it-Q6_K.gguf"
    }
}
def install_dependencies():
    logger.info("Installing required python packages via uv...")
    try:
        # We use uv for fast installations.
        # Install huggingface_hub and test dependencies
        subprocess.check_call(["uv", "pip", "install", "--system", "huggingface_hub", "pytest", "pytest-base-url", "pytest-playwright"])
        
        # Install llama-cpp-python using the pre-built CPU wheels for windows
        # Version 0.3.15+ is required for robust Gemma 3 and Gemma 4 support.
        subprocess.check_call([
            "uv", "pip", "install", "-U", "--system",
            "llama-cpp-python>=0.3.20", 
            "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu"
        ])
    except Exception as e:
        logger.warning(f"Dependency installation failed (possibly lack of permissions): {e}")
        logger.info("Proceeding to download models anyway. Ensure dependencies are already installed.")

def download_models():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        logger.error("huggingface_hub is not installed. Did the dependency installation fail?")
        sys.exit(1)

    for ui_id, model_info in MODELS_TO_DOWNLOAD.items():
        repo_id = model_info["repo"]
        filename = model_info["filename"]
        target_path = os.path.join(MODELS_DIR, filename)

        if not os.path.exists(target_path):
            logger.info(f"Downloading {filename} from {repo_id} (this may take a while)...")
            try:
                # Download to cache and then symlink/copy to models dir
                downloaded_file = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=MODELS_DIR,
                    local_dir_use_symlinks=False
                )
                logger.info(f"Successfully downloaded {filename} to {downloaded_file}")
            except Exception as e:
                logger.error(f"Failed to download {filename}: {e}")
        else:
            logger.info(f"Model {filename} already exists at {target_path}. Skipping.")

if __name__ == "__main__":
    logger.info("Starting Local LLM Setup...")
    install_dependencies()
    download_models()
    logger.info("Setup complete! You can now start the server with LocalAI.bat")
