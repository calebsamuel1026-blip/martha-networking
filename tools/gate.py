"""Pre-send gate. Every draft must pass before send_approved.py will send it.

Catches the mistakes that make an email look careless or AI-written: banned punctuation, AI-tell phrases,
leftover placeholders, a greeting that doesn't match the address, the same sentence or phrase reused across a
batch, stat stacking, wrong length, selling yourself. On top of the universal rules it reads the user's own:
  me/profile.md   interest_line  -> its wording may repeat across a batch (it is the user's house line)
                  never_say      -> banned phrases (a list: `never_say: phrase one; phrase two`)
                  house_phrases  -> extra wording allowed to repeat (optional)
                  resume_items   -> names of clubs/jobs/projects: at most one per first email (optional)
                  school, standing (e.g. sophomore) -> the intro sentence may repeat
  me/lessons.md   every line starting "BAN:" (after an optional "- " and date) bans that phrase

    python tools/gate.py                      checks data/approved/
    python tools/gate.py drafts/batch-1       checks another folder (relative to cwd, the repo, data/ or data/drafts/)
    python tools/gate.py path/to/draft.json   checks one draft (batch checks need a folder)

Exit code 0 when everything passes, 1 otherwise. Import use: gate.check(draft, name) -> [errors],
gate.run(folder) -> (drafts, {name: [errors]}), gate.cross_checks([(name, draft), ...]) -> {name: [errors]}.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import config as C

# These marks read as machine-written in any email, so they are blocked everywhere, first emails included.
BANNED_CHARS = {";": "semicolon", "—": "em dash", "–": "en dash", "…": "ellipsis character"}

# Phrases a reader recognizes as a template or as AI. Every one of these was learned from real replies
# (or the lack of them): recipients either called them out or they showed up only in emails nobody answered.
AI_TELLS = [
    "i hope this finds you", "hope this email finds you", "i came across your profile", "i am reaching out",
    "i'm reaching out", "passionate about", "leverage", "i was impressed", "float this back", "just bumping",
    "just checking in", "i wanted to reach out", "delve", "in today's", "fast-paced", "furthermore", "moreover",
    "additionally", "i am writing to", "i'm writing to", "esteemed", "tapestry", "testament to", "navigate the",
    "thrilled", "excited to connect", "eager to learn more about the opportunity", "synergy", "game-changer",
    "touch base", "circle back", "as an ai", "certainly!", "great question", "i'd be remiss", "hope you're doing well and",
    # read as a template by professionals in an audit of real drafts
    "stood out to me", "made me smile", "builder's mindset", "whatever you can spare",
    "if your calendar allows", "would be wonderful", "eager to contribute", "exactly the experience",
    "the world i live in", "journey", "beats reading", "side of the table", "i know i'm early", "only a sophomore",
    "only a freshman", "no pressure if things are busy", "a firm like yours", "i'm writing anyway",
    "nowhere near the same", "everything i know is secondhand",
    # checklist transitions ("we both like X, so I was glad to see...") that make the hook feel mechanical
    "is someone i'd like to hear from", "so it was good to see", "so that line caught my eye", "so i was glad to see",
    "is something we share", "we have in common", "have a few things in common", "jumped out at me",
    # sounding unsure about your own field costs the call: state the interest, don't debate it
    "than an email", "than typed", "out loud", "than guess at it", "fits me", "fit for me", "still deciding",
    "still working out", "still figuring out", "i belong", "haven't worked in",
    # narrating your reaction or grading how they told a story reads robotic in a reply
    "made me laugh", "i love that", "i love how", "so true", "is a great way to", "great way to show",
    "show what you mean", "thanks for sharing", "thank you for sharing", "appreciate you taking the time to share",
    "resonated", "what a great story", "absolutely!",
]
PLACEHOLDER = re.compile(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>|\bTODO\b|\bTBD\b|\bXXX\b|lorem|\bWINDOW\s*\d\b|"
                         r"\bFIRST[ _]?NAME\b|\bSLOT\s*\d\b|PLACEHOLDER", re.I)
NUMBER = re.compile(r"(?<![A-Za-z])\$?\d[\d,.]*\+?%?x?")
DATE_OR_TIME = re.compile(
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?"
    r"|\d{1,2}(?::\d{2})? ?(?:am|pm|a\.m\.|p\.m\.)|\d{1,2}/\d{1,2}(?:/\d{2,4})?", re.I)
YEAR = re.compile(r"^20[2-3]\d$")  # internship year and class year are context, not stats
SENTENCE = re.compile(r"[^.!?]+[.!?]")
SIGNOFF = re.compile(r"^\s*(?:--\s*$|thanks for your time|thank you for your time|thanks again|thanks so much|"
                     r"best regards|kind regards|warm regards|all the best|best,|best$|regards|sincerely|cheers)",
                     re.I | re.M)

FIRST_EMAIL_WORDS = (110, 180)
# Word ranges for every other draft "kind": too short reads cold, too long reads like a template.
KIND_WORDS = {
    "followup": (25, 90),
    "thankyou": (60, 110),
    "scheduling": (10, 80),   # confirming a time is one line plus "looking forward to it"
    "reply": (10, 140),       # short scheduling replies are fine
    "update": (25, 110),      # "I wanted to update you and let you know I applied for the X position"
    "request": (80, 140), "offer": (40, 90), "reconnect": (70, 120),
    # Mirror their register: when they write short and loose ("You bet!"), answer short and loose.
    # Use kind "riff" only for a reply to a short, casual message.
    "riff": (8, 45),
}
# The house style that earned replies: these plain lines repeat across a batch on purpose (each firm gets its
# own email, and nobody sees two). A 4-word run containing one of these may repeat.
HOUSE_PHRASES = ("hope your week", "week has been going", "has been going well", "with a strong interest",
                 "strong interest in", "pick your brain", "learn more from your", "more from your experience",
                 "be open to a", "open to a 15", "a 15 minute call", "15 minute call sometime", "minute call sometime next",
                 "call sometime next week", "thanks for your time", "grateful for a quick", "for a quick chat",
                 "in the coming weeks", "if you have time", "would love to pick", "love to pick your", "call with you to",
                 "hop on a call", "love to hop on", "on a call with", "a call with you", "to hop on a", "would you be open",
                 "you be open to", "i'm a current", "a current student", "current freshman at", "current sophomore at",
                 "current junior at", "current senior at")
# House sentences: any 4-word run inside one of these may repeat across a batch.
HOUSE_SENTENCES = ("hope your week has been going well", "hope you had a great weekend",
                   "i would love to pick your brain and learn more from your experience",
                   "would you be open to a 15 minute call sometime next week",
                   "if you have time in the coming weeks i'd be grateful for a quick call",
                   "i would love to hop on a call with you and hear more about your experience",
                   "would you be open to a quick call sometime in the next couple of weeks")
STANDINGS = ("freshman", "sophomore", "junior", "senior", "first-year", "second-year", "third-year", "fourth-year",
             "graduate student", "student", "master's student", "mba student")
COMMON = set("i a an the to of and in on for at is it you your my me we that this with be have i'd i'm would if as or".split())
SELLING = [r"\bi know (the|how|what|best|this|that)\b", r"\bknow best\b", r"\bso i know\b", r"\bi've seen how\b",
           r"\bfirsthand\b", r"\bwhere i've built\b", r"\bwhat i (know|follow)\b", r"\bin my model\b",
           r"\bi understand (the|how|what)\b", r"\bmy experience\b", r"\bi(?:'m| am) (experienced|skilled|well[- ]versed)\b",
           r"\bi bring\b", r"\bi can (add|help|contribute)\b", r"\bvalue to (your|the) team\b", r"\btrack record\b",
           r"\bi've worked on\b", r"\bpart i know\b", r"\bnumber i know\b", r"\bi'm (great|strong) at\b",
           r"\bi(?:'m| am) an expert\b", r"\bexpertise in\b"]
APPLICATION_WORDS = re.compile(r"\b(appl(y|ying|ied|ication)s?|summer analyst|summer associate|internships?|"
                               r"(intern|internship|analyst|rotational|leadership) program|recruit\w*|job shadow|hiring|"
                               r"role (is|gets) posted)\b", re.I)
SUBJECT_ASK = re.compile(r"\b(chat|call|coffee|internship|opportunity|question)\b", re.I)
WARM_KINDS = ("reply", "riff", "scheduling", "thankyou")
BAN_LINE = re.compile(r"^\s*(?:[-*]\s*)?(?:\[?\d{4}-\d{2}-\d{2}\]?\s*[:\-]?\s*)?BAN\s*:\s*(.+?)\s*$", re.I)
FIRM_SLOT = re.compile(r"[\{\[<]\s*firm\s*[\}\]>]", re.I)

_profile_cache = {}


def norm(s):
    """Lowercase, straight apostrophes, words only: the form every phrase comparison uses."""
    s = (s or "").lower().replace("’", "'").replace("‘", "'")
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", s).split())


def _clean_phrase(p):
    p = p.strip()
    q = re.match(r"""^["'“‘](.+?)["'”’]""", p)
    if q:
        return q.group(1).strip().lower()
    p = re.split(r"\s+\(|\s+--\s+|\s+—\s+|\s+-\s+|\s+because\s+", p)[0]
    return p.strip().strip(".,").lower()


def profile_rules():
    """The user's own rules from me/profile.md and me/lessons.md (empty when not set up yet)."""
    key = str(C.ME)
    if key in _profile_cache:
        return _profile_cache[key]
    prof = {}
    if (C.ME / "profile.md").exists():
        try:
            prof = C.load_profile()
        except SystemExit:
            prof = {}
    banned = [(_clean_phrase(p), "never_say in me/profile.md") for p in C.as_list(prof.get("never_say"))]
    lessons = C.ME / "lessons.md"
    if lessons.exists():
        for line in lessons.read_text(encoding="utf-8").splitlines():
            m = BAN_LINE.match(line)
            if m:
                banned.append((_clean_phrase(m.group(1)), "BAN in me/lessons.md"))
    banned = [(p, why) for p, why in banned if p]
    interest = [FIRM_SLOT.sub("{firm}", x) for x in C.as_list(prof.get("interest_line"))]
    house = [norm(x) for x in C.as_list(prof.get("house_phrases")) if norm(x)]
    school = prof.get("school") if isinstance(prof.get("school"), str) else ""
    standing = prof.get("standing") or prof.get("class_standing") or ""
    if school:
        for st in ([standing] if isinstance(standing, str) and standing else []) + list(STANDINGS):
            house.append(norm(f"i'm a current {st} at {school} with a strong interest in"))
    items = [norm(x) for x in C.as_list(prof.get("resume_items")) if norm(x)]
    rules = {"banned": banned, "interest": interest, "house": house, "resume_items": items}
    _profile_cache[key] = rules
    return rules


def house_sentences(firms):
    """Universal house sentences + the user's own, with the interest line filled in for every firm in the batch."""
    rules = profile_rules()
    out = [norm(h) for h in HOUSE_SENTENCES] + rules["house"]
    for line in rules["interest"]:
        out += [norm(part) for part in line.split("{firm}") if len(norm(part).split()) >= 2]
        out += [norm(line.replace("{firm}", f)) for f in firms if f]
    return out


_house_cache = {}


def house_grams(firms):
    """Every 4-word run allowed to repeat: runs inside a house sentence, plus runs that straddle two house sentences
    written back to back ("...going well. I'm a current...")."""
    key = (str(C.ME), frozenset(firms))
    if key not in _house_cache:
        sents = [s.split() for s in house_sentences(firms)]
        grams = set()
        for w in sents:
            grams.update(" ".join(w[i:i + 4]) for i in range(len(w) - 3))
        for a in sents:
            for b in sents:
                w = a[-3:] + b[:3]
                grams.update(" ".join(w[i:i + 4]) for i in range(len(w) - 3))
        _house_cache[key] = grams
    return _house_cache[key]


def body_without_signoff(body):
    m = SIGNOFF.search(body or "", 1)
    return body[:m.start()] if m else (body or "")


def _phrase_re(p):
    return re.compile(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])")


