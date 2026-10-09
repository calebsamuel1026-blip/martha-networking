"""Send one day's approved emails in small chunks, safely on a flaky connection.

Plan the order first (sends nothing):
    python tools/run_send_day.py <folder> --order [--chunk 8]
  Reorders the drafts in <folder> so every chunk passes gate.run on its own (no phrase repeated in too many
  emails of one chunk, at most 5 per firm per chunk, same-firm emails spread out) and writes <folder>/order.txt
  with a "# chunk N" line before each chunk. Drafts that fail the gate on their own are listed and left out.

Then send (only after the user's explicit "send"):
    python tools/run_send_day.py <folder> --list order.txt [--chunk 8] [--delay 120] [--cap N]
  For each chunk: copy the drafts into data/approved/, run send_approved.py --send --delay N (retrying only
  while smtp.gmail.com is unreachable, never re-sending anything already in data/sent/), then run
  check_replies.py (timeout 180 s) to catch bounces. Stops the whole run on the first bounce, on any BLOCKED
  guard, or when the daily cap is reached. Refuses to start if data/approved/ is not empty.

<folder> is relative to the current folder, the repo, data/ or data/drafts/. The list file is read as given or
from inside <folder>. In the list, blank lines and "#" lines split chunks; a chunk longer than --chunk is split.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import config as C

PY = sys.executable
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
TOOLS = Path(__file__).resolve().parent


def online():
    try:
        socket.create_connection(("smtp.gmail.com", 465), timeout=10).close()
        return True
    except OSError:
        return False


def bounced(names):
    names = set(names)
    return [o["file"] for o in C.jsonl(C.OUTCOMES) if o.get("outcome") == "bounce" and o.get("file") in names]


def resolve(arg):
    p = Path(arg)
    for c in ([p] if p.is_absolute() else [Path.cwd() / p, C.ROOT / p, C.DATA / p, C.DRAFTS / p]):
        if c.exists():
            return c
    sys.exit(f"Not found: {arg} (looked in the current folder, the repo, data/ and data/drafts/)")


def read_list(path, chunk):
    """File names from the list, in chunks. Blank and '#' lines are chunk boundaries. Strips \\r and BOMs."""
    groups, cur = [], []
    for raw in path.read_text(encoding="utf-8-sig").split("\n"):
        line = raw.replace("\r", "").replace("﻿", "").strip()
        if not line or line.startswith("#"):
            if cur:
                groups.append(cur)
                cur = []
            continue
        cur.append(line)
    if cur:
        groups.append(cur)
    return [g[i:i + chunk] for g in groups for i in range(0, len(g), chunk)]


# ---------- --order ----------

def plan_order(folder, chunk):
    import gate
    names = sorted(p.name for p in folder.glob("*.json") if not p.name.startswith("_"))
    drafts = {n: json.loads((folder / n).read_text(encoding="utf-8")) for n in names}
    already = [n for n in names if (C.SENT / n).exists()]
    bad = {n: gate.check(drafts[n], n) for n in names if n not in already}
    bad = {n: e for n, e in bad.items() if e}
    pool = [n for n in names if n not in already and n not in bad]
    firm = {n: (drafts[n].get("firm") or drafts[n].get("to", "").rsplit("@", 1)[-1]).lower() for n in pool}
    chunks = []
    while pool:
        cur = []
        while len(cur) < chunk:
            in_chunk = Counter(firm[n] for n in cur)
            # same-firm emails go in different chunks when possible, so no firm sees a burst
            cands = sorted((n for n in pool if n not in cur), key=lambda n: (in_chunk[firm[n]], pool.index(n)))
            pick = next((n for n in cands if in_chunk[firm[n]] < 5
                         and not gate.cross_checks([(x, drafts[x]) for x in cur + [n]])), None)
            if pick is None:
                break
            cur.append(pick)
        for n in cur:
            pool.remove(n)
        chunks.append(cur)
    # Confirm each chunk exactly the way send_approved.py will see it: alone in a folder, through gate.run.
    with tempfile.TemporaryDirectory() as tmp:
        for i, part in enumerate(chunks, 1):
            d = Path(tmp) / f"c{i}"
            d.mkdir()
            for n in part:
                shutil.copy2(folder / n, d / n)
            _, failed = gate.run(d)
            if failed:
                sys.exit(f"chunk {i} still fails the gate: {failed}. Nothing written.")
    # Chunking keeps a repeated sentence out of any single send, but a sentence (other than a house line) that two
    # people could compare is still worth a rewrite, most of all inside one firm.
    house = gate.house_grams({drafts[n].get("firm") or "" for n in names})
    seen = {}
    for n in names:
        if n in already or n in bad:
            continue
        for s in gate.SENTENCE.findall(gate.body_without_signoff(drafts[n].get("body", ""))):
            k = gate.norm(s)
            w = k.split()
            if len(w) >= 8 and not all(" ".join(w[i:i + 4]) in house for i in range(len(w) - 3)):
                seen.setdefault(k, []).append(n)
    reused = [(k, ns) for k, ns in seen.items() if len(ns) > 1]
    out = folder / "order.txt"
    lines = []
    for i, part in enumerate(chunks, 1):
        lines.append(f"# chunk {i}")
        lines += part
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for n in already:
        print(f"SKIP {n}: already in data/sent/")
    for n, errs in bad.items():
        print(f"FAIL {n} (left out): " + "; ".join(errs))
    for k, ns in reused:
        same = len({(drafts[n].get("firm") or "").lower() for n in ns}) < len(ns)
        print(f"WARN {', '.join(ns)} share a sentence{' (same firm!)' if same else ''}: \"{k[:70]}...\"")
    print(f"\n{sum(map(len, chunks))} drafts in {len(chunks)} chunk(s) of up to {chunk}, every chunk passes the gate. "
          f"Wrote {out}")
    return 0 if not bad else 1


# ---------- --list (send) ----------

def clear(files):
    for f in files:
        p = C.APPROVED / f
        if p.exists():
            p.unlink()


def send_day(folder, chunks, delay, cap):
    if any(C.APPROVED.glob("*.json")):
        sys.exit("data/approved/ is not empty; clear it first so nothing unreviewed goes out.")
    total = sum(map(len, chunks))
    missing = [f for part in chunks for f in part if not (folder / f).exists()]
    if missing:
        sys.exit(f"Not in {folder}: {', '.join(missing)}. Nothing was sent.")
    extra = ["--cap", str(cap)] if cap is not None else []
    sent_names = []
    for ci, files in enumerate(chunks, 1):
        part = [f for f in files if not (C.SENT / f).exists()]
        for f in part:
            shutil.copy2(folder / f, C.APPROVED / f)
        for attempt in range(10):
            left = [f for f in part if (C.APPROVED / f).exists()]
            if not left:
                break
            if not online():
                print(f"  offline, retrying in 30s (attempt {attempt + 1})", flush=True)
                time.sleep(30)
                continue
            r = subprocess.run([PY, str(TOOLS / "send_approved.py"), "--send", "--delay", str(delay)] + extra,
                               cwd=C.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=CHILD_ENV)
            tail = (r.stdout + r.stderr).strip().splitlines()
            shown = [l for l in tail if l.startswith(("Sent to", "BLOCKED", "Done", "Nothing", "Daily cap", "Sending",
                                                      "Bounce rate", "Network error"))]
            if shown:
                print("  " + "\n  ".join(shown), flush=True)
            if any(l.startswith("BLOCKED") for l in tail):
                clear(part)
                sys.exit("Blocked by a guard; stopping. Fix the draft and re-run.")
            if any(l.startswith("Daily cap reached") for l in tail):
                clear(part)
                sent_names += [f for f in part if (C.SENT / f).exists()]
                sys.exit(f"STOPPED: daily cap reached. {len(sent_names)} sent this run; the rest wait for tomorrow.")
            if r.returncode != 0 and not any(l.startswith("Sent to") for l in tail):
                time.sleep(30)  # a transient SMTP error: wait, then retry what is left
        if any((C.APPROVED / f).exists() for f in part):
            clear(part)
            sys.exit(f"STOPPED: chunk {ci} could not be sent after 10 attempts. "
                     f"{len(sent_names) + sum((C.SENT / f).exists() for f in part)} sent this run.")
        sent_names += [f for f in part if (C.SENT / f).exists()]
        print(f"chunk {ci}/{len(chunks)}: {len(sent_names)} sent so far; checking bounces", flush=True)
        checker = TOOLS / "check_replies.py"
        if not checker.exists():
            print("  check_replies.py not found; bounce check skipped", flush=True)
        elif online():
            try:  # an IMAP call can hang on a dropped connection: never let it stall the send day
                subprocess.run([PY, str(checker)], cwd=C.ROOT, capture_output=True, text=True, timeout=180,
                               encoding="utf-8", errors="replace", env=CHILD_ENV)
            except subprocess.TimeoutExpired:
                print("  bounce check timed out; continuing (re-run python tools/check_replies.py later)", flush=True)
        hits = bounced(sent_names)
        if hits:
            clear([f for part2 in chunks for f in part2])
            sys.exit(f"STOPPED: bounce on {hits}. {len(sent_names)} sent this run.")
    print(f"DONE: {len(sent_names)} of {total} sent; no bounces seen yet.")


def main():
    sys.stdout.reconfigure(errors="replace")  # never crash printing a name the console can't show
    ap = argparse.ArgumentParser(description="Plan (--order) or send (--list) one day's emails in gate-clean chunks.")
    ap.add_argument("folder", help="drafts folder, e.g. drafts/batch-1")
    ap.add_argument("files", nargs="*", help="file names to send (alternative to --list)")
    ap.add_argument("--order", action="store_true", help="plan chunks that each pass the gate; writes <folder>/order.txt")
    ap.add_argument("--list", dest="list_file", help="text file with one draft file name per line (e.g. order.txt)")
    ap.add_argument("--chunk", type=int, default=8, help="emails per chunk (default 8)")
    ap.add_argument("--delay", type=int, default=120, help="seconds between emails inside a chunk (default 120)")
    ap.add_argument("--cap", type=int, default=None, help="passed to send_approved.py --cap")
    a = ap.parse_args()
    folder = resolve(a.folder)
    if not folder.is_dir():
        sys.exit(f"{folder} is not a folder.")
    if a.order:
        sys.exit(plan_order(folder, a.chunk))
    if a.list_file:
        lp = Path(a.list_file)
        lp = lp if lp.exists() else folder / a.list_file
        if not lp.exists():
            sys.exit(f"List file not found: {a.list_file}")
        chunks = read_list(lp, a.chunk)
    else:
        files = [f.replace("\r", "").strip() for f in a.files if f.strip()]
        chunks = [files[i:i + a.chunk] for i in range(0, len(files), a.chunk)]
    if not chunks:
        sys.exit("No files to send. Use --order to plan, then --list order.txt.")
    send_day(folder, chunks, a.delay, a.cap)


if __name__ == "__main__":
    main()
