"""Label what happened after an email, and list the latest outcome of every thread.

    python tools/outcomes.py label <sent-file> <outcome> "note"
    python tools/outcomes.py list                 every first email and its latest outcome
    python tools/outcomes.py list --only call     just one outcome

<sent-file> is a file name from data/sent/ (with or without .json), or any unique part of one, or of the
person's name ("reyes"). Labels attach to the thread's FIRST email, so labeling a follow-up or a reply file
labels its whole thread. Each label is one line appended to data/outcomes.jsonl; the last line for a file
wins, so labeling again corrects a mistake.

Outcomes:
  call      they offered or agreed to a call
  referral  they handed you to someone else (recruiting, a colleague, "send your resume in December")
  replied   a warm human reply, no call yet
  declined  a human said no (no interns, too busy): a targeting signal, not a copy signal
  ooo       out-of-office auto-reply: never reached a human
  negative  annoyed, or asked not to be contacted
  bounce    the address does not exist (check_replies.py logs these itself)
A first email with no outcome after 4 days counts as no reply (every real reply so far came within 43 hours).

The helpers here (load_sent, threads, read_outcomes...) are shared by check_replies, digest and results.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

LABELS = ("call", "referral", "replied", "declined", "ooo", "negative", "bounce")
POSITIVE = {"replied", "call", "referral"}
HUMAN = POSITIVE | {"declined", "negative"}       # a person read it and answered
UNREACHED = {"bounce", "ooo"}                      # left out of every rate
RESPONSE_KINDS = {"reply", "thankyou", "scheduling"}  # answers to people who wrote back (not cold volume)
NO_REPLY_DAYS = 4


def safe_stdout():
    """Names with accents must never crash a print on a Windows console or a pipe."""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(errors="replace")


def parse_when(s):
    """sent_at, outcome dates and email Date values -> naive local datetime (None when unreadable)."""
    if not s:
        return None
    if isinstance(s, dt.datetime):
        t = s
    else:
        s = str(s).strip().replace("Z", "+00:00")
        try:
            t = dt.datetime.fromisoformat(s)
        except ValueError:
            try:
                t = dt.datetime.fromisoformat(s[:10])
            except ValueError:
                return None
    if t.tzinfo:
        t = t.astimezone().replace(tzinfo=None)
    return t


def norm_file(name):
    name = Path(str(name).strip()).name
    return name if name.endswith(".json") else name + ".json"


def load_sent():
    """Every record in data/sent/, with _file, _when (datetime), _date, _kind and _root (thread's first file)."""
    rows = []
    for p in sorted(config.SENT.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            print(f"(skipping unreadable data/sent/{p.name})", file=sys.stderr)
            continue
        if not isinstance(d, dict):
            continue
        d["_file"] = p.name
        d["_when"] = parse_when(d.get("sent_at"))
        d["_date"] = d["_when"].date() if d["_when"] else None
        d["_kind"] = str(d.get("kind") or "first").lower()
        d["_root"] = norm_file(d["reply_to"]) if d.get("reply_to") and d["_kind"] != "first" else p.name
        rows.append(d)
    return rows


def threads(sent=None):
    """thread root file -> its records, oldest first."""
    sent = load_sent() if sent is None else sent
    out = {}
    for d in sent:
        out.setdefault(d["_root"], []).append(d)
    for msgs in out.values():
        msgs.sort(key=lambda d: d["_when"] or dt.datetime.min)
    return out


def first_of(root, msgs):
    """The thread's first email, or None when only follow-ups/replies of it are on disk."""
    return next((m for m in msgs if m["_file"] == root and m["_kind"] == "first"), None)


def read_outcomes():
    """All lines of data/outcomes.jsonl in order (a damaged line is skipped, not fatal)."""
    p = config.OUTCOMES
    rows = []
    if p.exists():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except ValueError:
                print(f"(outcomes.jsonl line {i} is not JSON, skipped)", file=sys.stderr)
                continue
            if isinstance(o, dict) and o.get("file") and o.get("outcome"):
                rows.append(o)
    return rows


def latest_outcomes(rows=None):
    """file -> its latest outcome record (the last line wins)."""
    out = {}
    for o in read_outcomes() if rows is None else rows:
        out[o["file"]] = o
    return out


def append_outcome(file, outcome, note="", date=None):
    rec = {"file": file, "outcome": outcome, "note": note, "date": date or str(dt.date.today())}
    config.OUTCOMES.parent.mkdir(parents=True, exist_ok=True)
    with config.OUTCOMES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def status_of(first, latest, today=None):
    """call/referral/.../bounce, or no_reply after NO_REPLY_DAYS of silence, or pending before that."""
    o = latest.get(first["_file"])
    if o:
        return o["outcome"]
    today = today or dt.date.today()
    if first["_date"] and (today - first["_date"]).days >= NO_REPLY_DAYS:
        return "no_reply"
    return "pending"


def resolve(arg, sent):
    """A user's file argument -> the thread root it belongs to."""
    by_name = {d["_file"]: d for d in sent}
    for cand in (arg.strip(), norm_file(arg)):
        if cand in by_name:
            return by_name[cand]["_root"]
    a = arg.strip().lower().removesuffix(".json")
    hits = [d for d in sent if a in d["_file"].lower() or a in str(d.get("name") or "").lower()]
    roots = sorted({d["_root"] for d in hits})
    if len(roots) == 1:
        return roots[0]
    if not roots:
        sys.exit(f"Nothing in data/sent/ matches '{arg}'. Run `python tools/outcomes.py list` to see the files.")
    sys.exit(f"'{arg}' matches {len(roots)} threads. Be more specific: " + ", ".join(roots))


def cmd_label(args):
    sent = load_sent()
    if not sent:
        sys.exit("data/sent/ is empty: nothing to label yet.")
    root = resolve(args.file, sent)
    prev = latest_outcomes().get(root)
    append_outcome(root, args.outcome, " ".join(args.note).strip())
    was = f" (was {prev['outcome']})" if prev and prev["outcome"] != args.outcome else ""
    print(f"Labeled {root}: {args.outcome}{was}.")


def cmd_list(args):
    sent = load_sent()
    latest = latest_outcomes()
    today = dt.date.today()
    rows = []
    for root, msgs in threads(sent).items():
        first = first_of(root, msgs) or msgs[0]
        st = status_of(first, latest, today) if first["_file"] == root else (latest.get(root) or {}).get("outcome", "?")
        if args.only and st != args.only:
            continue
        o = latest.get(root) or {}
        rows.append((first["_date"] or dt.date.min, root, str(first.get("name") or ""), str(first.get("firm") or ""),
                     st, o.get("date", ""), o.get("note", ""), len(msgs) - 1))
    if not rows:
        print("Nothing sent yet." if not sent else "No thread has that outcome.")
        return
    rows.sort()
    print(f"{'sent':10}  {'outcome':9} {'name':22} {'firm':22} {'file':34} note")
    for d, root, name, firm, st, odate, note, more in rows:
        extra = f" [+{more} more sent]" if more else ""
        when = f"({odate}) " if odate else ""
        print(f"{str(d) if d != dt.date.min else '?':10}  {st:9} {name[:22]:22} {firm[:22]:22} {root[:34]:34} "
              f"{when}{note[:60]}{extra}")
    counts = {}
    for r in rows:
        counts[r[4]] = counts.get(r[4], 0) + 1
    print("\n" + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) + f"  ({len(rows)} threads)")


def main(argv=None):
    safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lb = sub.add_parser("label", help="record what happened in a thread")
    lb.add_argument("file", help="data/sent file name, or a unique part of it or of the person's name")
    lb.add_argument("outcome", choices=LABELS)
    lb.add_argument("note", nargs="*", help="short note, e.g. \"call Tue 2pm\"")
    ls = sub.add_parser("list", help="latest outcome of every first email")
    ls.add_argument("--only", choices=LABELS + ("no_reply", "pending"), help="show one outcome only")
    args = ap.parse_args(argv)
    (cmd_label if args.cmd == "label" else cmd_list)(args)


if __name__ == "__main__":
    main()
