"""Check Gmail for replies, bounces and out-of-office notes from the people in data/sent/.

    python tools/check_replies.py              scan the last 30 days of the inbox
    python tools/check_replies.py --days 90    scan further back (first run, or after a long break)
    python tools/check_replies.py --dry-run    show what it finds, write nothing

Logs in over IMAP with GMAIL_ADDRESS and GMAIL_APP_PASSWORD from me/config.env (the password is never printed)
and opens the inbox READ-ONLY: nothing is marked read, moved or deleted. It only reads messages from people you
emailed (or that answer one of your sent emails), plus delivery-failure notices that name one of them.

Results:
  data/replies/<sent file stem>.txt   their messages, newest last, with each Message-ID (for threading a reply)
  data/outcomes.jsonl                 "replied", "bounce" or "ooo" for the thread's first email
Each (thread, outcome) pair is logged once. A thread you already labeled call/referral/declined/negative keeps
your label: new messages in it are still saved to its replies file and printed, so you can answer them.
"""
import argparse
import datetime as dt
import email
import imaplib
import re
import socket
import sys
from email.header import decode_header, make_header
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import outcomes as O  # noqa: E402

HOST, PORT, TIMEOUT = "imap.gmail.com", 993, 60
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
HEADER_FIELDS = ("FROM SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES AUTO-SUBMITTED X-AUTOREPLY X-AUTORESPOND "
                 "PRECEDENCE X-FAILED-RECIPIENTS")
SEEN = config.REPLIES / ".seen"  # Message-IDs already handled, so nothing is fetched or logged twice
SEP = "\n----- next message -----\n"

BOUNCE_FROM = re.compile(r"mailer-daemon|postmaster|mail delivery (subsystem|system)|microsoftexchange", re.I)
BOUNCE_SUBJECT = re.compile(
    r"delivery status notification|undeliver|delivery (has )?failed|delivery failure|failure notice|returned mail|"
    r"could not be delivered|mail delivery failed|message not delivered|address not found|non-?delivery", re.I)
DELAY = re.compile(r"\(delay\)|\bdelayed\b|delivery delayed|will (retry|keep trying)|still trying", re.I)
OOO_SUBJECT = re.compile(
    r"automatic reply|auto(matic)?[- ]?(reply|response)|autoreply|out of (the )?office|\bOOO\b|away from (the |my )?office|"
    r"on (vacation|holiday|leave)\b|abwesenheit|r[ée]ponse automatique|respuesta autom[aá]tica|fuera de la oficina", re.I)
OOO_AUTOMATED = re.compile(r"this is an? automat(ed|ic) (reply|response|message)|auto-?generated (reply|response|message)",
                           re.I)
OOO_AWAY = re.compile(
    r"\b(I am|I'm|I will be|I'll be)\s+(currently\s+)?(out of (the )?office|away from (the |my )?(office|desk|e-?mail)|"
    r"on (vacation|holiday|PTO|leave|parental leave|maternity leave|paternity leave)|traveling)", re.I)
OOO_RETURN = re.compile(r"limited (access to|ability to (check|respond to)) (my )?e-?mail|"
                        r"\b(respond|reply|get back to you)\b[^.\n]{0,40}\b(upon|on|when I|after) (my )?return", re.I)
ENGAGED = re.compile(r"happy to|glad to|would love|let'?s (chat|talk|connect|find)|let me know|your (resume|note)|"
                     r"\b(call|chat|talk|connect)\b", re.I)
RETURN_DATE = re.compile(
    r"\b(?:return(?:ing)?|back)\s+(?:to the office\s+)?(?:on\s+)?((?:(?:Mon|Tues?|Wed(?:nes)?|Thu(?:rs)?|Fri|Sat(?:ur)?|Sun)"
    r"[a-z]*,?\s+)?(?:[A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}/\d{1,2}(?:/\d{2,4})?))")
