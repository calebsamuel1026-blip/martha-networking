"""What the data says: response rates, and candidate lessons when a difference is real.

    python tools/results.py                  rates overall, by segment, by subject thread, by day + candidate lessons
    python tools/results.py --write-lessons  also append the qualifying lessons to me/lessons.md

Counts first emails only. A first email with no outcome counts as no reply after 4 days (every real reply in the
original data came within 43 hours); younger ones are "pending" and left out.
  delivered  = sent minus bounce and out-of-office (never reached a human)
  any reply  = a human answered: replied, call, referral, declined or negative
  positive   = call, referral or replied
  call/ref   = call or referral, the real goal
A candidate lesson needs at least 30 delivered emails in each of two values of a dimension and a two-proportion
z of at least 2 on the positive rate. Mention dimensions use BROAD patterns (every phrasing of a thing): an
earlier version matched only one phrasing and produced a false lesson.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import outcomes as O  # noqa: E402

MIN_N, MIN_Z = 30, 2.0
HUMAN = O.HUMAN

SENIORITY = [  # order matters: the first match wins
    ("recruiter", r"recruit|talent|campus|university relations|early[- ]careers?|human resources|\bHR\b|"
                  r"people (team|partner|operations)|staffing"),
    ("senior", r"managing director|\bMD\b|\bpartner\b|principal|founder|owner|(?<!vice )(?<!vice-)president|\bchief\b|"
               r"\bC[EFOTM]O\b|"
               r"head of|chair|executive director|\bSVP\b|\bEVP\b|senior vice president|director|\bdean\b"),
    ("mid", r"vice president|\bVP\b|manager|senior associate|\blead\b|supervisor|senior (consultant|engineer|analyst|"
            r"accountant|advisor|adviser)|counsel|attorney|\bsenior\b"),
    ("junior", r"analyst|associate|consultant|engineer|accountant|coordinator|specialist|assistant|intern|junior|"
               r"\bstaff\b|representative|advisor|adviser|planner|nurse|teacher|developer|scientist"),
]
FAMILY = [  # broad role families that work for any field
    ("recruiting", SENIORITY[0][1]),
    ("advisor / wealth", r"financial (advisor|adviser|planner|consultant)|wealth|private client|planner|\bCFP\b"),
    ("banking / deals", r"invest(ment)?[- ]bank|\bM&A\b|mergers|capital markets|corporate finance|leveraged|"
                        r"restructuring|coverage|private equity|venture|transaction|\bdeal"),
    ("consulting / strategy", r"consult|strategy|strategic|advisory"),
    ("accounting / audit / tax", r"account|audit|\btax\b|\bCPA\b|assurance|controller"),
    ("engineering / tech", r"engineer|developer|software|data scien|technolog|\bIT\b|product manager|architect"),
    ("sales / marketing", r"sales|marketing|\bbrand|business development|account executive|growth|communications"),
    ("legal", r"attorney|counsel|lawyer|legal|paralegal|law clerk"),
    ("healthcare", r"physician|doctor|nurse|clinical|medical|health|pharm|therap"),
    ("finance / operations", r"financ|analyst|operations|logistics|supply chain|treasury|\brisk\b|portfolio"),
]
TEAM_INBOX = re.compile(r"recruit|career|campus|early|talent|jobs|\bhr\b|^hr|info|hello|contact|team|intern|admissions",
                        re.I)
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def classify(text, table, default="other"):
    for label, rx in table:
        if re.search(rx, text or "", re.I):
            return label
    return default


def title_of(d):
    cp = d.get("call_prep") if isinstance(d.get("call_prep"), dict) else {}
    return str(cp.get("title") or d.get("title") or "")


def segment(d):
    cp = d.get("call_prep") if isinstance(d.get("call_prep"), dict) else {}
    s = str(cp.get("seniority") or "").strip()
    if s:
        return classify(s, SENIORITY, default=s.lower())
    return classify(title_of(d), SENIORITY, default="unknown")


def words_bucket(n):
    return "<100 words" if n < 100 else "100-129" if n < 130 else "130-160" if n <= 160 else ">160 words"


def subject_thread(d):
    """The subject's common thread with this person's name and firm taken out, so the same idea groups together."""
    if d.get("thread") or d.get("thread_type"):
        return str(d.get("thread") or d.get("thread_type"))
    s = re.sub(r"^\s*((re|fwd?)\s*:\s*)+", "", str(d.get("subject") or ""), flags=re.I).lower()
    for w in sorted(re.split(r"[\s,.&()]+", str(d.get("firm") or "")), key=len, reverse=True):
        if len(w) > 2:
            s = re.sub(rf"\b{re.escape(w.lower())}\b", "<firm>", s)
    for w in re.split(r"[\s,.]+", str(d.get("name") or "")):
        if len(w) > 1:
            s = re.sub(rf"\b{re.escape(w.lower())}\b", "<name>", s)
    s = re.sub(r"<firm>(\s*<firm>)+", "<firm>", s)
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", s)).strip() or "(no subject)"


QUALIFIERS = r"\b(club|varsity|intramural|competitive|amateur|youth|high school|college|recreational|pickup)\b"


def term_pattern(term):
    """Broad: any case, singular/plural/-ing/-er forms of the last word ("board game(s)", "hike/hiking/hiker"), and
    spaces, hyphens or nothing between words ("cross country", "cross-country", "crosscountry")."""
    words = [w for w in re.split(r"[\s\-_/]+", str(term).strip()) if w]
    if not words:
        return None
    last = words[-1]
    if len(last) > 5 and last.lower().endswith("ing"):
        tail = re.escape(last[:-3]) + r"(e|es|ed|er|ers|ing)"
    elif len(last) > 3 and last.lower().endswith("s") and not last.lower().endswith("ss"):
        tail = re.escape(last[:-1]) + r"(s|es|'s)?"
    else:
        tail = re.escape(last) + r"(s|es|ing|ed|er|ers|'s)?"
    sep = r"[\s/-]*"  # kept outside the f-string: a backslash there is a SyntaxError before Python 3.12
    return rf"\b{sep.join([re.escape(w) for w in words[:-1]] + [tail])}\b"


def interest_pattern(term):
    """The interest without its (notes), and also without qualifiers: "club volleyball (setter)" -> volleyball."""
    t = re.sub(r"\(.*?\)", " ", str(term)).strip()
    core = re.sub(r"\s+", " ", re.sub(QUALIFIERS, " ", t, flags=re.I)).strip()
    pats = [term_pattern(t)] + ([term_pattern(core)] if core and core.lower() != t.lower() else [])
    pats = [p for p in pats if p]
    return (t, "|".join(pats)) if pats else (t, None)


def school_regex(profile):
    """The school's full name, any aliases the user listed, the name without 'University/College of', and its
    initials (case-sensitive, so 'UM' does not match 'um')."""
    names = []
    for k, v in profile.items():
        if "school" in k.lower() and not k.startswith("_"):
            names += config.as_list(v)
    names = [n for n in names if isinstance(n, str) and n.strip()]
    if not names:
        return None
    pats, initials = [], set()
    for n in names:
        pats.append(term_pattern(n))
        short = re.sub(r"\b(the|university|college|of|at|institute|school)\b", " ", n, flags=re.I).strip()
        if short and short.lower() != n.lower() and len(short) > 3:
            pats.append(term_pattern(short))
        caps = [w[0] for w in re.findall(r"\b[A-Z][a-zA-Z]+", n) if w.lower() not in ("of", "the", "at", "and")]
        if len(caps) >= 2:
            initials.add("".join(caps))
        if re.fullmatch(r"[A-Z&]{2,6}", n.strip()):
            initials.add(n.strip())
    broad = re.compile("|".join(p for p in pats if p), re.I)
    init = re.compile(r"\b(" + "|".join(map(re.escape, sorted(initials))) + r")\b") if initials else None
    return lambda text: bool(broad.search(text) or (init and init.search(text)))


def dimensions(profile):
    dims = {
        "segment (seniority)": segment,
        "role family": lambda d: classify(title_of(d), FAMILY),
        "subject thread": subject_thread,
        "length": lambda d: words_bucket(len(str(d.get("body") or "").split())),
        "resume attached": lambda d: "no" if str(d.get("attach") or "").lower() in ("", "none", "false", "no") else "yes",
        "recipient": lambda d: "team inbox" if TEAM_INBOX.search(str(d.get("to") or "").split("@")[0]) else "person",
        "send time": lambda d: ("unknown" if not d["_when"] else "morning (6-12)" if 6 <= d["_when"].hour < 12 else
                                "afternoon (12-18)" if 12 <= d["_when"].hour < 18 else "evening/night"),
        "send weekday": lambda d: WEEKDAYS[d["_when"].weekday()] if d["_when"] else "unknown",
        "hook of theirs used": lambda d: "yes" if str(((d.get("research") or {}) if isinstance(d.get("research"), dict)
                                                       else {}).get("hook_used") or "").strip() else "no",
    }
    school = school_regex(profile)
    if school:
        dims["mentions your school"] = lambda d: "yes" if school(str(d.get("body") or "")) else "no"
    for t in config.as_list(profile.get("interests"))[:8]:
        label, pat = interest_pattern(t) if isinstance(t, str) else (t, None)
        if pat:
            rx = re.compile(pat, re.I)
            dims[f"mentions {label}"] = lambda d, rx=rx: "yes" if rx.search(str(d.get("body") or "")) else "no"
    return dims


def load_profile():
    if not (config.ME / "profile.md").exists():
        return {}
    try:
        return config.load_profile()
    except SystemExit:
        return {}


def rows_of(today):
    sent = O.load_sent()
    latest = O.latest_outcomes()
    rows, pending = [], 0
    for root, msgs in O.threads(sent).items():
        first = O.first_of(root, msgs)
        if not first:
            continue
        st = O.status_of(first, latest, today)
        if st == "pending":
            pending += 1
            continue
        rows.append((first, st))
    return rows, pending


def tally(rows):
    n = len(rows)
    dl = [s for _, s in rows if s not in O.UNREACHED]
    return {"sent": n, "delivered": len(dl), "human": sum(s in HUMAN for s in dl),
            "positive": sum(s in O.POSITIVE for s in dl), "callref": sum(s in ("call", "referral") for s in dl),
            "declined": sum(s == "declined" for s in dl), "bounce": sum(s == "bounce" for _, s in rows),
            "ooo": sum(s == "ooo" for _, s in rows)}


def pct(k, n):
    return f"{k} ({k / n:.0%})" if n else f"{k} (-)"


def print_table(title, groups, limit=None):
    print(f"\n{title}")
    print(f"  {'':30} {'sent':>5} {'deliv':>6} {'any reply':>11} {'positive':>11} {'call/ref':>10}")
    items = sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))
    for key, rows in items[:limit]:
        t = tally(rows)
        print(f"  {str(key)[:30]:30} {t['sent']:5} {t['delivered']:6} {pct(t['human'], t['delivered']):>11} "
              f"{pct(t['positive'], t['delivered']):>11} {pct(t['callref'], t['delivered']):>10}")
    if limit and len(items) > limit:
        print(f"  ...{len(items) - limit} more")


def z_test(r1, n1, r2, n2):
    p = (r1 + r2) / (n1 + n2)
    se = (p * (1 - p) * (1 / n1 + 1 / n2)) ** 0.5
    return (r1 / n1 - r2 / n2) / se if se else 0.0


def candidate_lessons(rows, dims):
    """Best value vs every other value with n >= MIN_N, positive rate, z >= MIN_Z."""
    delivered = [(d, s) for d, s in rows if s not in O.UNREACHED]
    lessons = []
    for dim, fn in dims.items():
        groups = {}
        for d, s in delivered:
            try:
                key = fn(d)
            except Exception:
                key = "unknown"
            g = groups.setdefault(key, [0, 0])
            g[0] += 1
            g[1] += s in O.POSITIVE
        big = {k: v for k, v in groups.items() if v[0] >= MIN_N and k != "unknown"}
        if len(big) < 2:
            continue
        best = max(big, key=lambda k: big[k][1] / big[k][0])
        bn, br = big[best]
        for k, (n, r) in sorted(big.items()):
            if k == best:
                continue
            z = z_test(br, bn, r, n)
            if z >= MIN_Z:
                key = f"{dim}: '{best}' beat '{k}'"
                lessons.append((key, f"{key} on positive replies, {br}/{bn} ({br / bn:.0%}) vs {r}/{n} ({r / n:.0%}), "
                                     f"z={z:.1f}"))
    return lessons


def write_lessons(lessons):
    p = config.ME / "lessons.md"
    if not config.ME.exists():
        sys.exit("No me/ folder yet. Copy me.example/ to me/ (or run /onboard) first.")
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    new = [(k, l) for k, l in lessons if f"[results] {k}" not in text]
    if new:
        today = dt.date.today()
        add = "".join(f"- {today} [results] {l}\n" for _, l in new)
        p.write_text(text + ("" if not text or text.endswith("\n") else "\n") + add, encoding="utf-8")
    return len(new), len(lessons) - len(new)


def main(argv=None):
    O.safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-lessons", action="store_true", help="append qualifying lessons to me/lessons.md")
    args = ap.parse_args(argv)
    today = dt.date.today()
    rows, pending = rows_of(today)
    if not rows:
        print("No first emails old enough to count yet." + (f" ({pending} pending, under 4 days old)" if pending else ""))
        return
    t = tally(rows)
    dates = sorted(d["_date"] for d, _ in rows if d["_date"])
    span = f"{dates[0]} to {dates[-1]}" if dates else "unknown dates"
    print(f"=== Results: {t['sent']} first emails, {span} ===")
    print(f"  delivered {t['delivered']} (bounced {t['bounce']}, out of office {t['ooo']}); "
          f"{pending} pending (under {O.NO_REPLY_DAYS} days old, not counted)")
    d = t["delivered"]
    print(f"  any human reply {pct(t['human'], d)}   positive {pct(t['positive'], d)}   "
          f"call or referral {pct(t['callref'], d)}   declined {t['declined']}")
    if t["sent"]:
        print(f"  bounce rate {t['bounce'] / t['sent']:.1%} of everything sent")

    dims = dimensions(load_profile())
    by = lambda fn: {k: [r for r in rows if fn(r[0]) == k] for k in {fn(r[0]) for r in rows}}  # noqa: E731
    print_table("By segment (call_prep.seniority, else title keywords):", by(segment))
    print_table("By role family (title keywords):", by(dims["role family"]))
    print_table("By subject thread:", by(subject_thread), limit=12)
    by_day = {}
    for r in rows:
        by_day.setdefault(str(r[0]["_date"] or "?"), []).append(r)
    print(f"\nBy day sent:\n  {'':30} {'sent':>5} {'deliv':>6} {'any reply':>11} {'positive':>11} {'call/ref':>10}")
    for day in sorted(by_day):
        tt = tally(by_day[day])
        print(f"  {day:30} {tt['sent']:5} {tt['delivered']:6} {pct(tt['human'], tt['delivered']):>11} "
              f"{pct(tt['positive'], tt['delivered']):>11} {pct(tt['callref'], tt['delivered']):>10}")

    lessons = candidate_lessons(rows, dims)
    print(f"\nCandidate lessons (n>={MIN_N} delivered per value, z>={MIN_Z:g} on positive rate):")
    if lessons:
        for _, l in lessons:
            print(f"  - {l}")
        print("  Correlation, not proof: check each one makes sense before changing how you write.")
    else:
        print(f"  none yet. Each needs {MIN_N}+ delivered emails in two values of a dimension.")
    if args.write_lessons and lessons:
        added, already = write_lessons(lessons)
        print(f"\n{added} lesson(s) added to me/lessons.md" + (f", {already} already there." if already else "."))
    elif args.write_lessons:
        print("\nNothing to write to me/lessons.md.")


if __name__ == "__main__":
    main()
