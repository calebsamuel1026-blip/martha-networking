"""The morning command: what came in and what to do today. Sends nothing.

    python tools/digest.py               check Gmail first (check_replies.py, up to 3 minutes), then the digest
    python tools/digest.py --no-check    skip the Gmail check (offline, or you just ran it)

Prints, in order:
  1. replies to answer: threads where they wrote and you have not answered since (with the saved reply file)
  2. follow-ups due: first emails with no reply. Follow-up 1 is due 7 days after the first email, follow-up 2 at
     14 days (and at least 7 days after follow-up 1), nothing after that. Out-of-office threads still get them.
  3. applications to do: the postings saved on sent emails ("application"), with when they open
  4. drafts waiting in data/drafts/ and data/approved/
  5. send room left today and bounce health (the same guard the sender uses: over the last 40 first emails,
     more than 3% bounced -> cap 15, more than 8% -> sending paused)
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import outcomes as O  # noqa: E402

TOOLS = Path(__file__).resolve().parent
ANSWER = {"call", "referral", "replied", "declined"}
FOLLOWUP_DAYS = (7, 14)
BOUNCE_WINDOW = 40
DEFAULT_CAP = 40
# "I applied", "I've just applied", "I submitted my application", "applied for the ... role": the update email
APPLIED = re.compile(r"\b(I|I've|I have|I just|just)\s+(just\s+|recently\s+|now\s+|also\s+)?(applied|submitted (my |an |the )?"
                     r"application)\b|\bapplied (for|to) the\b|\bmy application (is in|went in|has been submitted)", re.I)
DONE_STATUS = re.compile(r"applied|submitted|done|closed|rejected|offer", re.I)
MONTH = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def section(title):
    print(f"\n{title}")


def run_check(timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([sys.executable, str(TOOLS / "check_replies.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env, cwd=str(config.ROOT))
        out = (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        out = (f"The Gmail check took over {timeout}s and was stopped. Run `python tools/check_replies.py` "
               "by itself, then `python tools/digest.py --no-check`.")
    print("  " + out.replace("\n", "\n  "))


def last_inbound(path):
    """When they last wrote (a human message, not an auto-reply), from the replies file."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = [b for b in text.split("----- next message -----") if "Auto-reply: yes" not in b]
    for b in reversed(blocks):
        m = re.search(r"^Date: (.+)$", b, re.M)
        if m:
            try:
                from email.utils import parsedate_to_datetime
                return O.parse_when(parsedate_to_datetime(m.group(1).strip()))
            except Exception:
                pass
    return dt.datetime.fromtimestamp(path.stat().st_mtime)


