"""Send the emails the user approved, from their own Gmail. DRY RUN unless --send.

Setup (once): put GMAIL_ADDRESS and GMAIL_APP_PASSWORD (a Gmail app password the user creates and types in
themselves) in me/config.env, and the résumé PDF in me/resume/. This tool never prints the password.

Each email is one draft JSON in data/approved/ (schema in SPEC.md). Before anything goes out, every draft must
clear these guards and gate.py:
  - first emails: email_confidence "published" and address_check "verified" within the last 3 days
    (python tools/verify_addresses.py <folder>). Printed addresses bounced 0.5%, pattern-guessed ones 13%.
  - never a second first email to an address that already got one (use a follow-up instead)
  - per-firm cap: at most N people ever at one firm (me/strategy.md "max people per firm: N", default 3),
    counted by email domain over every first email already sent
  - at most 5 first emails to one firm in one batch, so a firm's mail filter never sees a burst
  - daily cap DAILY_CAP (me/config.env, default 40) for cold mail; replies to people who wrote back don't wait
  - bounce guard over the last 40 published first emails: >3% bounced -> cap 15, >8% -> sending paused
    (Gmail starts filtering senders whose mail bounces, so this throttles before that happens)
Follow-ups and replies thread under the original: reply_to names the sent file (its message_id is used),
in_reply_to carries a Message-ID they sent. The first PDF in me/resume/ is attached unless attach is "none".

    python tools/send_approved.py                         dry run: what would go out, guards, send room; sends nothing
    python tools/send_approved.py --send                  sends, saves each to data/sent/ with sent_at + message_id
    python tools/send_approved.py --send --delay 120      seconds between emails (default 45)
    python tools/send_approved.py --send --cap 20         today's cap override (the bounce guard still wins)
    python tools/send_approved.py --test-login            logs in to Gmail and quits (sends nothing)
"""
import argparse
import json
import mimetypes
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import config as C

DELAY_SECONDS = 45
DEFAULT_DAILY_CAP = 40
MAX_PER_FIRM_PER_BATCH = 5
BOUNCE_WINDOW = 40
WARM_KINDS = ("reply", "riff", "scheduling", "thankyou")  # answering someone who wrote back isn't cold volume
FREEMAIL = {"gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com", "msn.com",
            "icloud.com", "me.com", "mac.com", "aol.com", "protonmail.com", "proton.me", "comcast.net",
            "att.net", "verizon.net", "ymail.com", "gmx.com"}


# ---------- records ----------

def sent_records():
    out = []
    for f in sorted(C.SENT.glob("*.json")):
        try:
            out.append((f.name, json.loads(f.read_text(encoding="utf-8"))))
        except ValueError:
            continue
    return out


def kind_of(d):
    return d.get("kind") or "first"