QUOTE_CUT = re.compile(
    r"^\s*On\b[^\n]{0,250}(\n[^\n]{0,250})?\bwrote:\s*$"   # Gmail / Apple Mail, may wrap onto a second line
    r"|^\s*-{2,}\s*Original Message\s*-{2,}"
    r"|^\s*_{8,}\s*$"                                    # Outlook separator line
    r"|^\s*From:\s[^\n]+\n\s*(Sent|Date):\s"             # Outlook header block
    r"|^\s*>", re.M | re.I)


def dec(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def msg_when(h):
    try:
        return O.parse_when(parsedate_to_datetime(h.get("Date")))
    except Exception:
        return None


def norm_id(x):
    x = (x or "").strip().lower()
    return x if not x or x.startswith("<") else f"<{x}>"


def ids_in(value):
    return {norm_id(m) for m in re.findall(r"<[^<>\s]+>", value or "")}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.skip += 1
        elif tag in ("br", "p", "div", "tr", "li", "blockquote"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(html):
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\n\s*\n+", "\n\n", "".join(p.out))


def _decode(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    try:
        return payload.decode(part.get_content_charset() or "utf-8", "replace")
    except LookupError:
        return payload.decode("utf-8", "replace")


def text_of(msg, everything=False):
    """The message's text: the first plain part (or its HTML as text). everything=True joins every part,
    including a returned original inside a bounce."""
    plain, html = [], []
    for part in msg.walk():
        if part.is_multipart() or part.get_content_type() not in ("text/plain", "text/html"):
            continue
        if part.get_filename() and not everything:
            continue
        (plain if part.get_content_type() == "text/plain" else html).append(_decode(part))
    if everything:
        return "\n".join(plain + [html_to_text(h) for h in html])
    return plain[0] if plain else html_to_text(html[0]) if html else ""


def their_words(body):
    """Only the new text they wrote, not the quoted history below it."""
    body = body.replace("\r\n", "\n")
    m = QUOTE_CUT.search(body)
    new = body[:m.start()].strip() if m else body.strip()
    return (new or body.strip())[:4000]


def auto_reply_kind(h, subject, words):
    """'ooo' when the message is an out-of-office or other automatic reply, else ''."""
    auto = (h.get("Auto-Submitted") or "").strip().lower()
    if (auto and auto != "no") or h.get("X-Autoreply") or h.get("X-Autorespond") \
            or (h.get("Precedence") or "").strip().lower() == "auto_reply":
        return "ooo"
    if OOO_SUBJECT.search(subject):
        return "ooo"
    if len(words.split()) < 150:
        if OOO_AUTOMATED.search(words):
            return "ooo"
        # a person who says "I'm out this week, happy to talk after" is a real reply: only pure away notices count
        if OOO_AWAY.search(words) and OOO_RETURN.search(words) and not ENGAGED.search(words):
            return "ooo"
    return ""


def bounced_addresses(msg, known):
    """Addresses from `known` that this delivery-failure notice says failed. Delays are not failures."""
    actions = {}
    for part in msg.walk():
        if part.get_content_type() != "message/delivery-status":
            continue
        blocks = part.get_payload()
        for b in blocks if isinstance(blocks, list) else []:
            rcpt = b.get("Final-Recipient") or b.get("Original-Recipient")
            if rcpt:
                actions[rcpt.split(";")[-1].strip().strip("<>").lower()] = (b.get("Action") or "").strip().lower()
    failed = {a for a, act in actions.items() if act in ("failed", "")}
    failed |= {a.lower() for _, a in getaddresses([msg.get("X-Failed-Recipients", "")]) if a}
    if not actions and not failed:
        if DELAY.search(dec(msg.get("Subject", ""))):
            return set()
        text = text_of(msg, everything=True)
        failed = {a for a in known if re.search(rf"(?<![\w.+-]){re.escape(a)}(?![\w-])", text, re.I)}
    return {a for a in failed if a in known}


def saved_ids():
    if not SEEN.exists():
        return set()
    return {l.strip() for l in SEEN.read_text(encoding="utf-8").splitlines() if l.strip()}


def save_reply(root, h, subject, words, auto):
    p = config.REPLIES / f"{Path(root).stem}.txt"
    block = (f"From: {dec(h.get('From'))}\nDate: {h.get('Date', '')}\nSubject: {subject}\n"
             f"Message-ID: {(h.get('Message-ID') or '').strip()}\n" + ("Auto-reply: yes\n" if auto else "")
             + f"\n{words}\n")
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text((old.rstrip("\n") + "\n" + SEP + block) if old.strip() else block, encoding="utf-8")
    return p


def imap_date(d):
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year}"  # not strftime: %b depends on the computer's language


def connect(env):
    user = (env.get("GMAIL_ADDRESS") or "").strip()
    secret = (env.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
    if not user or not secret:
        sys.exit("Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to me/config.env first (see README, 'Gmail app password').")
    socket.setdefaulttimeout(TIMEOUT)
    try:
        imap = imaplib.IMAP4_SSL(HOST, PORT, timeout=TIMEOUT)
    except OSError as e:
        sys.exit(f"Could not reach Gmail ({type(e).__name__}). Check the internet connection and try again.")
    try:
        imap.login(user, secret)
    except imaplib.IMAP4.error:
        sys.exit("Gmail refused the login. Check GMAIL_ADDRESS and the 16-letter app password in me/config.env, "
                 "and that IMAP is turned on in Gmail settings.")
    typ, _ = imap.select("INBOX", readonly=True)  # read-only: nothing is marked read or moved
    if typ != "OK":
        sys.exit("Could not open the Gmail inbox.")
    return imap, user.lower()


def fetch_headers(imap, uids, chunk=200):
    out = []
    for i in range(0, len(uids), chunk):
        typ, data = imap.uid("fetch", b",".join(uids[i:i + chunk]), f"(BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})])")
        if typ != "OK":
            continue
        for item in data:
            if isinstance(item, tuple):
                m = re.search(rb"UID (\d+)", item[0])
                if m:
                    out.append((m.group(1), email.message_from_bytes(item[1])))
    return out


def fetch_full(imap, uid):
    typ, data = imap.uid("fetch", uid, "(BODY.PEEK[])")
    for item in data if typ == "OK" else []:
        if isinstance(item, tuple):
            return email.message_from_bytes(item[1])
    return None


def run(days=30, dry=False):
    """Returns the printed lines. Exits with a message when there is nothing to check or the login fails."""
    sent = O.load_sent()
    if not sent:
        return ["Nothing sent yet."]
    by_addr, by_id = {}, {}
    for d in sorted(sent, key=lambda d: d["_when"] or dt.datetime.min):
        for _, a in getaddresses([str(d.get("to") or "")]):
            if a:
                by_addr.setdefault(a.lower(), (d["_root"], d["_when"]))
        if d.get("message_id"):
            by_id[norm_id(d["message_id"])] = d["_root"]
    names = {}
    for root, msgs in O.threads(sent).items():
        f = O.first_of(root, msgs) or msgs[0]
        names[root] = f"{f.get('name') or f.get('to')} ({f.get('firm') or '?'})"
    dates = [d["_date"] for d in sent if d["_date"]]
    since = max(min(dates), dt.date.today() - dt.timedelta(days=days)) if dates else dt.date.today() - dt.timedelta(days=days)

    rows = O.read_outcomes()
    have = {(o["file"], o["outcome"]) for o in rows}
    latest = O.latest_outcomes(rows)
    seen = saved_ids()
    found, new_seen = [], []
    imap, me = connect(config.load_env())
    try:
        typ, data = imap.uid("search", None, "SINCE", imap_date(since))
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        for uid, h in fetch_headers(imap, uids):
            frm = parseaddr(dec(h.get("From", "")))[1].lower()
            if not frm or frm == me:
                continue
            subject = dec(h.get("Subject", ""))
            mid = (h.get("Message-ID") or "").strip() or f"<uid-{uid.decode()}-{frm}>"
            if mid.lower() in seen:
                continue
            when = msg_when(h)
            is_bounce = BOUNCE_FROM.search(dec(h.get("From", ""))) or (
                frm not in by_addr and BOUNCE_SUBJECT.search(subject) and not re.match(r"\s*(re|fwd?)\s*:", subject, re.I))
            if is_bounce:
                msg = fetch_full(imap, uid)
                if msg is None:
                    continue
                for a in sorted(bounced_addresses(msg, by_addr)):
                    root, first_when = by_addr[a]
                    if when and first_when and when < first_when - dt.timedelta(minutes=5):
                        continue  # an old failure from before this email went out
                    if (root, "bounce") in have:
                        continue
                    if (latest.get(root) or {}).get("outcome") in O.HUMAN:
                        found.append(f"bounce notice for {a}, but {names.get(root, root)} already answered: not logged")
                    else:
                        if not dry:
                            O.append_outcome(root, "bounce", f"auto: check_replies ({a})")
                        have.add((root, "bounce"))
                        found.append(f"BOUNCE: {a}  {names.get(root, root)}  [{root}]")
                new_seen.append(mid.lower())
                continue
            root = None
            if frm in by_addr:
                r, first_when = by_addr[frm]
                if not (when and first_when and when < first_when - dt.timedelta(minutes=5)):
                    root = r
            if not root:
                refs = ids_in(h.get("In-Reply-To")) | ids_in(h.get("References"))
                root = next((by_id[i] for i in refs if i in by_id), None)
            if not root:
                continue
            msg = fetch_full(imap, uid)
            if msg is None:
                continue
            words = their_words(text_of(msg))
            kind = auto_reply_kind(msg, subject, words) or "replied"
            cur = (latest.get(root) or {}).get("outcome")
            who = names.get(root, root)
            if kind == "ooo":
                m = RETURN_DATE.search(words)
                note = "auto: out-of-office" + (f", back {m.group(1)}" if m else "")
                if cur is None and (root, "ooo") not in have:
                    if not dry:
                        O.append_outcome(root, "ooo", note)
                    have.add((root, "ooo"))
                    latest[root] = {"outcome": "ooo"}
                    found.append(f"out of office: {who}{', back ' + m.group(1) if m else ''}  [{root}]")
            else:
                path = config.REPLIES / f"{Path(root).stem}.txt"
                if not dry:
                    path = save_reply(root, msg, subject, words, auto=False)
                rel = f"data/replies/{path.name}"
                if (root, "replied") not in have and cur not in O.HUMAN:
                    if not dry:
                        O.append_outcome(root, "replied", "auto: check_replies")
                    have.add((root, "replied"))
                    latest[root] = {"outcome": "replied"}
                    found.append(f"REPLY: {who} -> {rel}  (label it: python tools/outcomes.py label {root} "
                                 f"call|referral|replied|declined)")
                else:
                    found.append(f"new message in an answered thread ({cur}): {who} -> {rel}")
            new_seen.append(mid.lower())
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    if new_seen and not dry:
        with SEEN.open("a", encoding="utf-8") as f:
            f.write("".join(m + "\n" for m in new_seen))
    lines = found or ["No new replies or bounces."]
    if dry:
        lines.append("(dry run: nothing was written)")
    return lines


def main(argv=None):
    O.safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=30, help="how many days of the inbox to scan (default 30)")
    ap.add_argument("--dry-run", action="store_true", help="show what it finds, write nothing")
    args = ap.parse_args(argv)
    print("\n".join(run(days=max(args.days, 1), dry=args.dry_run)))


if __name__ == "__main__":
    main()
