"""Shared paths and loaders. Every tool imports this instead of hard-coding paths.

me/    the user's private profile (gitignored): profile.md, strategy.md, lessons.md, availability.json, config.env, resume/
data/  the user's working data (gitignored): research/, drafts/, approved/, sent/, replies/, outcomes.jsonl
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ME = ROOT / "me"
DATA = ROOT / "data"
KNOWLEDGE = ROOT / "knowledge"
RESEARCH, DRAFTS, APPROVED, SENT, REPLIES = (DATA / d for d in ("research", "drafts", "approved", "sent", "replies"))
OUTCOMES = DATA / "outcomes.jsonl"
for _d in (RESEARCH, DRAFTS, APPROVED, SENT, REPLIES):
    _d.mkdir(parents=True, exist_ok=True)


def require_me():
    if not (ME / "profile.md").exists():
        sys.exit("No me/profile.md yet. Copy me.example/ to me/ and fill it in (or run /onboard in Claude Code).")


def load_profile():
    """me/profile.md starts with a front-matter block of `key: value` lines between --- markers.
    Lists are written as `key: a; b; c`. Everything after the block is free-text story the writer reads."""
    require_me()
    text = (ME / "profile.md").read_text(encoding="utf-8")
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, v = line.split(":", 1)
                v = v.strip()
                meta[k.strip()] = [x.strip() for x in v.split(";") if x.strip()] if ";" in v else v
    meta["_body"] = body
    return meta


def as_list(v):
    if not v:
        return []
    return v if isinstance(v, list) else [v]


def load_env():
    """me/config.env: KEY=value lines. The user types their own Gmail app password here; tools never print it."""
    env = {}
    p = ME / "config.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "DAILY_CAP")})
    return env


def load_availability():
    p = ME / "availability.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"window": [8, 17], "recurring": [], "one_off": []}


def load_strategy_cap(default=3):
    """Per-firm cap ("max people per firm: 3") from me/strategy.md, default 3."""
    p = ME / "strategy.md"
    if p.exists():
        m = re.search(r"max people per firm\s*:\s*(\d+)", p.read_text(encoding="utf-8"), re.I)
        if m:
            return int(m.group(1))
    return default


def jsonl(path):
    path = Path(path)
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def last_outcomes():
    """file name -> latest outcome (the last line for a file wins)."""
    out = {}
    for o in jsonl(OUTCOMES):
        out[o["file"]] = o
    return out
