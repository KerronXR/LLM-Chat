import http.server, socketserver, os, json, base64, time, secrets, urllib.request, logging, re, threading
from core import (
    load_local_model, logger, MODELS_MAPPING, MODELS_DIR,
    model_supports_vision, is_session_continuation, record_session_turn, reset_chat_session
)
import atexit, signal

PORT, HEARTBEAT_INTERVAL = 8000, 5.0
_model_lock, _abort_lock, _active_abort = threading.Lock(), threading.Lock(), None
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

def normalize_incoming_attachments(data):
    raw = data.get('attachments')
    if raw is None and data.get('attachment'):
        raw = [data['attachment']]
    if not raw or not isinstance(raw, list):
        return []
    images = [a for a in raw if isinstance(a, dict) and (a.get('type') == 'image' or a.get('kind') == 'image' or str(a.get('type', '')).startswith('image/'))]
    files = [a for a in raw if isinstance(a, dict) and a.get('type') == 'file']
    return images[:3] + files


def build_continuation_turn(model_id, user_text):
    mid = (model_id or "").lower()
    if "qwen" in mid or "deepseek" in mid:
        return f"<|im_start|>user\n{user_text}<|im_end|>\n<|im_start|>assistant\n", ["<|im_end|>", "<|endoftext|>"]
    if "llama-3" in mid or "llama3" in mid:
        return f"<|start_header_id|>user<|end_header_id|>\n\n{user_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n", ["<|eot_id|>", "<|end_of_text|>"]
    return f"<start_of_turn>user\n{user_text}<end_of_turn>\n<start_of_turn>model\n", ["<end_of_turn>", "<eos>"]