def check(draft, name):
    """Checks one draft on its own. Returns a list of plain-English problems (empty = passes)."""
    errs = []
    rules = profile_rules()
    body, subject, to = draft.get("body", "") or "", draft.get("subject", "") or "", draft.get("to", "") or ""
    kind = draft.get("kind") or "first"
    first = kind == "first"
    text = subject + "\n" + body
    for ch, label in BANNED_CHARS.items():
        if ch in text:
            errs.append(f"contains {label}")
    low = text.lower().replace("’", "'").replace("‘", "'")
    for tell in AI_TELLS:
        if tell in low and not (tell == "leverage" and "leveraged finance" in low):
            errs.append(f'AI-tell phrase "{tell}"')
    for phrase, why in rules["banned"]:
        if _phrase_re(phrase).search(low):
            errs.append(f'banned phrase "{phrase}" ({why})')
    ph_text = text.replace(draft.get("firm", "") or "@@nofirm@@", " ")  # a firm literally named "TBD ..." is fine
    m = PLACEHOLDER.search(ph_text)
    if m:
        errs.append(f'leftover placeholder "{m.group(0)}"')
    if re.search(r"^(Hi|Hello|Dear) there\b", body, re.M):
        errs.append('generic greeting "Hi there"')
    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", to, re.I):
        errs.append(f"bad address {to!r}")
    # The greeting's first name should show up in the address (unless it's a team inbox like recruiting@).
    m = re.match(r"(?:Hi|Hello|Dear) ([A-Z][a-z]+)\b", body)
    local = to.split("@")[0].lower()
    team = any(w in local for w in ("recruit", "career", "campus", "talent", "early", "hr", "intern", "info", "admin"))
    last = (draft.get("name") or "").split()[-1].lower() if (draft.get("name") or "").split() else ""
    if m and not team and m.group(1).lower()[:1] != local[:1] and m.group(1).lower() not in local \
            and not (last and last in local):
        errs.append(f"greeting name {m.group(1)} doesn't match address {to}")
    firm = draft.get("firm", "") or ""
    if firm and first and firm.split()[0].lower() not in low:
        errs.append(f"firm name {firm!r} never mentioned")
    # One number in a first email is context. Two or more reads like a résumé recap (stat stacking).
    no_dates = DATE_OR_TIME.sub(" ", body_without_signoff(body))
    nums = [n for n in NUMBER.findall(no_dates) if not YEAR.match(n.strip(".,"))]
    if first and draft.get("thread_type") != "application" and len(nums) > 1:
        errs.append(f"stat stacking: {len(nums)} numbers {nums}")
    if first:
        words = len(body.split())
        lo, hi = FIRST_EMAIL_WORDS
        if not lo <= words <= hi:
            errs.append(f"{words} words (want {lo}-{hi})")
        if not subject or len(subject) > 60:
            errs.append("subject missing or over 60 characters")
        # Naming the application in a first email makes the call feel transactional. The posting lives in the
        # draft's "application" field for tracking only. (thread_type "application" is the deliberate exception.)
        m2 = None if draft.get("thread_type") == "application" else APPLICATION_WORDS.search(body)
        if m2:
            errs.append(f'mentions the application ("{m2.group(0)}"), keep it out of the first email')
        if draft.get("thread_type") != "application" and ("?" in subject or SUBJECT_ASK.search(subject)):
            errs.append("subject contains an ask (the subject is the shared thread only)")
    attaching = draft.get("attach", "resume") not in (None, "", "none", False)
    if not attaching and re.search(r"\b(attached|attaching|enclosed)\b", body, re.I):
        errs.append("says something is attached but no résumé is attached")
    if kind in KIND_WORDS:
        lo, hi = KIND_WORDS[kind]
        words = len(body.split())
        if not lo <= words <= hi:
            errs.append(f"{words} words for a {kind} (want {lo}-{hi})")
    for para in body.strip().split("\n\n"):
        lines = para.split("\n")
        if len(lines) > 1 and not lines[0].rstrip().endswith(",") and not para.startswith("--"):
            errs.append("hard line break inside a paragraph")
            break
    if body.count("?") > 2:
        errs.append("more than two questions (one ask per email)")
    # Learned from real replies: if it's obvious you're selling yourself, you won't sell. No expertise claims.
    blow = body.lower().replace("’", "'")
    for p in SELLING:
        m = re.search(p, blow)
        if m:
            errs.append(f'sells yourself ("{m.group(0)}"): drop the claim, mention your own work only as plain context')
            break
    m = re.search(r"(i've|i have|i am|i'm) (been )?building", blow)
    if m:
        errs.append(f'"{m.group(0)}" sounds like hustling without results; state it plainly, in the past tense')
    # In a first email a direct question followed by a call ask reads like you only want the call for that answer.
    # State the curiosity and make the call about getting to know them.
    if first and "?" in body:
        errs.append("first email asks a direct question; state the curiosity instead (no question marks)")
    # Don't overcorrect into self-deprecation either.
    m = re.search(r"(my )?(small|little|tiny|humble|modest) (tool|project|app|company|business|startup|side project)"
                  r"|just a (small |little )?(tool|project|app|startup)", blow)
    if m:
        errs.append(f'downplays your own work ("{m.group(0)}"); describe it plainly, no shrinking adjectives')
    hits = [i for i in rules["resume_items"] if _phrase_re(i).search(norm(body))]
    if first and len(hits) > 1:
        errs.append(f"lists résumé items ({', '.join(hits)}); mention one at most, plainly")
    if kind == "reply" and len(hits) >= 2:  # they already have the résumé: answer with motivation, not accomplishments
        errs.append(f"reply restates the résumé ({', '.join(hits)})")
    return errs