def load_drafts():
    out = []
    for folder in (config.DRAFTS, config.APPROVED):
        for p in sorted(folder.rglob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                d = {}
            out.append((p, d if isinstance(d, dict) else {}))
    return out


def parse_open(text):
    """A date from free text like '2026-12-01 (careers page)' or 'Estimated Jan-Mar 2027'."""
    t = str(text or "")
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\b[^0-9]{0,12}?(20\d\d)\b", t, re.I)
    if m:
        return dt.date(int(m.group(2)), MONTH[m.group(1).lower()], 1)
    return None


def bounce_health(sent, rows):
    """(rate, n) over the last BOUNCE_WINDOW first emails to published addresses."""
    bounced = {o["file"] for o in rows if o["outcome"] == "bounce"}
    recent = sorted((d for d in sent if d["_kind"] == "first"
                     and str(d.get("email_confidence", "")).lower() == "published"),
                    key=lambda d: d["_when"] or dt.datetime.min, reverse=True)[:BOUNCE_WINDOW]
    if not recent:
        return 0.0, 0
    return sum(d["_file"] in bounced for d in recent) / len(recent), len(recent)


def who(d):
    return f"{d.get('name') or d.get('to') or '?'} ({d.get('firm') or '?'})"


def main(argv=None):
    O.safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-check", action="store_true", help="skip the Gmail check")
    ap.add_argument("--timeout", type=int, default=180, help="seconds allowed for the Gmail check (default 180)")
    args = ap.parse_args(argv)
    today = dt.date.today()
    print(f"=== Networking digest {today} ===")

    section("Gmail check:")
    if args.no_check:
        print("  skipped (--no-check)")
    else:
        run_check(args.timeout)

    sent = O.load_sent()
    rows = O.read_outcomes()
    latest = O.latest_outcomes(rows)
    threads = O.threads(sent)
    drafts = load_drafts()
    if not sent:
        print("\nNothing sent yet. Start with /find-contacts, then /draft and /send-day.")

    # 1. replies to answer
    todo = []
    for root, msgs in threads.items():
        o = latest.get(root)
        if not o or o["outcome"] not in ANSWER:
            continue
        rf = config.REPLIES / f"{Path(root).stem}.txt"
        inbound = last_inbound(rf)
        if inbound is None:
            continue  # labeled by hand with no email to answer
        ours = [m["_when"] for m in msgs if m["_file"] != root and m["_when"]]
        if any(w >= inbound for w in ours):
            continue
        first = O.first_of(root, msgs) or msgs[0]
        unlabeled = o["outcome"] == "replied" and str(o.get("note", "")).startswith("auto")
        drafted = any(d.get("reply_to") and O.norm_file(d["reply_to"]) == root and d.get("kind") != "followup"
                      for _, d in drafts)
        todo.append((inbound, first, o, rf, unlabeled, drafted, root))
    section(f"Replies to answer ({len(todo)}):" if todo else "Replies to answer: none.")
    for inbound, first, o, rf, unlabeled, drafted, root in sorted(todo, key=lambda t: t[0]):
        print(f"  - {who(first)}: {o['outcome']}, wrote {inbound:%a %b %d %H:%M}  data/replies/{rf.name}"
              + ("  [reply draft waiting]" if drafted else ""))
        if unlabeled:
            print(f"      label it: python tools/outcomes.py label {root} call|referral|replied|declined \"note\"")

    # 2. follow-ups due
    due, soon = [], 0
    for root, msgs in threads.items():
        first = O.first_of(root, msgs)
        if not first or not first["_date"]:
            continue
        o = latest.get(root)
        if o and o["outcome"] != "ooo":
            continue
        if any(m["_kind"] in O.RESPONSE_KINDS for m in msgs):
            continue  # a conversation is under way
        fus = [m for m in msgs if m["_kind"] == "followup"]
        if len(fus) >= 2:
            continue
        n = len(fus) + 1
        when = first["_date"] + dt.timedelta(days=FOLLOWUP_DAYS[n - 1])
        if n == 2 and fus[-1]["_date"]:
            when = max(when, fus[-1]["_date"] + dt.timedelta(days=7))
        if when > today:
            soon += when <= today + dt.timedelta(days=2)
            continue
        drafted = any(d.get("kind") == "followup" and d.get("reply_to") and O.norm_file(d["reply_to"]) == root
                      for _, d in drafts)
        due.append((when, n, first, root, drafted, o))
    section(f"Follow-ups due ({len(due)}):" if due else "Follow-ups due: none today.")
    for when, n, first, root, drafted, o in sorted(due, key=lambda t: t[0]):
        age = (today - first["_date"]).days
        extra = "  [draft waiting]" if drafted else ""
        extra += f"  (had an out-of-office: {o.get('note', '')})" if o else ""
        print(f"  - follow-up {n} to {who(first)}: first email {first['_date']} (day {age})  reply_to={root}{extra}")
    if soon:
        print(f"  ({soon} more due in the next 2 days)")

    # 3. applications to do
    applied_firms = {str(d.get("firm") or "").lower() for d in sent if APPLIED.search(str(d.get("body") or ""))}
    apps = {}
    for d in sent:
        a = d.get("application")
        if not isinstance(a, dict) or not (a.get("title") or a.get("url")):
            continue
        firm = str(d.get("firm") or "")
        key = (firm.lower(), str(a.get("url") or a.get("title")).lower())
        if key in apps:
            continue
        if firm.lower() in applied_firms or DONE_STATUS.search(str(a.get("status") or "")):
            apps[key] = None
            continue
        apps[key] = (parse_open(a.get("est_open")), firm, a)
    done = sum(v is None for v in apps.values())
    todo_apps = sorted((v for v in apps.values() if v), key=lambda v: (v[0] or dt.date.max, v[1].lower()))
    section(f"Applications to do ({len(todo_apps)}):" if todo_apps else "Applications to do: none saved.")
    for opens, firm, a in todo_apps[:25]:
        flag = "  [should be open now]" if opens and opens <= today else ""
        est = str(a.get("est_open") or "opening date unknown")
        print(f"  - {firm}: {a.get('title') or '(posting)'}{flag}\n      opens: {est[:110]}{'...' if len(est) > 110 else ''}"
              + (f"\n      {a['url']}" if a.get("url") else ""))
    if len(todo_apps) > 25:
        print(f"  ...and {len(todo_apps) - 25} more")
    if done:
        print(f"  ({done} already applied or closed, not listed)")

    # 4. drafts waiting
    section("Drafts waiting:")
    batches = {}
    for p, _ in drafts:
        if config.DRAFTS in p.parents:
            b = p.parent.relative_to(config.DRAFTS).as_posix()
            batches[b] = batches.get(b, 0) + 1
    approved = sum(1 for p, _ in drafts if p.parent == config.APPROVED)
    for b, n in sorted(batches.items()):
        print(f"  - data/drafts/{b}: {n}")
    if not batches:
        print("  no drafts")
    if approved:
        print(f"  - data/approved: {approved} (staged for the sender; it should normally be empty)")

    # 5. send room and bounce health
    env = config.load_env()
    try:
        cap = int(env.get("DAILY_CAP") or DEFAULT_CAP)
    except ValueError:
        cap = DEFAULT_CAP
    rate, n = bounce_health(sent, rows)
    guard = ""
    if n >= 10 and rate > 0.08:
        cap, guard = 0, "  SENDING PAUSED: fix addresses first (re-verify, drop guessed ones)"
    elif n >= 10 and rate > 0.03:
        cap, guard = min(cap, 15), "  cap lowered to 15 to protect the Gmail account"
    sent_today = sum(1 for d in sent if d["_date"] == today and d["_kind"] not in O.RESPONSE_KINDS)
    section("Sending:")
    print(f"  room left today: {max(cap - sent_today, 0)} of {cap} (sent {sent_today} today; replies don't count)")
    print(f"  bounce rate: {rate:.1%} over the last {n} first emails")
    if guard:
        print(f"  {guard.strip()}")
    recent = [(o["date"], o["file"]) for o in rows if o["outcome"] == "bounce"
              and O.parse_when(o.get("date")) and (today - O.parse_when(o["date"]).date()).days <= 14]
    by_file = {d["_file"]: d for d in sent}
    for date, f in sorted(set(recent)):
        d = by_file.get(f, {})
        print(f"  - bounced {date}: {who(d) if d else f}. Find their address printed on a live page again, "
              "or the next person at the firm.")
    print("\nNothing was sent.")


if __name__ == "__main__":
    main()
