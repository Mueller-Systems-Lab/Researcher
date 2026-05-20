"""
Thinking-Proxy: Filtert <think>-Tags aus Ollama-Responses.
Macht Qwen3.5 kompatibel mit GPT Researcher (OpenAI-API-Format).

Start:  python scripts/thinking_proxy.py
Port:   11435 (Proxy) → 11434 (Ollama)
"""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

OLLAMA_URL = "http://localhost:11434"


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        target_url = f"{OLLAMA_URL}{self.path}"

        resp = requests.post(
            target_url,
            data=body,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
        data = resp.json()

        # Filter: <think>-Tags aus content entfernen
        if "choices" in data:
            for c in data["choices"]:
                msg = c.get("message", {})
                # Ollama v1 API: content leer → reasoning hat die Antwort
                raw = msg.get("content", "") or msg.get("reasoning", "") or ""
                cleaned = re.sub(
                    r"<think>.*?</think>", "", raw, flags=re.DOTALL
                ).strip()
                msg["content"] = cleaned
                msg.pop("reasoning", None)
                msg.pop("reasoning_content", None)
        elif "message" in data:
            msg = data["message"]
            raw = msg.get("content", "") or msg.get("reasoning", "") or ""
            cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            msg["content"] = cleaned
            msg.pop("thinking", None)
            msg.pop("reasoning", None)

        self.send_response(resp.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        resp = requests.get(f"{OLLAMA_URL}{self.path}", timeout=10)
        self.send_response(resp.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp.content)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11435
    print(f"🧹 Thinking-Proxy: :{port} → Ollama :11434")
    print("   Filtert &lt;think&gt;-Tags aus allen Responses")
    HTTPServer(("127.0.0.1", port), ProxyHandler).serve_forever()