def cross_checks(drafts):
    """Batch checks over [(name, draft), ...]: the same sentence in two emails is a giveaway (especially to people
    at the same firm), and the same 4-word run in more than 30% of a batch (min 3) reads as a template."""
    seen = defaultdict(list)
    for name, d in drafts:
        for s in SENTENCE.findall(body_without_signoff(d.get("body", "") or "")):
            key = norm(s)
            if len(key.split()) >= 8:
                seen[key].append(name)
    errs = defaultdict(list)
    if len(drafts) >= 5:
        house = house_grams({(d.get("firm") or "") for _, d in drafts})
        grams = defaultdict(set)
        for name, d in drafts:
            words = norm(body_without_signoff(d.get("body", "") or "")).split()[3:]  # skip the greeting
            for i in range(len(words) - 3):
                g = " ".join(words[i:i + 4])
                if not all(w in COMMON for w in g.split()):
                    grams[g].add(name)
        limit = max(3, int(len(drafts) * 0.3))
        for g, names in grams.items():
            if len(names) > limit and g not in house and not any(p in g for p in HOUSE_PHRASES):
                for n in names:
                    errs[n].append(f'phrase "{g}" appears in {len(names)} of {len(drafts)} emails')
    for key, names in seen.items():
        if len(set(names)) > 1:
            for n in set(names):
                errs[n].append(f'sentence reused in {len(set(names))} emails: "{key[:60]}..."')
    return errs


