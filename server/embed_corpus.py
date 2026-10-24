#!/usr/bin/env python3
"""
Embed the compressed reading corpus into reading.html as a base64 string.
This makes the corpus loadable over file:// protocol (where fetch is blocked by CORS).

Usage: python embed_corpus.py
"""
import base64
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CORPUS_PATH = os.path.join(ROOT, "reading-corpus.json")
HTML_PATH = os.path.join(ROOT, "reading.html")

MARKER_START = "/*__CORPUS_B64_START__*/"
MARKER_END = "/*__CORPUS_B64_END__*/"


def main():
    with open(CORPUS_PATH, "rb") as f:
        raw = f.read()

    data = json.loads(raw)
    mini = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    gz = gzip.compress(mini, 9)
    b64 = base64.b64encode(gz).decode("ascii")

    print(f"Corpus:  {len(data['passages'])} passages")
    print(f"Raw:     {len(raw):,} bytes")
    print(f"Minify:  {len(mini):,} bytes")
    print(f"Gzip:    {len(gz):,} bytes")
    print(f"Base64:  {len(b64):,} bytes ({len(b64)/1024:.1f} KB)")

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    payload = f'{MARKER_START}\nvar CORPUS_B64 = "{b64}";\n{MARKER_END}'

    if MARKER_START in html and MARKER_END in html:
        # Replace existing block
        pattern = re.compile(
            re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
            re.DOTALL,
        )
        html = pattern.sub(lambda m: payload, html, count=1)
        action = "Replaced"
    else:
        # Insert right before the "/* --- Corpus Data --- */" marker
        anchor = "/* --- Corpus Data --- */"
        if anchor not in html:
            raise SystemExit("ERROR: anchor marker not found in reading.html")
        html = html.replace(anchor, payload + "\n\n" + anchor, 1)
        action = "Inserted"

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{action} corpus into reading.html")
    print(f"reading.html size: {os.path.getsize(HTML_PATH):,} bytes")


if __name__ == "__main__":
    main()
