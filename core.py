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

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODELS_MAPPING = {
    "dolphin-llama3:latest": "dolphin-2.9-llama3-8b-q4_K_M.gguf",
    "gemma-3-12b-it:latest": "gemma-3-12b-it-heretic.Q4_K_M.gguf"
}

llm_instance = None
current_model_path = None

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
    llm_instance = Llama(model_path=model_path, n_gpu_layers=0, n_ctx=8192, n_threads=max(1, os.cpu_count() - 2), verbose=False)
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

fastsd_process = None

def start_fastsd(fastsd_dir, port):
    global fastsd_process
    if not is_port_in_use(port):
        logger.info(f"Starting FastSD CPU on {port}...")
        python_exe = os.path.join(fastsd_dir, "env", "Scripts", "python.exe")
        env = os.environ.copy()
        env["PATH"] = env.get("PATH", "") + ";" + os.path.join(fastsd_dir, "env", "Lib", "site-packages", "openvino", "libs")
        fastsd_process = subprocess.Popen([python_exe, os.path.join(fastsd_dir, "src", "app.py"), "--api", "--port", str(port)], cwd=fastsd_dir, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(5)
    return fastsd_process

def cleanup_llm():
    """Explicitly release LLM instance and collect garbage to free memory."""
    global llm_instance
    if llm_instance is not None:
        logger.info("Cleaning up LLM instance memory...")
        # Llama class handles its own C++ destruction in __del__
        # but we help by deleting the Python reference and collecting
        del llm_instance
        llm_instance = None
        gc.collect()
        logger.info("Memory collection triggered.")

def stop_fastsd():
    global fastsd_process
    if fastsd_process:
        logger.info("Stopping FastSD CPU...")
        try:
            # Try gentle first
            fastsd_process.terminate()
            fastsd_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.warning("Standard termination timed out. Force killing tree...")
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(fastsd_process.pid)], capture_output=True)
            else:
                fastsd_process.kill()
        except Exception as e:
            logger.error(f"Error stopping FastSD process: {e}")
        finally:
            fastsd_process = None
