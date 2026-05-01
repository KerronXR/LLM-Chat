import http.server, socketserver, os, json, base64, time, secrets, urllib.request, logging
from core import load_local_model, logger, MODELS_MAPPING, MODELS_DIR, model_supports_vision
import atexit, signal

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(DIRECTORY, "images")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

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
        if self.path in ['/login.html', '/local_ai_icon.png', '/local_ai_icon.ico'] or self.path.startswith(('/js/', '/css/')): return super().do_GET()
        if not self.is_authenticated(): self.send_response(302); self.send_header('Location', '/login.html'); self.end_headers(); return
        if self.path == '/persona.txt' and os.path.exists(os.path.join(DIRECTORY, "persona.txt")):
            p = os.path.join(DIRECTORY, "persona.txt"); s = os.path.getsize(p)
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.send_header('Content-Length', str(s)); self.end_headers()
            with open(p, 'rb') as f: self.wfile.write(f.read())
        elif self.path == '/api/history':
            d = b'[]'
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'rb') as f: d = f.read()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(d))); self.end_headers(); self.wfile.write(d)
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
            elif self.path == '/api/history':
                with open(HISTORY_FILE, "wb") as f: f.write(raw)
                self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
            elif self.path == '/api/logout':
                t = self.headers.get('Cookie', '').split('session_token=')[-1].split(';')[0] if 'session_token=' in self.headers.get('Cookie', '') else None
                if t in sessions: del sessions[t]; save_sessions()
                self.send_response(200); self.send_header('Set-Cookie', 'session_token=; Max-Age=0; Path=/'); self.send_header('Content-Length', '0'); self.end_headers()
            elif self.path == '/save_persona':
                with open(os.path.join(DIRECTORY, "persona.txt"), "wb") as f: f.write(raw)
                self.send_response(200); self.send_header('Content-Length', '0'); self.end_headers()
            else: self.send_error(404)
        except Exception as e: logger.error(f"POST {self.path} Error: {e}", exc_info=True); self.send_error(500, str(e)) if not getattr(self.wfile, 'closed', False) else None

    def handle_chat(self, raw):
        data = json.loads(raw); mid = data.get('model', 'gemma-4-e4b-it-heretic:latest'); llm = load_local_model(mid)
        self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson'); self.send_header('Transfer-Encoding', 'chunked'); self.end_headers()
        def chunk(obj):
            ds = json.dumps(obj) + "\n"; b = ds.encode()
            self.wfile.write(f"{len(b):X}\r\n".encode() + b + b"\r\n"); self.wfile.flush()
        msg = data.get('messages', [])
        attachment = data.get('attachment')
        vision_requested = bool(attachment and attachment.get('type') == 'image')
        if attachment:
            if attachment['type'] == 'file':
                # Append context for text/doc files
                ctx_msg = f"\n\n[Attached File: {attachment['name']}]\n{attachment['content']}"
                if msg: msg[-1]['content'] += ctx_msg
            elif attachment['type'] == 'image':
                if not model_supports_vision(mid):
                    chunk({
                        "model": mid,
                        "message": {
                            "role": "assistant",
                            "content": "This model cannot analyze attached images. Switch to Gemma-4 E4B (Latest 2026) and try again."
                        },
                        "done": True,
                        "prompt_eval_count": 0,
                        "eval_count": 0,
                        "context_length": 8192
                    })
                    self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
                    return

                if msg:
                    prompt_text = msg[-1].get('content') or "Please describe this image."
                    mime_type = attachment.get('mimeType') or 'image/png'
                    data_url = f"data:{mime_type};base64,{attachment['data']}"
                    logger.info("Vision attachment received: mime=%s bytes=%s", mime_type, len(attachment.get('data', '')))
                    msg[-1]['content'] = [
                        {"type": "image", "image": data_url},
                        {"type": "text", "text": prompt_text}
                    ]
        
        prompt_for_count = json.dumps(msg).encode() if not vision_requested else json.dumps(data.get('messages', [])).encode()
        ec, pc = 0, len(llm.tokenize(prompt_for_count))
        try:
            for out in llm.create_chat_completion(messages=msg, stream=True, max_tokens=4096):
                delta = out["choices"][0]["delta"]
                if "content" in delta:
                    ec += 1; chunk({"model": mid, "message": {"role": "assistant", "content": delta["content"]}, "done": False})
            chunk({"model": mid, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": pc, "eval_count": ec, "context_length": 8192})
            self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
        except Exception as e:
            logger.error("Chat generation failed for %s: %s", mid, e, exc_info=True)
            try:
                chunk({"error": str(e), "done": True, "prompt_eval_count": pc, "eval_count": ec, "context_length": 8192})
                self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
            except Exception:
                pass



class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def handle_exit(sig, frame):
    from core import cleanup_llm
    logger.info(f"Signal {sig} received. Cleaning up...")
    cleanup_llm()
    # On Windows, os._exit(0) is the most reliable way to kill sub-threads
    os._exit(0)

if __name__ == "__main__":
    from core import force_cleanup_port
    force_cleanup_port(PORT)
    
    # Handle normal exit and sudden breaks
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, handle_exit)
    
    try:
        server = ThreadedHTTPServer(("", PORT), Handler)
        logger.info(f"Server ready at http://localhost:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Process interrupted. Shutting down...")
    finally:
        from core import cleanup_llm
        cleanup_llm()
