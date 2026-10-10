"""Shared fixtures for the martha-networking test suite.

Every test runs offline against a throwaway me/ and data/ under tmp_path: config.ME, config.DATA and every derived
path are pointed there, the network is switched off, and SMTP raises if anything tries to open it. Nothing here
reads or writes the real me/ or data/ folders.
"""
import os
import smtplib
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent / "tools"
for p in (str(TOOLS), str(TESTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("MPLBACKEND", "Agg")

# config.py creates data/ subfolders inside the repo when it is first imported. The tests never use the real data/,
# so that one-time side effect is skipped here (every path is redirected to tmp_path below).
_real_mkdir = Path.mkdir
Path.mkdir = lambda self, *a, **k: None
try:
    import config  # noqa: E402
finally:
    Path.mkdir = _real_mkdir

import gate  # noqa: E402
import verify_addresses  # noqa: E402

PROFILE = """---
# Fictional test profile. Nobody real.
name: Alex Sample
first_name: Alex
school: Lakeshore State University
standing: sophomore
class_year: 2029
major: Accounting
interest_line: a strong interest in audit at <Firm>
never_say: family business (the bakery is not my family's); GPA (never mention grades)
resume: Alex-Sample-Resume.pdf
attach: resume
---

# Story

Alex Sample is a made-up accounting sophomore used only by the test suite.
"""
STRATEGY = "# My strategy\n\nmax people per firm: 3\n"
LESSONS = "# My lessons\n\n- 2026-10-01 BAN: circle back\n"
FAKE_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def reset_rules():
    """gate.py caches the profile and lessons rules; call after editing me/ inside a test."""
    gate._profile_cache.clear()
    gate._house_cache.clear()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No test may reach the network or open SMTP. Any attempt fails the test."""
    attempts = []

    def no_network(*args, **kwargs):
        attempts.append(args[1:] if args and isinstance(args[0], socket.socket) else args)
        raise OSError("network access is disabled in the test suite")

    def no_smtp(*args, **kwargs):
        raise AssertionError("SMTP must never be opened by the test suite")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(smtplib, "SMTP_SSL", no_smtp)
    monkeypatch.setattr(smtplib, "SMTP", no_smtp)
    yield attempts
    assert not attempts, f"a test tried to reach the network: {attempts}"


@pytest.fixture(autouse=True)
def ws(tmp_path, monkeypatch):
    """A fake me/ (profile, strategy, lessons, résumé PDF) and an empty data/ tree, wired into config."""
    me, data = tmp_path / "me", tmp_path / "data"
    (me / "resume").mkdir(parents=True)
    (me / "profile.md").write_text(PROFILE, encoding="utf-8")
    (me / "strategy.md").write_text(STRATEGY, encoding="utf-8")
    (me / "lessons.md").write_text(LESSONS, encoding="utf-8")
    (me / "resume" / "Alex-Sample-Resume.pdf").write_bytes(FAKE_PDF)
    paths = {name: data / name.lower() for name in ("RESEARCH", "DRAFTS", "APPROVED", "SENT", "REPLIES")}
    for p in paths.values():
        p.mkdir(parents=True)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "ME", me)
    monkeypatch.setattr(config, "DATA", data)
    for name, p in paths.items():
        monkeypatch.setattr(config, name, p)
    monkeypatch.setattr(config, "OUTCOMES", data / "outcomes.jsonl")
    for var in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "DAILY_CAP"):
        monkeypatch.delenv(var, raising=False)
    reset_rules()
    verify_addresses._cache.clear()
    yield SimpleNamespace(root=tmp_path, me=me, data=data, approved=paths["APPROVED"], sent=paths["SENT"],
                          drafts=paths["DRAFTS"], outcomes=data / "outcomes.jsonl", reset_rules=reset_rules)
    reset_rules()
    verify_addresses._cache.clear()
