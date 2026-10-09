"""Save the user's rulings so Martha and the gate follow them from now on.

    python tools/capture.py note "<ruling>"   appends "- YYYY-MM-DD <ruling>" to me/lessons.md (Martha reads it)
    python tools/capture.py ban "<phrase>"    appends "BAN: <phrase>" to me/lessons.md (gate.py blocks drafts using it)

Write the ruling in the user's own words, with a short example when it helps:
    python tools/capture.py note "one shared interest per email, not two"
    python tools/capture.py ban "I'd love to pick your brain"
The same ruling or phrase is never saved twice.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def _lessons():
    if not config.ME.exists():
        sys.exit("No me/ folder yet. Copy me.example/ to me/ (or run /onboard in Claude Code) first.")
    p = config.ME / "lessons.md"
    return p, (p.read_text(encoding="utf-8") if p.exists() else "")


def _append(p, text, line):
    p.write_text(text + ("" if not text or text.endswith("\n") else "\n") + line + "\n", encoding="utf-8")


def _norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def note(ruling):
    ruling = " ".join(ruling.split())
    if not ruling:
        sys.exit("Nothing to save: give the ruling in quotes.")
    p, text = _lessons()
    have = {_norm(re.sub(r"^\s*-\s*\d{4}-\d{2}-\d{2}\s*", "", l)) for l in text.splitlines()}
    if _norm(ruling) in have:
        return "Already in me/lessons.md."
    _append(p, text, f"- {dt.date.today()} {ruling}")
    return "Saved to me/lessons.md."


def ban(phrase):
    phrase = " ".join(phrase.split()).strip("\"'")
    if not phrase:
        sys.exit("Nothing to ban: give the phrase in quotes.")
    p, text = _lessons()
    have = {_norm(m.group(1)) for m in re.finditer(r"BAN\s*:\s*(.+?)\s*$", text, re.M | re.I)}
    if _norm(phrase) in have:
        return "Already banned."
    _append(p, text, f"BAN: {phrase}")
    return f'Banned "{phrase}". The gate now blocks any draft that uses it.'


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("note", help="save a dated ruling")
    n.add_argument("text", nargs="+")
    b = sub.add_parser("ban", help="ban a phrase")
    b.add_argument("text", nargs="+")
    args = ap.parse_args(argv)
    print((note if args.cmd == "note" else ban)(" ".join(args.text)))


if __name__ == "__main__":
    main()
