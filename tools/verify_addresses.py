"""Re-check every first-email address against the live web before it can be sent.

For each draft JSON in the given folders (files starting with "_" are skipped, and so are drafts that are not
first emails):
  1. Fetch the page in email_source_url and confirm the exact address is printed there today: plain HTML,
     mailto links, simple obfuscation like "name [at] firm.com", Cloudflare-protected addresses (data-cfemail and
     /cdn-cgi/l/email-protection#hex), ROT13-scrambled addresses, and PDFs (needs pymupdf).
  2. Fetch the person's bio page (bio_url, call_prep.bio_url, or practice when it is a URL) and confirm it still
     loads and still names them, so nobody gets an email after leaving the firm.
Writes the result into the draft as address_check {status, detail, checked_at}.
send_approved.py refuses a first email unless address_check.status is "verified" and checked within 3 days.

Statuses: verified, no-source, source-down, not-printed, bio-down, bio-missing-name.

    python tools/verify_addresses.py data/research/batch-1 drafts/batch-1 [--dry]
Folders are relative to the current folder, the repo, data/ or data/drafts/ (single JSON files work too).
--dry prints the results without writing address_check.
"""
import argparse
import codecs
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import config as C

try:
    import requests
except ImportError:  # requirements.txt has it; fall back to the standard library so a check still runs
    requests = None
    import urllib.error
    import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_cache = {}


def first_url(s):
    m = re.search(r"https?://[^\s)\"'>]+", s or "")
    return m.group(0).rstrip(".,;") if m else None


def _get(url):
    """Returns (status_code, content_type, raw bytes, text) or raises OSError-like errors."""
    if requests is not None:
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True)
        return r.status_code, r.headers.get("content-type", ""), r.content, r.text
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read()
            ctype = r.headers.get("content-type", "")
            return r.status, ctype, raw, raw.decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, "", b"", ""


def pdf_text(raw):
    try:
        import fitz  # pymupdf
    except ImportError:
        return None, "PDF source, but pymupdf is not installed (pip install pymupdf)"
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        return "\n".join(p.get_text() for p in doc), None
    except Exception as e:
        return None, f"pdf unreadable ({type(e).__name__})"


def fetch_text(url):
    """(text, info). text is None when the page can't be read; info says why."""
    if url in _cache:
        return _cache[url]
    try:
        code, ctype, raw, page = _get(url)
    except Exception as e:  # network errors of any library
        _cache[url] = (None, f"unreachable ({type(e).__name__})")
        return _cache[url]
    if code >= 400:
        _cache[url] = (None, f"HTTP {code}")
        return _cache[url]
    if "pdf" in ctype.lower() or url.lower().split("?")[0].endswith(".pdf"):
        text, err = pdf_text(raw)
        if text is None:
            _cache[url] = (None, err)
            return _cache[url]
    else:
        text = html.unescape(page)
        # Cloudflare email protection hides each address as hex, XOR-ed with the first byte.
        hexes = re.findall(r'data-cfemail="([0-9a-fA-F]+)"', page) + re.findall(r"email-protection#([0-9a-fA-F]+)", page)
        text += "\n" + "\n".join(cf_decode(h) for h in hexes)
        # Percent-encoded mailto links (name%40firm.com).
        text += "\n" + "\n".join(unquote(m) for m in re.findall(r"mailto:([^\"'>\s?]+)", page, re.I))
        # Some sites scramble addresses with ROT13: decode every email-shaped token.
        text += "\n" + "\n".join(codecs.decode(m, "rot13") for m in EMAIL.findall(page))
    _cache[url] = (text, f"HTTP {code}")
    return _cache[url]


def cf_decode(h):
    try:
        key = int(h[:2], 16)
        return "".join(chr(int(h[i:i + 2], 16) ^ key) for i in range(2, len(h) - 1, 2))
    except ValueError:
        return ""


def normalize(text):
    t = text.lower()
    t = re.sub(r"\s*(\[at\]|\(at\)|\{at\}|\s+at\s+)\s*", "@", t)
    t = re.sub(r"\s*(\[dot\]|\(dot\)|\{dot\}|\s+dot\s+)\s*", ".", t)
    return t


def check(d):
    """Returns (status, detail) for one draft."""
    to = (d.get("to") or d.get("email") or "").strip().lower()
    src = first_url(d.get("email_source_url") or (d.get("research") or {}).get("email_source_url"))
    if not src:
        return "no-source", "email_source_url has no link"
    text, info = fetch_text(src)
    if text is None:
        return "source-down", f"{src}: {info}"
    if to not in normalize(text):
        return "not-printed", f"{to} not found on {src} ({info})"
    name = (d.get("name") or "").split()
    last = name[-1].lower() if name else ""
    bio = first_url(d.get("bio_url") or (d.get("call_prep") or {}).get("bio_url") or d.get("practice"))
    if bio and bio != src:
        btext, binfo = fetch_text(bio)
        if btext is None:
            return "bio-down", f"address printed on {src}, but bio {bio} gives {binfo}: may have left the firm"
        if last and last not in btext.lower():
            return "bio-missing-name", f"bio {bio} loads but no longer names {d.get('name')}"
    return "verified", f"printed on {src}" + (f"; bio live {bio}" if bio and bio != src else "")


def resolve(arg):
    p = Path(arg)
    for c in ([p] if p.is_absolute() else [Path.cwd() / p, C.ROOT / p, C.DATA / p, C.DRAFTS / p]):
        if c.exists():
            return c
    sys.exit(f"Not found: {arg} (looked in the current folder, the repo, data/ and data/drafts/)")


def main():
    sys.stdout.reconfigure(errors="replace")  # never crash printing a name the console can't show
    ap = argparse.ArgumentParser(description="Re-fetch each first email's source page and confirm the exact address "
                                             "is still printed there (and the bio still names the person). Writes "
                                             "address_check into each draft.")
    ap.add_argument("folders", nargs="+", help="folders (or single JSON files) of drafts/research records")
    ap.add_argument("--dry", action="store_true", help="print results only, don't write address_check")
    a = ap.parse_args()
    counts = {}
    for folder in a.folders:
        target = resolve(folder)
        files = [target] if target.is_file() else sorted(target.glob("*.json"))
        for p in files:
            if p.name.startswith("_"):
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            if (d.get("kind") or "first") != "first" or not (d.get("to") or d.get("email")):
                continue
            status, detail = check(d)
            counts[status] = counts.get(status, 0) + 1
            print(f"{status:16} {p.parent.name}/{p.name:40} {detail}")
            if not a.dry:
                d["address_check"] = {"status": status, "detail": detail, "checked_at": time.strftime("%Y-%m-%d %H:%M")}
                p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + (", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "no first-email drafts found"))


if __name__ == "__main__":
    main()