def firm_key(d):
    """The firm a draft counts against: its registered email domain (na.firm.com -> firm.com), or the firm name
    for personal addresses like gmail.com."""
    domain = (d.get("to") or "").lower().rsplit("@", 1)[-1].strip()
    if not domain or domain in FREEMAIL:
        return "firm:" + (d.get("firm") or domain or "?").strip().lower()
    parts = domain.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in ("co", "com", "ac", "org", "net", "gov", "edu"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def parse_time(s, fmt):
    try:
        return time.mktime(time.strptime(s, fmt))
    except (TypeError, ValueError):
        return 0.0


# ---------- caps ----------

def bounce_rate(last=BOUNCE_WINDOW):
    """Share of the most recent published first emails that bounced (outcomes.jsonl "bounce")."""
    bounced = {o.get("file") for o in C.jsonl(C.OUTCOMES) if o.get("outcome") == "bounce"}
    recent = sorted(((d.get("sent_at", ""), name) for name, d in sent_records()
                     if kind_of(d) == "first" and str(d.get("email_confidence", "")).lower() == "published"),
                    reverse=True)[:last]
    if not recent:
        return 0.0, 0
    return sum(1 for _, name in recent if name in bounced) / len(recent), len(recent)


def daily_cap(env, override=None, quiet=False):
    """(cap, cold emails already sent today). The bounce guard always wins over the cap and any override."""
    try:
        cap = int(env.get("DAILY_CAP") or DEFAULT_DAILY_CAP)
    except ValueError:
        cap = DEFAULT_DAILY_CAP
    if override is not None:
        cap = override
    today = time.strftime("%Y-%m-%d")
    sent_today = sum(1 for _, d in sent_records()
                     if kind_of(d) not in WARM_KINDS and str(d.get("sent_at", "")).startswith(today))
    rate, n = bounce_rate()
    if n >= 10 and rate > 0.08:
        if not quiet:
            print(f"Bounce rate {rate:.0%} over the last {n} published first emails. Sending paused: fix addresses first.")
        cap = 0
    elif n >= 10 and rate > 0.03:
        if not quiet:
            print(f"Bounce rate {rate:.0%} over the last {n} published first emails. Cap lowered to 15 to protect "
                  "the Gmail account.")
        cap = min(cap, 15)
    return cap, sent_today


# ---------- drafts ----------

def find_resume(prof):
    folder = C.ME / "resume"
    named = prof.get("resume") if isinstance(prof.get("resume"), str) else ""
    if named and (folder / Path(named).name).exists() and named.lower().endswith(".pdf"):
        return folder / Path(named).name
    pdfs = sorted(folder.glob("*.pdf")) if folder.exists() else []
    return pdfs[0] if pdfs else None


def resolve_attachment(spec, prof):
    """None for attach "none"; a PDF path for anything else ("resume", a track name, or a file in me/resume/)."""
    if spec in (None, "", False, "none", "None"):
        return None
    if isinstance(spec, str) and spec.lower().endswith(".pdf"):
        p = Path(spec)
        return p if p.is_absolute() and p.exists() else C.ME / "resume" / p.name  # missing: reported by the guards
    return find_resume(prof) or (C.ME / "resume" / "(no PDF found)")


def load_profile_safe():
    if (C.ME / "profile.md").exists():
        try:
            return C.load_profile()
        except SystemExit:
            pass
    return {}


def load_drafts(prof):
    drafts = []
    for path in sorted(C.APPROVED.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"BLOCKED {path.name}: not valid JSON ({e}). Nothing was sent.")
        missing = [k for k in ("to", "subject", "body") if not data.get(k)]
        if missing:
            sys.exit(f"BLOCKED {path.name}: missing {', '.join(missing)}. Nothing was sent.")
        data["_attach"] = resolve_attachment(data.get("attach", prof.get("attach") or "resume"), prof)
        drafts.append((path, data))
    return drafts


def recipient_guards(drafts):
    """Everything that must be true about the recipients before a batch goes out. Returns a list of problems."""
    problems, warnings = [], []
    sent = sent_records()
    sent_first_to = {d.get("to", "").lower(): name for name, d in sent if kind_of(d) == "first"}
    cap = C.load_strategy_cap()
    people_at = {}  # firm key -> set of addresses ever sent a first email
    for name, d in sent:
        if kind_of(d) == "first" and d.get("to"):
            people_at.setdefault(firm_key(d), set()).add(d["to"].lower())
    batch_count, batch_to = {}, {}
    now = time.time()
    for path, d in drafts:
        kind = kind_of(d)
        to = d["to"].strip().lower()
        if d["_attach"] is not None and not d["_attach"].exists():
            problems.append(f"{path.name}: no résumé PDF at {d['_attach']}. Put your PDF in me/resume/ "
                            "or set attach to \"none\".")
        if kind != "first":
            if not (d.get("reply_to") or d.get("in_reply_to")):
                problems.append(f"{path.name}: a {kind} must name the sent email it answers (reply_to) "
                                "or the Message-ID it answers (in_reply_to).")
            if d.get("reply_to") and not (C.SENT / d["reply_to"]).exists():
                problems.append(f"{path.name}: reply_to {d['reply_to']} not found in data/sent/.")
            continue
        if to in sent_first_to:
            problems.append(f"{path.name}: {to} already got a first email ({sent_first_to[to]}). "
                            "Use a follow-up instead.")
        if to in batch_to:
            problems.append(f"{path.name}: {to} is also in {batch_to[to]} in this batch.")
        batch_to[to] = path.name
        conf = str(d.get("email_confidence", "")).lower()
        if conf != "published":
            problems.append(f"{path.name}: email_confidence is '{conf or 'missing'}'. Only addresses printed on a "
                            "public page are sent (pattern-guessed addresses bounced 13% vs 0.5% for printed ones). "
                            "Find a printed address or reach this person another way.")
        chk = d.get("address_check") or {}
        age = now - parse_time(chk.get("checked_at", ""), "%Y-%m-%d %H:%M")
        if chk.get("status") != "verified" or age > 3 * 86400:
            seen = chk.get("status") or "never checked"
            if chk.get("status") == "verified":
                seen = f"last verified {chk.get('checked_at') or '?'}, older than 3 days"
            problems.append(f"{path.name}: address not verified in the last 3 days ({seen}). "
                            "Run: python tools/verify_addresses.py <folder>")
        key = firm_key(d)
        firm = d.get("firm") or key
        batch_count[key] = batch_count.get(key, 0) + 1
        if batch_count[key] > MAX_PER_FIRM_PER_BATCH:
            problems.append(f"{path.name}: more than {MAX_PER_FIRM_PER_BATCH} first emails to {firm} in one batch. "
                            "Move this one to another day.")
        people = people_at.setdefault(key, set())
        if to not in people and len(people) >= cap:
            problems.append(f"{path.name}: {firm} ({key}) already has {len(people)} people emailed; the per-firm cap "
                            f"is {cap} (me/strategy.md \"max people per firm\").")
        people.add(to)
        app = d.get("application") or {}
        if not app.get("title"):
            warnings.append(f"{path.name}: no application.title. Tie each contact to a real role so the update "
                            "email after applying has something to say.")
    return problems, warnings


# ---------- message ----------

def unwrap(text):
    """Each paragraph goes out as one line so the mail client wraps it naturally. Hard breaks mid-sentence read as
    copy-paste. Keeps sign-offs like "Best,\\nDana" and the "--" signature block as written."""
    paragraphs = []
    for para in text.strip().replace("\r\n", "\n").split("\n\n"):
        lines = [l.strip() for l in para.split("\n") if l.strip()]
        if not lines or lines[0].startswith("--"):
            paragraphs.append("\n".join(lines))
            continue
        out = lines[0]
        for line in lines[1:]:
            out += ("\n" if out.endswith(",") else " ") + line
        paragraphs.append(out)
    return "\n\n".join(paragraphs)


def signature(prof):
    """"--" block from me/profile.md: `signature:` if set (use " | " between parts), else name + school | major |
    class year. Empty when the profile has no name."""
    if isinstance(prof.get("signature"), str) and prof["signature"].strip():
        return "\n\n--\n" + prof["signature"].strip()
    name = prof.get("name") if isinstance(prof.get("name"), str) else ""
    if not name:
        return ""
    year = next((prof[k] for k in ("class_year", "class", "graduation_year", "grad_year")
                 if isinstance(prof.get(k), str) and prof.get(k)), "")
    bits = [prof.get("school"), prof.get("major"), (f"Class of {year}" if year and year.isdigit() else year)]
    line2 = " | ".join(b for b in bits if isinstance(b, str) and b)
    return "\n\n--\n" + name + ("\n" + line2 if line2 else "")


def build_message(d, cfg, prof):
    msg = EmailMessage()
    from_name = cfg.get("FROM_NAME") or (prof.get("name") if isinstance(prof.get("name"), str) else "")
    msg["From"] = f"{from_name} <{cfg['GMAIL_ADDRESS']}>" if from_name else cfg["GMAIL_ADDRESS"]
    msg["To"] = d["to"]
    if d.get("cc"):  # e.g. an assistant the contact looped in to schedule the call
        msg["Cc"] = d["cc"]
    msg["Subject"] = d["subject"]
    msg["Message-ID"] = make_msgid(domain=cfg["GMAIL_ADDRESS"].split("@")[1])
    if d.get("reply_to"):  # follow-ups thread under the original email
        orig = json.loads((C.SENT / d["reply_to"]).read_text(encoding="utf-8"))
        if orig.get("message_id"):
            msg["In-Reply-To"] = orig["message_id"]
            msg["References"] = orig["message_id"]
        if not d["subject"].lower().startswith("re:"):
            msg.replace_header("Subject", "Re: " + orig.get("subject", d["subject"]))
    if d.get("in_reply_to"):  # answering a thread they started (or a colleague they looped in)
        for h in ("In-Reply-To", "References"):
            if h in msg:
                msg.replace_header(h, d["in_reply_to"])
            else:
                msg[h] = d["in_reply_to"]
    body = unwrap(d["body"])
    sig = signature(prof)
    if sig and sig.strip().splitlines()[-1] not in body:
        body += sig
    msg.set_content(body)
    if d["_attach"]:
        ctype = mimetypes.guess_type(d["_attach"].name)[0] or "application/pdf"
        main, sub = ctype.split("/", 1)
        msg.add_attachment(d["_attach"].read_bytes(), maintype=main, subtype=sub, filename=d["_attach"].name)
    return msg


def gmail_config(env, need=True):
    missing = [k for k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD") if not env.get(k)]
    if missing and need:
        sys.exit(f"BLOCKED me/config.env is missing {', '.join(missing)}. Add it there yourself (see "
                 "me.example/config.env.example). Nothing was sent.")
    return missing


def login(smtp, env):
    try:
        smtp.login(env["GMAIL_ADDRESS"], env["GMAIL_APP_PASSWORD"].replace(" ", ""))
    except smtplib.SMTPAuthenticationError:
        sys.exit("BLOCKED Gmail refused the login. Check GMAIL_ADDRESS and the app password in me/config.env "
                 "(2-Step Verification must be on; the password is not shown here). Nothing more was sent.")


# ---------- main ----------

def main():
    sys.stdout.reconfigure(errors="replace")  # never crash printing a name the console can't show
    ap = argparse.ArgumentParser(description="Send data/approved/ from your Gmail. Dry run unless --send.")
    ap.add_argument("--send", action="store_true", help="actually send (default is a dry run)")
    ap.add_argument("--delay", type=int, default=DELAY_SECONDS, help="seconds between emails (default 45)")
    ap.add_argument("--cap", type=int, default=None, help="today's cap override (the bounce guard still applies)")
    ap.add_argument("--test-login", action="store_true", help="log in to Gmail and quit; sends nothing")
    a = ap.parse_args()
    env = C.load_env()
    prof = load_profile_safe()

    if a.test_login:
        gmail_config(env)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
            login(smtp, env)
        print(f"Login OK for {env['GMAIL_ADDRESS']}. Nothing was sent.")
        return

    drafts = load_drafts(prof)
    if not drafts:
        missing = gmail_config(env, need=False)
        print("No approved emails in data/approved/.")
        print(f"Setup: Gmail address {'set' if env.get('GMAIL_ADDRESS') else 'MISSING'}, app password "
              f"{'set' if env.get('GMAIL_APP_PASSWORD') else 'MISSING'}, résumé "
              f"{find_resume(prof).name if find_resume(prof) else 'MISSING (me/resume/*.pdf)'}"
              + (". Fill in me/config.env yourself." if missing else "."))
        return
    for path, d in drafts:
        att = d["_attach"].name if d["_attach"] else "no attachment"
        print(f"- {path.name}: to {d['to']} | {d['subject']} | {kind_of(d)} | {att}")
    problems, warnings = recipient_guards(drafts)
    for w in warnings:
        print("WARN " + w)
    if problems:
        for p in problems:
            print("BLOCKED " + p)
        sys.exit("\nNothing was sent.")
    import gate  # every email must pass the pre-send gate, dry run or not
    _, failed = gate.run(C.APPROVED)
    if failed:
        for name, errs in failed.items():
            print(f"BLOCKED {name}: " + "; ".join(errs))
        sys.exit(f"\n{len(failed)} email(s) failed the pre-send gate. Nothing was sent.")

    cap, sent_today = daily_cap(env, a.cap)
    room = max(cap - sent_today, 0)
    warm = [x for x in drafts if kind_of(x[1]) in WARM_KINDS]  # replies never wait on the cold cap
    cold = [x for x in drafts if kind_of(x[1]) not in WARM_KINDS]
    if not a.send:
        missing = gmail_config(env, need=False)
        print(f"\nSend room today: {room} cold (cap {cap}, sent {sent_today}); {len(warm)} warm + {len(cold)} cold queued.")
        if missing:
            print(f"Note: me/config.env is missing {', '.join(missing)}; --send will refuse until you add it.")
        print(f"{len(drafts)} email(s) ready. Nothing was sent. Re-run with --send to send them.")
        return

    gmail_config(env)
    if room == 0 and not warm:
        print(f"Daily cap reached ({sent_today}/{cap}). The rest send tomorrow.")
        return
    if len(cold) > room:
        print(f"Sending {room} cold today (cap {cap}, already sent {sent_today}). {len(cold) - room} wait for tomorrow.")
        cold = cold[:room]
    queue = warm + cold
    for i, (path, d) in enumerate(queue):
        msg = build_message(d, env, prof)
        try:  # one connection per email: Gmail drops idle connections during the delay between sends
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=60) as smtp:
                login(smtp, env)
                smtp.send_message(msg)
        except smtplib.SMTPRecipientsRefused:
            sys.exit(f"BLOCKED {path.name}: Gmail refused the address {d['to']}. Left in data/approved/; "
                     f"{i} sent before it.")
        except (OSError, smtplib.SMTPException) as e:
            sys.exit(f"Network error sending {path.name} ({type(e).__name__}). {i} sent; the rest stay in "
                     "data/approved/. Re-run when back online.")
        d.pop("_attach", None)
        d["sent_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        d["message_id"] = msg["Message-ID"]
        (C.SENT / path.name).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        path.unlink()
        print(f"Sent to {d['to']}", flush=True)
        if i < len(queue) - 1:
            time.sleep(a.delay)
    print("Done.")


if __name__ == "__main__":
    main()
