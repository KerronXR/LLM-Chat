import urllib.request
import json

req_body = {
    "prompt": "a dog",
    "width": 256,
    "height": 256,
    "batch_size": 1
}

print("Testing 256x256 through UI backend...")
req = urllib.request.Request("http://localhost:8000/generate_image", data=json.dumps(req_body).encode(), headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print("Success:", r.status, r.read().decode()[:100])
except Exception as e:
    print("Exception:", e)
