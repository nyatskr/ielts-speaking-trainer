"""
Kokoro TTS server for IELTS Speaking Builder.

Runs a local HTTP server on port 8880 that:
  1. Accepts a script (list of turns with voice + text)
  2. Generates audio for each turn using Kokoro
  3. Concatenates into a single WAV per topic
  4. Returns the audio + per-turn timestamps

API:
  POST /generate
    Body: {
      "turns": [
        {"voice": "bm_george", "text": "Good morning. Can you tell me your full name?"},
        {"voice": "bf_emma", "text": "My name is Emma."},
        ...
      ],
      "pause": 0.4
    }
    Response: {
      "audio": "<base64 WAV>",
      "duration": 12.34,
      "timestamps": [[0.00, 3.20], [3.60, 5.80], ...]
    }

  GET /voices
    Response: {"voices": ["bm_george", "bm_fable", "bf_emma", ...]}

Usage:
  C:/Users/nyats/.workbuddy-ai/binaries/python/envs/kokoro/Scripts/python.exe server/kokoro_server.py
"""

import json
import io
import base64
import threading
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8880

_pipeline = None
_pipeline_lock = threading.Lock()

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                print("[kokoro] Loading pipeline (lang_code='b')...")
                from kokoro import KPipeline
                _pipeline = KPipeline(lang_code="b")
                print("[kokoro] Pipeline ready.")
    return _pipeline

def generate_turn(voice, text, speed=1.0):
    """Generate audio for a single turn. Returns (audio_np, duration_sec)."""
    import numpy as np
    pipeline = get_pipeline()
    chunks = []
    for gs, ps, audio in pipeline(text, voice=voice, speed=speed):
        chunks.append(audio)
    if not chunks:
        return np.zeros(0, dtype=np.float32), 0.0
    full = np.concatenate(chunks)
    return full, len(full) / 24000.0

def generate_dialogue(turns, pause_sec=0.4, speed=1.0):
    """Generate a full dialogue. Returns (audio_np, timestamps)."""
    import numpy as np
    all_audio = []
    timestamps = []
    cursor = 0.0
    pause_samples = int(pause_sec * 24000)

    for turn in turns:
        voice = turn.get("voice", "bf_emma")
        text = turn.get("text", "")
        if not text.strip():
            continue

        audio, dur = generate_turn(voice, text, speed)
        if len(audio) == 0:
            continue

        start = cursor
        all_audio.append(audio)
        cursor += dur
        timestamps.append([round(start, 3), round(cursor, 3)])

        if pause_samples > 0:
            all_audio.append(np.zeros(pause_samples, dtype=np.float32))
            cursor += pause_samples

    if not all_audio:
        return np.zeros(0, dtype=np.float32), []

    final = np.concatenate(all_audio)
    return final, timestamps

def wav_to_base64(audio_np, sr=24000):
    """Convert numpy audio to base64-encoded WAV string."""
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, audio_np, sr, format="WAV", subtype="FLOAT")
    return base64.b64encode(buf.getvalue()).decode("ascii")

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/voices":
            voices = [
                "bf_emma", "bf_isabella", "bf_lily", "bf_alice",
                "bm_george", "bm_fable", "bm_daniel", "bm_lewis"
            ]
            self._send_json(200, {"voices": voices})
        elif self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self.send_response(404)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        if self.path != "/generate":
            self.send_response(404)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        turns = data.get("turns", [])
        pause = data.get("pause", 0.4)
        speed = data.get("speed", 1.0)

        if not turns:
            self._send_json(400, {"error": "No turns provided"})
            return

        print(f"[generate] {len(turns)} turns, pause={pause}s, speed={speed}")

        try:
            audio_np, timestamps = generate_dialogue(turns, pause, speed)
            if len(audio_np) == 0:
                self._send_json(500, {"error": "No audio generated"})
                return

            duration = len(audio_np) / 24000.0
            audio_b64 = wav_to_base64(audio_np)

            response = {
                "audio": audio_b64,
                "duration": round(duration, 3),
                "timestamps": timestamps,
                "sample_rate": 24000
            }
            self._send_json(200, response)
            print(f"[generate] Done: {duration:.2f}s, {len(timestamps)} timestamps")
        except Exception as e:
            print(f"[generate] ERROR: {e}")
            self._send_json(500, {"error": str(e)})

    def log_message(self, format, *args):
        print(f"[http] {args[0]}")

def main():
    try:
        import torch
        cuda = torch.cuda.is_available()
        print(f"[torch] CUDA available: {cuda}")
        if cuda:
            print(f"[torch] GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("[torch] not found, will use CPU")

    print(f"[server] Starting on http://localhost:{PORT}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[server] Ready. Open builder.html and point it to http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()
