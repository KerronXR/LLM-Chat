import os
import gc
import logging
import subprocess
import time
import socket
from datetime import datetime

# Setup logging
ERROR_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "errors")
if not os.path.exists(ERROR_LOG_DIR):
    os.makedirs(ERROR_LOG_DIR)

def get_error_log_filename():
    return os.path.join(ERROR_LOG_DIR, f"error_{datetime.now().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_error_log_filename(), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Models"))
MODELS_MAPPING = {
    "llama-3.2-3b-instruct-uncensored:latest": "Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf",
    "deepseek-r1-distill-qwen-7b-uncensored:latest": "DeepSeek-R1-Distill-Qwen-7B-Uncensored.Q4_K_M.gguf",
    "gemma-4-e4b-it:latest": "google_gemma-4-E4B-it-Q6_K.gguf"
}

def get_chat_format(model_id):
    mid = (model_id or "").lower()
    if "llama-3" in mid or "llama3" in mid:
        return "llama-3"
    if "deepseek" in mid or "qwen" in mid:
        return "chatml"
    return "gemma"

ASSISTANT_MAPPING = {
    "gemma-4-e4b-it:latest": "gemma-4-E4B-it-assistant.Q8_0.gguf"
}
VISION_PROJECTOR_MAPPING = {
    "gemma-4-e4b-it:latest": "mmproj-google_gemma-4-E4B-it-f16.gguf"
}

llm_instance = None
current_model_path = None


class GemmaVisionChatHandler:
    def __init__(self, clip_model_path, chat_template, verbose=False):
        from llama_cpp.llama_chat_format import Llava15ChatHandler

        class _GemmaVisionHandler(Llava15ChatHandler):
            DEFAULT_SYSTEM_MESSAGE = None

            def __init__(self, clip_model_path, chat_template, verbose=False):
                super().__init__(clip_model_path=clip_model_path, verbose=verbose)
                self.CHAT_FORMAT = self._adapt_chat_template(chat_template)

            @staticmethod
            def _adapt_chat_template(chat_template):
                res = chat_template.replace("{{- '<|image|>' -}}", "{{- item['image'] if 'image' in item else item.get('image_url', '') -}}")
                return res.replace("{{- '\n\n<|image|>\n\n' -}}", "{{- item['image'] if 'image' in item else item.get('image_url', '') -}}")

            @staticmethod
            def get_image_urls(messages):
                image_urls = []
                for message in messages:
                    if message.get("role") != "user":
                        continue
                    content = message.get("content")
                    if not isinstance(content, list):
                        continue
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "image":
                            if isinstance(item.get("image"), str):
                                image_urls.append(item["image"])
                        elif item.get("type") == "image_url":
                            if isinstance(item.get("image_url"), dict) and "url" in item["image_url"]:
                                image_urls.append(item["image_url"]["url"])
                            elif isinstance(item.get("image_url"), str):
                                image_urls.append(item["image_url"])
                return image_urls

        self.handler = _GemmaVisionHandler(
            clip_model_path=clip_model_path,
            chat_template=chat_template,
            verbose=verbose,
        )


def model_supports_vision(model_id):
    projector = VISION_PROJECTOR_MAPPING.get(model_id)
    return bool(projector and os.path.exists(os.path.join(MODELS_DIR, projector)))


def _configure_chat_handler(llm, model_id):
    projector_name = VISION_PROJECTOR_MAPPING.get(model_id)
    if not projector_name:
        llm.chat_handler = None
        return llm

    projector_path = os.path.join(MODELS_DIR, projector_name)
    if not os.path.exists(projector_path):
        logger.warning("Vision projector missing for %s: %s", model_id, projector_path)
        llm.chat_handler = None
        return llm

    chat_template = llm.metadata.get("tokenizer.chat_template")
    if not chat_template:
        logger.warning("Chat template missing for %s; vision disabled.", model_id)
        llm.chat_handler = None
        return llm

    llm.chat_handler = GemmaVisionChatHandler(
        clip_model_path=projector_path,
        chat_template=chat_template,
        verbose=False,
    ).handler
    llm.chat_format = None
    return llm

def load_local_model(model_id):
    global llm_instance, current_model_path
    from llama_cpp import Llama
    filename = MODELS_MAPPING.get(model_id)
    if not filename:
        raise ValueError(f"Unknown model ID: {model_id}")
    model_path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    if current_model_path == model_path and llm_instance is not None:
        return llm_instance
    logger.info(f"Loading: {filename}...")
    if llm_instance is not None:
        del llm_instance
        gc.collect()
    
    chat_fmt = get_chat_format(model_id)
    n_threads = max(1, os.cpu_count() - 2)
    logger.info(f"Initializing Llama engine: format={chat_fmt}, threads={n_threads}")
    llm_instance = Llama(
        model_path=model_path, 
        n_gpu_layers=0, 
        n_ctx=4096, 
        n_threads=n_threads, 
        verbose=False, 
        chat_format=chat_fmt,
        flash_attn=True
    )
    
    _configure_chat_handler(llm_instance, model_id)
    current_model_path = model_path
    return llm_instance

def is_port_in_use(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', p)) == 0

def force_cleanup_port(port):
    """Forcefully kill any process using the specified port on Windows."""
    if not is_port_in_use(port):
        return
    logger.info(f"Cleaning up ghost process on port {port}...")
    if os.name == 'nt':
        try:
            # Find PID on this port
            cmd = f'netstat -ano | findstr :{port}'
            out = subprocess.check_output(cmd, shell=True).decode()
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    if pid != '0':
                        logger.info(f"Force killing PID {pid} tree...")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to force cleanup port {port}: {e}")



_chat_session = {"messages": [], "tokens": 0, "model_id": None}

def reset_chat_session():
    """Reset the multi-turn session cache."""
    _chat_session["messages"] = []
    _chat_session["tokens"] = 0
    _chat_session["model_id"] = None

def record_session_turn(messages, assistant_content, tokens_count, model_id=None):
    """Record completed chat turn into session state."""
    _chat_session["messages"] = [dict(m) for m in messages] + [{"role": "assistant", "content": assistant_content}]
    _chat_session["tokens"] = tokens_count
    if model_id:
        _chat_session["model_id"] = model_id

def is_session_continuation(messages, model_id=None):
    """Check if incoming messages extend current active session without new attachments."""
    if model_id and _chat_session["model_id"] and model_id != _chat_session["model_id"]:
        return False
    prior = _chat_session["messages"]
    if not prior or len(messages) != len(prior) + 1:
        return False
    
    def _norm_text(c):
        if isinstance(c, str):
            return c.strip()
        if isinstance(c, list):
            for item in c:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "").strip()
        return ""

    for p_msg, m_msg in zip(prior, messages[:-1]):
        if p_msg.get("role") != m_msg.get("role"):
            return False
        if _norm_text(p_msg.get("content")) != _norm_text(m_msg.get("content")):
            return False
    return messages[-1].get("role") == "user"

def cleanup_llm():
    """Explicitly release LLM instance and collect garbage to free memory."""
    global llm_instance
    reset_chat_session()
    if llm_instance is not None:
        logger.info("Cleaning up LLM instance memory...")
        del llm_instance
        llm_instance = None
        gc.collect()
        logger.info("Memory collection triggered.")



