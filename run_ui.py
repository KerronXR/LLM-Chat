import http.server
import socketserver
import threading
import webbrowser
import os
import subprocess
import time
import signal
import logging
from datetime import datetime
import urllib.request
import json
import base64
import gc
import uuid
import secrets

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

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

PORT = 8000
FASTSD_PORT = 8001
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FASTSD_DIR = os.path.join(DIRECTORY, "fastsdcpu")
FASTSD_PYTHON = os.path.join(FASTSD_DIR, "env", "Scripts", "python.exe")
IMAGES_DIR = os.path.join(DIRECTORY, "images")
MODELS_DIR = os.path.join(DIRECTORY, "models")
HISTORY_FILE = os.path.join(DIRECTORY, "history.json")
SESSIONS_FILE = os.path.join(DIRECTORY, "sessions.json")
PASSWORD = "AAaa1111$"

# In-memory session store
sessions = {}

def load_sessions():
    global sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                sessions = json.load(f)
        except: sessions = {}

def save_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f)

load_sessions()

for d in [IMAGES_DIR, MODELS_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

llm_instance = None
current_model_path = None

MODELS_MAPPING = {
    "dolphin-llama3:latest": "dolphin-2.9-llama3-8b-q4_K_M.gguf",
    "gemma-3-12b-it:latest": "gemma-3-12b-it-heretic.Q4_K_M.gguf"
}

def load_local_model(model_id):
    global llm_instance, current_model_path
    if not HAS_LLAMA_CPP:
        raise RuntimeError("llama-cpp-python is not installed.")
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

def start_fastsd():
    def is_port_in_use(port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    if not is_port_in_use(FASTSD_PORT):
        logger.info(f"Starting FastSD CPU on {FASTSD_PORT}...")
        env = os.environ.copy()
        env["PATH"] = env.get("PATH", "") + ";" + os.path.join(FASTSD_DIR, "env", "Lib", "site-packages", "openvino", "libs")
        subprocess.Popen([FASTSD_PYTHON, os.path.join(FASTSD_DIR, "src", "app.py"), "--api", "--port", str(FASTSD_PORT)], cwd=FASTSD_DIR, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(5)

class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def get_session_token(self):
        cookie = self.headers.get('Cookie', '')
        if 'session_token=' in cookie:
            return cookie.split('session_token=')[-1].split(';')[0]
        return None

    def is_authenticated(self):
        token = self.get_session_token()
        return token and token in sessions

    def do_GET(self):
        # Exclude login page and static assets from auth for now, or serve login if not authed
        if self.path == '/login.html' or self.path.startswith('/js/') or self.path.startswith('/css/'):
            return super().do_GET()
        
        if not self.is_authenticated():
            if self.path.startswith('/api/'):
                self.send_response(401); self.end_headers()
                return
            # Redirect to login
            self.send_response(302)
            self.send_header('Location', '/login.html')
            self.end_headers()
            return

        if self.path == '/persona.txt':
            p = os.path.join(DIRECTORY, "persona.txt")
            if os.path.exists(p):
                self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
                with open(p, 'rb') as f: self.wfile.write(f.read())
            else: self.send_error(404)
        elif self.path == '/api/history':
            if os.path.exists(HISTORY_FILE):
                self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                with open(HISTORY_FILE, 'rb') as f: self.wfile.write(f.read())
            else:
                self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                self.wfile.write(b'[]')
        else: return super().do_GET()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length)
            
            if self.path == '/api/login':
                post_data = json.loads(raw_data)
                if post_data.get('password') == PASSWORD:
                    token = secrets.token_hex(32)
                    sessions[token] = int(time.time())
                    save_sessions()
                    self.send_response(200)
                    self.send_header('Set-Cookie', f'session_token={token}; HttpOnly; Path=/; Max-Age=2592000') # 30 days
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                else:
                    self.send_response(401); self.end_headers()
            
            elif not self.is_authenticated():
                self.send_response(401); self.end_headers()
                return

            elif self.path == '/api/chat':
                post_data = json.loads(raw_data)
                model_id = post_data.get('model', 'gemma-3-12b-it:latest')
                llm = load_local_model(model_id)
                self.send_response(200); self.send_header('Content-type', 'application/x-ndjson'); self.send_header('Transfer-Encoding', 'chunked'); self.end_headers()
                def send_chunk(chunk_data):
                    ds = json.dumps(chunk_data) + "\n"
                    self.wfile.write(f"{len(ds.encode()):X}\r\n{ds}\r\n".encode()); self.wfile.flush()
                try:
                    for output in llm.create_chat_completion(messages=post_data.get('messages', []), stream=True, max_tokens=4096):
                        if "content" in output["choices"][0]["delta"]:
                            send_chunk({"model": model_id, "message": {"role": "assistant", "content": output["choices"][0]["delta"]["content"]}, "done": False})
                    send_chunk({"model": model_id, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 0, "eval_count": 0})
                    self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
                except ConnectionError: pass
            elif self.path == '/generate_image':
                post_data = json.loads(raw_data)
                
                # Sanitize dimensions to prevent OpenVINO/Torch deadlocks (must be >= 256 and divisible by 8)
                safe_width = max(256, int(post_data.get('width', 512)))
                safe_width = (safe_width // 8) * 8
                safe_height = max(256, int(post_data.get('height', 512)))
                safe_height = (safe_height // 8) * 8

                req_body = {
                    "prompt": post_data.get('prompt', ''), "use_openvino": True, "number_of_images": post_data.get('batch_size', 1),
                    "image_width": safe_width, "image_height": safe_height, "diffusion_task": "text_to_image"
                }
                init = post_data.get('init_image')
                if init:
                    req_body["init_image"] = init.split(',')[1] if ',' in init else init
                    req_body["diffusion_task"] = "image_to_image"; req_body["strength"] = 0.5
                try:
                    req = urllib.request.Request(f"http://localhost:{FASTSD_PORT}/api/generate", data=json.dumps(req_body).encode(), headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=120) as response:
                        res_data = json.loads(response.read())
                        urls = []
                        for i, img_b64 in enumerate(res_data.get('images', [])):
                            filename = f"gen_{int(time.time())}_{i}.png"
                            with open(os.path.join(IMAGES_DIR, filename), "wb") as f: f.write(base64.b64decode(img_b64))
                            urls.append(f"/images/{filename}")
                        self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                        self.wfile.write(json.dumps({"urls": urls, "url": urls[0] if urls else None}).encode())
                except Exception as e:
                    self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Image generation failed: {str(e)}"}).encode())
            elif self.path == '/upscale_image':
                post_data = json.loads(raw_data)
                init = post_data.get('image', '')
                if init.startswith('data:'): init = init.split(',')[1]
                req_body = {"image": init, "mode": post_data.get('mode', 'aura_sr'), "scale_factor": 2, "strength": 0.3}
                try:
                    req = urllib.request.Request(f"http://localhost:{FASTSD_PORT}/api/upscale", data=json.dumps(req_body).encode(), headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=180) as response:
                        res_data = json.loads(response.read())
                        filename = f"upscale_{int(time.time())}.png"
                        with open(os.path.join(IMAGES_DIR, filename), "wb") as f: f.write(base64.b64decode(res_data['image']))
                        self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                        self.wfile.write(json.dumps({"url": f"/images/{filename}"}).encode())
                except Exception as e:
                    self.send_response(200); self.send_header('Content-type', 'application/json'); self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Upscale failed: {str(e)}"}).encode())
            elif self.path == '/api/history':
                with open(HISTORY_FILE, "wb") as f: f.write(raw_data)
                self.send_response(200); self.end_headers()
            elif self.path == '/api/logout':
                token = self.get_session_token()
                if token in sessions:
                    del sessions[token]
                    save_sessions()
                self.send_response(200)
                self.send_header('Set-Cookie', 'session_token=; HttpOnly; Path=/; Max-Age=0')
                self.end_headers()
            elif self.path == '/save_persona':
                with open(os.path.join(DIRECTORY, "persona.txt"), "w", encoding="utf-8") as f: f.write(raw_data.decode('utf-8'))
                self.send_response(200); self.end_headers()
            else: self.send_error(404)
        except ConnectionError: pass
        except Exception as e:
            logger.error(f"POST Error: {e}", exc_info=True)
            try: self.send_error(500, str(e))
            except ConnectionError: pass

    def log_message(self, format, *args): return

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

def run_server():
    start_fastsd()
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with ThreadedHTTPServer(("", PORT), Handler) as httpd:
            logger.info(f"Server ready at http://localhost:{PORT}"); webbrowser.open(f"http://localhost:{PORT}"); httpd.serve_forever()
    except Exception as e: logger.error(f"Server error: {e}")

if __name__ == "__main__":
    run_server()
