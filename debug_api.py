import urllib.request
import json

# Try to authenticate first (we need the session_token)
PASSWORD = "AAaa1111$"
SERVER_URL = "http://localhost:8000"

def get_session():
    login_body = json.dumps({"password": PASSWORD}).encode()
    req = urllib.request.Request(f"{SERVER_URL}/api/login", data=login_body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as res:
            cookie = res.info().get('Set-Cookie')
            if cookie:
                return cookie.split(';')[0]
    except Exception as e:
        print(f"Login failed: {e}")
    return None

session_token = get_session()
if not session_token:
    print("Could not get session token.")
    # Still continue to see what happens
    session_token = "invalid-token"

headers = {
    'Content-Type': 'application/json',
    'Cookie': session_token
}

req_body = {
    "prompt": "a dog",
    "width": 512,
    "height": 512,
    "batch_size": 1
}

print(f"Testing /generate_image with {session_token}...")
req = urllib.request.Request(f"{SERVER_URL}/generate_image", data=json.dumps(req_body).encode(), headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print("Status:", r.status)
        print("Body:", r.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Body:", e.read().decode())
except Exception as e:
    print("Exception:", e)