def load(folder):
    folder = Path(folder)
    files = [folder] if folder.is_file() else sorted(folder.glob("*.json"))
    return [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in files]


def run(folder):
    """Gate every *.json in folder. Returns (drafts, failed) where failed = {file name: [problems]}."""
    drafts = load(folder)
    shared = cross_checks(drafts)
    failed = {}
    for name, d in drafts:
        errs = check(d, name) + shared.get(name, [])
        if errs:
            failed[name] = errs
    return drafts, failed


def resolve(arg):
    p = Path(arg)
    for c in ([p] if p.is_absolute() else [Path.cwd() / p, C.ROOT / p, C.DATA / p, C.DRAFTS / p]):
        if c.exists():
            return c
    sys.exit(f"Not found: {arg} (looked in the current folder, the repo, data/ and data/drafts/)")


def main():
    sys.stdout.reconfigure(errors="replace")  # never crash printing a name the console can't show
    ap = argparse.ArgumentParser(description="Pre-send gate: checks drafts against the universal writing rules plus "
                                             "your me/profile.md never_say list and me/lessons.md BAN: lines.")
    ap.add_argument("folder", nargs="?", help="folder of draft JSON files, or one file (default: data/approved)")
    a = ap.parse_args()
    folder = resolve(a.folder) if a.folder else C.APPROVED
    drafts, failed = run(folder)
    for name, errs in failed.items():
        print(f"FAIL {name}")
        for e in errs:
            print(f"   - {e}")
    print(f"\n{len(drafts) - len(failed)}/{len(drafts)} passed the gate.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