class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

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
                try:
                    if not json.loads(raw): reset_chat_session()
                except Exception: pass
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
        global _active_abort
        with _abort_lock:
            if _active_abort: _active_abort.set()
            my_abort = threading.Event()
            _active_abort = my_abort
        data = json.loads(raw); mid = data.get('model', 'gemma-4-e4b-it:latest'); llm = load_local_model(mid)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'close')
        self.send_header('X-Accel-Buffering', 'no')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        write_lock = threading.Lock()
        def chunk(obj):
            with write_lock:
                if getattr(self.wfile, 'closed', None) is True: return
                try:
                    self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode('utf-8'))
                    self.wfile.flush()
                except Exception: pass
        stop_hb = threading.Event()
        def _hb():
            while not stop_hb.wait(HEARTBEAT_INTERVAL):
                with write_lock:
                    if getattr(self.wfile, 'closed', None) is True: break
                    try:
                        self.wfile.write(b": ping\n\n"); self.wfile.flush()
                    except Exception: break
        threading.Thread(target=_hb, daemon=True).start()
        msg = data.get('messages', [])
        attachments = normalize_incoming_attachments(data)
        has_history_images = any(
            isinstance(m.get('content'), list) and any(
                isinstance(item, dict) and item.get('type') in ('image', 'image_url')
                for item in m['content']
            )
            for m in msg if isinstance(m, dict)
        )
        vision_requested = any(a.get('type') == 'image' for a in attachments) or has_history_images
        if vision_requested and not model_supports_vision(mid):
            chunk({"model": mid, "message": {"role": "assistant", "content": "This model cannot analyze attached images. Switch to Gemma-4 E4B (Latest 2026) and try again."}, "done": True, "prompt_eval_count": 0, "eval_count": 0, "context_length": 8192})
            return

        for att in attachments:
            if att.get('type') == 'file' and msg:
                ctx_msg = f"\n\n[Attached File: {att.get('name')}]\n{att.get('content')}"
                if isinstance(msg[-1].get('content'), list):
                    msg[-1]['content'].append({"type": "text", "text": ctx_msg})
                else:
                    msg[-1]['content'] = f"{msg[-1].get('content', '')}{ctx_msg}"

        img_attachments = [a for a in attachments if a.get('type') == 'image']
        if img_attachments and msg:
            curr_content = msg[-1].get('content')
            prompt_text = "Please describe the attached images."
            if isinstance(curr_content, list):
                for item in curr_content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        prompt_text = item.get('text', '')
                        break
            elif isinstance(curr_content, str) and curr_content:
                prompt_text = curr_content
                if re.search(r"\b(price|cost|how\s+much|buy|where|what\s+is)\b", curr_content, re.I):
                    prompt_text = f"Identify the specific product or item shown, then answer: {curr_content}"
            content_items = []
            for img_att in img_attachments:
                mime_type = img_att.get('mimeType') or 'image/png'
                data_url = img_att.get('dataUrl') or f"data:{mime_type};base64,{img_att.get('data', '')}"
                content_items.append({"type": "image_url", "image_url": {"url": data_url}, "image": data_url})
            content_items.append({"type": "text", "text": prompt_text})
            msg[-1]['content'] = content_items

        web_search_mode = data.get('web_search', 'auto')
        if not attachments and msg:
            from web_search import (
                should_trigger_search_from_history,
                resolve_contextual_query,
                safe_duckduckgo_search,
                format_search_prompt_context,
            )
            if should_trigger_search_from_history(msg, mode=web_search_mode):
                search_query = resolve_contextual_query(msg)
                chunk({"status": "searching", "query": search_query[:50], "done": False})
                s_results = safe_duckduckgo_search(search_query)
                if s_results:
                    chunk({"status": "sources", "count": len(s_results), "sources": [{"title": r["title"], "url": r["url"]} for r in s_results], "done": False})
                    s_ctx = format_search_prompt_context(s_results)
                    if isinstance(msg[-1].get('content'), list):
                        msg[-1]['content'].append({"type": "text", "text": f"\n\n{s_ctx}"})
                    else:
                        msg[-1]['content'] = f"{msg[-1].get('content', '')}\n\n{s_ctx}"
        
        def extract_text_for_count(messages_list):
            return " ".join(
                m.get('content', '') if isinstance(m.get('content'), str)
                else " ".join(i.get('text', '') for i in m.get('content', []) if isinstance(i, dict) and i.get('type') == 'text')
                for m in messages_list if isinstance(m, dict)
            )

        prompt_for_count = extract_text_for_count(msg).encode()
        ec, pc = 0, len(llm.tokenize(prompt_for_count))
        def _persist_turn(reply):
            if not reply: return
            record_session_turn(msg, reply, getattr(llm, 'n_tokens', 0), mid)
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(list(msg) + [{"role": "assistant", "content": reply}], f, ensure_ascii=False)
            except Exception: pass

        try:
            with _model_lock:
                if my_abort.is_set(): return
                gen_start, assistant_reply = None, []
                if not attachments and is_session_continuation(msg, mid):
                    logger.info("Fast follow-up turn: reusing active KV cache without image re-encode")
                    user_text = msg[-1].get('content', '')
                    if isinstance(user_text, list):
                        user_text = " ".join(item.get('text', '') for item in user_text if isinstance(item, dict) and item.get('type') == 'text')
                    turn_prompt, stop_tokens = build_continuation_turn(mid, user_text)
                    new_tokens = llm.tokenize(turn_prompt.encode('utf-8'), add_bos=False)
                    llm.eval(new_tokens); pc = len(new_tokens)
                    prompt_ids = llm.input_ids[:llm.n_tokens].tolist()
                    max_gen = min(2048, max(1, 4096 - llm.n_tokens - 1))
                    for out in llm.create_completion(prompt=prompt_ids, stream=True, max_tokens=max_gen, stop=stop_tokens):
                        if my_abort.is_set(): break
                        tok = out["choices"][0].get("text", "")
                        if tok:
                            if any(s in tok for s in stop_tokens):
                                clean = tok
                                for s in stop_tokens: clean = clean.split(s)[0]
                                if clean:
                                    ec += 1; assistant_reply.append(clean); elapsed = time.perf_counter() - gen_start if gen_start else 0.001
                                    chunk({"model": mid, "message": {"role": "assistant", "content": clean}, "done": False, "tps": round(ec/elapsed, 2)})
                                break
                            if gen_start is None: gen_start = time.perf_counter()
                            ec += 1; assistant_reply.append(tok); elapsed = time.perf_counter() - gen_start
                            chunk({"model": mid, "message": {"role": "assistant", "content": tok}, "done": False, "tps": round(ec/elapsed, 2) if elapsed > 0 else 0})
                else:
                    for out in llm.create_chat_completion(messages=msg, stream=True, max_tokens=2048):
                        if my_abort.is_set(): break
                        delta = out["choices"][0]["delta"]
                        if "content" in delta:
                            if gen_start is None: gen_start = time.perf_counter()
                            ec += 1; assistant_reply.append(delta["content"]); elapsed = time.perf_counter() - gen_start
                            chunk({"model": mid, "message": {"role": "assistant", "content": delta["content"]}, "done": False, "tps": round(ec/elapsed, 2) if elapsed > 0 else 0})
                full_reply = "".join(assistant_reply)
                _persist_turn(full_reply)
                gen_elapsed = time.perf_counter() - gen_start if gen_start else 0
                avg_tps = round(ec / gen_elapsed, 2) if gen_elapsed > 0 else 0
                chunk({"model": mid, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": pc, "eval_count": ec, "context_length": 8192, "avg_tps": avg_tps})
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            logger.info("Client disconnected/locked during generation: %s", e)
            _persist_turn("".join(assistant_reply))
        except Exception as e:
            logger.error("Chat generation failed for %s: %s", mid, e, exc_info=True)
            reset_chat_session()
            try: chunk({"error": str(e), "done": True, "prompt_eval_count": pc, "eval_count": ec, "context_length": 8192})
            except Exception: pass
        finally:
            stop_hb.set()
            with _abort_lock:
                if _active_abort is my_abort: _active_abort = None
            self.close_connection = True

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def handle_exit(sig, frame):
    from core import cleanup_llm
    logger.info(f"Signal {sig} received. Cleaning up...")
    cleanup_llm(); os._exit(0)

if __name__ == "__main__":
    from core import force_cleanup_port
    force_cleanup_port(PORT)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    if hasattr(signal, 'SIGBREAK'): signal.signal(signal.SIGBREAK, handle_exit)
    try:
        server = ThreadedHTTPServer(("", PORT), Handler)
        logger.info(f"Server ready at http://localhost:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Process interrupted. Shutting down...")
    finally:
        from core import cleanup_llm
        cleanup_llm()
