import json
import threading
import urllib.request

BASE = "http://127.0.0.1:5000"
results = []


def hit():
    with urllib.request.urlopen(f"{BASE}/cars") as r:
        results.append(r.status)


threads = [threading.Thread(target=hit) for _ in range(20)]
[t.start() for t in threads]
[t.join() for t in threads]
print("status codes:", sorted(set(results)), "| requests:", len(results))
with urllib.request.urlopen(f"{BASE}/health") as r:
    print(json.dumps(json.load(r), indent=2))
