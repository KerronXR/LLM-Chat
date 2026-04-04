import http.server, socketserver, os, json, base64, time, secrets, urllib.request, logging
from core import load_local_model, start_fastsd, stop_fastsd, logger, MODELS_MAPPING, MODELS_DIR
import atexit, signal

PORT, FASTSD_PORT = 8000, 8001
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FASTSD_DIR, IMAGES_DIR = os.path.join(DIRECTORY, "fastsdcpu"), os.path.join(DIRECTORY, "images")
HISTORY_FILE, SESSIONS_FILE, PASSWORD = os.path.join(DIRECTORY, "history.json"), os.path.join(DIRECTORY, "sessions.json"), "AAaa1111$"

sessions = {}
def save_sessions():
    with open(SESSIONS_FILE, 'w') as f: json.dump(sessions, f)
if os.path.exists(SESSIONS_FILE):
    try:
        with open(SESSIONS_FILE, 'r') as f: sessions = json.load(f)
    except: pass
for d in [IMAGES_DIR, MODELS_DIR]:
    if not os.path.exists(d): os.makedirs(d)

class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def is_authenticated(self):
        cookie = self.headers.get('Cookie', '')
        if 'session_token=' not in cookie: return False
        try:
            # More robust split for various cookie formats
            parts = cookie.split('session_token=')[1].split(';')[0]
            token = parts.strip()
            return token and token in sessions
        except: return False

    def do_GET(self):
        if self.path in ['/login.html'] or self.path.startswith(('/js/', '/css/')): return super().do_GET()
        if not self.is_authenticated(): self.send_response(302); self.send_header('Location', '/login.html'); self.end_headers(); return
        if self.path == '/persona.txt' and os.path.exists(os.path.join(DIRECTORY, "persona.txt")):
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.end_headers()
            with open(os.path.join(DIRECTORY, "persona.txt"), 'rb') as f: self.wfile.write(f.read())
        elif self.path == '/api/history':
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'rb') as f: self.wfile.write(f.read())
            else: self.wfile.write(b'[]')
        else: return super().do_GET()

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if self.path == '/api/login':
                if json.loads(raw).get('password') == PASSWORD:
                    t = secrets.token_hex(32); sessions[t] = int(time.time()); save_sessions()
                    resp = b'{"status":"ok"}'
                    self.send_response(200); self.send_header('Set-Cookie', f'session_token={t}; HttpOnly; Path=/; Max-Age=2592000'); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(resp))); self.end_headers(); self.wfile.write(resp)
                else: self.send_error(401)
            elif not self.is_authenticated(): self.send_error(401)
            elif self.path == '/api/chat': self.handle_chat(raw)
            elif self.path == '/generate_image': self.handle_image(raw)
            elif self.path == '/api/upscale' or self.path == '/upscale_image': self.handle_upscale(raw)
            elif self.path == '/api/history':
                with open(HISTORY_FILE, "wb") as f: f.write(raw)
                self.send_response(200); self.end_headers()
            elif self.path == '/api/logout':
                t = self.headers.get('Cookie', '').split('session_token=')[-1].split(';')[0] if 'session_token=' in self.headers.get('Cookie', '') else None
                if t in sessions: del sessions[t]; save_sessions()
                self.send_response(200); self.send_header('Set-Cookie', 'session_token=; Max-Age=0; Path=/'); self.send_header('Content-Length', '0'); self.end_headers()
            elif self.path == '/save_persona':
                with open(os.path.join(DIRECTORY, "persona.txt"), "wb") as f: f.write(raw)
                self.send_response(200); self.end_headers()
            else: self.send_error(404)
        except Exception as e: logger.error(f"POST {self.path} Error: {e}", exc_info=True); self.send_error(500, str(e)) if not getattr(self.wfile, 'closed', False) else None

    def handle_chat(self, raw):
        data = json.loads(raw); mid = data.get('model', 'gemma-3-12b-it:latest'); llm = load_local_model(mid)
        self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson'); self.send_header('Transfer-Encoding', 'chunked'); self.end_headers()
        def chunk(obj):
            ds = json.dumps(obj) + "\n"; b = ds.encode()
            self.wfile.write(f"{len(b):X}\r\n".encode() + b + b"\r\n"); self.wfile.flush()
        msg = data.get('messages', []); ec, pc = 0, len(llm.tokenize(json.dumps(msg).encode()))
        try:
            for out in llm.create_chat_completion(messages=msg, stream=True, max_tokens=4096):
                delta = out["choices"][0]["delta"]
                if "content" in delta:
                    ec += 1; chunk({"model": mid, "message": {"role": "assistant", "content": delta["content"]}, "done": False})
            chunk({"model": mid, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": pc, "eval_count": ec, "context_length": 8192})
            self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
        except: pass

    def handle_image(self, raw):
        try:
            data = json.loads(raw)
            width = (max(256, int(data.get('width', 512))) // 8) * 8
            height = (max(256, int(data.get('height', 512))) // 8) * 8
            batch_size = int(data.get('batch_size', 1))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-ndjson')
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            
            def send_chunk(obj):
                ds = (json.dumps(obj) + "\n").encode()
                self.wfile.write(f"{len(ds):X}\r\n".encode() + ds + b"\r\n")
                self.wfile.flush()

            urls = []
            for i in range(batch_size):
                body = {
                    "prompt": data.get('prompt', ''),
                    "use_openvino": True,
                    "number_of_images": 1,
                    "image_width": width,
                    "image_height": height,
                    "diffusion_task": "text_to_image"
                }
                if data.get('init_image'):
                    body["init_image"] = data['init_image'].split(',')[1] if ',' in data['init_image'] else data['init_image']
                    body["diffusion_task"] = "image_to_image"
                    body["strength"] = 0.5
                
                req = urllib.request.Request(f"http://localhost:{FASTSD_PORT}/api/generate", data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=1800) as res:
                    rd = json.loads(res.read())
                    for b64 in rd.get('images', []):
                        fn = f"gen_{int(time.time())}_{i}.png"
                        with open(os.path.join(IMAGES_DIR, fn), "wb") as f:
                            f.write(base64.b64decode(b64))
                        url = f"/images/{fn}"
                        urls.append(url)
                        send_chunk({"url": url, "index": i + 1, "total": batch_size})
            
            send_chunk({"done": True, "urls": urls})
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            try: send_chunk({"error": str(e)})
            except: pass
            try: self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
            except: pass

    def handle_upscale(self, raw):
        try:
            data = json.loads(raw)
            image_b64 = data.get('image', '') # From UI or previous gen
            if not image_b64 and data.get('image_path'):
                 # Load from disk if path provided
                 path = data['image_path'].lstrip('/')
                 full_path = os.path.join(DIRECTORY, path)
                 if os.path.exists(full_path):
                     with open(full_path, "rb") as f:
                         image_b64 = base64.b64encode(f.read()).decode()

            init = image_b64.split(',')[1] if ',' in image_b64 else image_b64
            body = {"image": init, "mode": data.get('mode', 'aura_sr'), "scale_factor": 2, "strength": 0.3}
            
            req = urllib.request.Request(f"http://localhost:{FASTSD_PORT}/api/upscale", data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=600) as res:
                rd = json.loads(res.read())
                fn = f"upscale_{int(time.time())}.png"
                if 'image' in rd:
                    with open(os.path.join(IMAGES_DIR, fn), "wb") as f: f.write(base64.b64decode(rd['image']))
                    resp_data = json.dumps({"url": f"/images/{fn}"}).encode()
                    self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(resp_data))); self.end_headers(); self.wfile.write(resp_data)
                elif 'error' in rd:
                    raise Exception(rd['error'])
                else:
                    raise Exception("Unknown error from FastSD upscale")
        except Exception as e:
            logger.error(f"Image upscale failed: {e}", exc_info=True)
            error_msg = json.dumps({"error": f"Image upscale failed: {str(e)}"}).encode()
            try:
                if not getattr(self.wfile, 'closed', False):
                    self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(error_msg))); self.end_headers(); self.wfile.write(error_msg)
            except: pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def handle_exit(sig, frame):
    from core import cleanup_llm
    logger.info(f"Signal {sig} received. Cleaning up...")
    stop_fastsd()
    cleanup_llm()
    # On Windows, os._exit(0) is the most reliable way to kill sub-threads
    os._exit(0)

if __name__ == "__main__":
    from core import force_cleanup_port
    force_cleanup_port(PORT)
    force_cleanup_port(FASTSD_PORT)
    
    # Handle normal exit and sudden breaks
    atexit.register(stop_fastsd)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, handle_exit)
    
    # FastSD started as background process
    start_fastsd(FASTSD_DIR, FASTSD_PORT)
    try:
        server = ThreadedHTTPServer(("", PORT), Handler)
        logger.info(f"Server ready at http://localhost:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Process interrupted. Shutting down...")
    finally:
        from core import cleanup_llm
        cleanup_llm()
        stop_fastsd()
