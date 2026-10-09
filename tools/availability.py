"""PNG of your open call times, to attach when someone asks "when works for you?".

    python tools/availability.py 2026-10-19                    one week (any date in it; snaps to that Monday)
    python tools/availability.py 2026-10-19 2026-10-26         those weeks side by side
    python tools/availability.py 2026-10-19 --weeks 3          3 weeks starting there
    python tools/availability.py                               this week and next (next two if it's the weekend)
    python tools/availability.py 2026-10-19 --busy 2026-10-21 12:00-12:45    plus extra busy blocks (repeatable)

Reads me/availability.json:
  {"window": [8, 17], "tz": "America/New_York", "weekends": false,
   "recurring": [{"days": ["Tue", "Thu"], "start": "15:00", "end": "16:30", "label": "class"},
                 {"days": ["Wed"], "start": "13:15", "end": "14:15", "every_other": true, "anchor": "2026-10-14",
                  "from": "2026-10-14", "until": "2026-12-09", "label": "1:1"}],
   "one_off": [{"date": "2026-10-16", "start": "14:00", "end": "14:45", "label": "call"}]}
  every_other: the block happens every second week, on the weeks of its anchor date (a day it does happen).
  from / until: optional date limits for a recurring block. Blocks are clipped to the window.
Labels stay private: the picture only says "Busy". Title: "<your name> | Availability for a call".
Saves data/availability-<first Monday>.png.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

DAY_NAMES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
TZ_LABEL = {"America/New_York": "Eastern", "America/Detroit": "Eastern", "America/Chicago": "Central",
            "America/Denver": "Mountain", "America/Phoenix": "Arizona", "America/Los_Angeles": "Pacific",
            "America/Anchorage": "Alaska", "Pacific/Honolulu": "Hawaii"}
GREEN, GREY, INK, MUTED, LINE = "#cfe8d5", "#d9dde4", "#14213a", "#5b6679", "#ffffff"


def hours(x):
    """8, 8.5, "08:30", "8:30am", "3:05 PM" -> float hours."""
    if isinstance(x, (int, float)):
        return float(x)
    m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\s*", str(x), re.I)
    if not m:
        raise ValueError(f"can't read the time {x!r} (use \"15:30\")")
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ap.startswith("p") and h < 12:
        h += 12
    if ap.startswith("a") and h == 12:
        h = 0
    return h + mi / 60


def day_set(spec):
    out = set()
    for s in ([spec] if isinstance(spec, str) else spec or []):
        s = str(s).strip().lower()
        if s in ("weekdays", "weekday"):
            out |= {0, 1, 2, 3, 4}
        elif s in ("daily", "every day", "everyday", "all"):
            out |= set(range(7))
        elif s[:3] in DAY_NAMES:
            out.add(DAY_NAMES[s[:3]])
        else:
            raise ValueError(f"unknown day {s!r} (use Mon, Tue, ... or weekdays)")
    return out


def as_date(x):
    return dt.date.fromisoformat(str(x)[:10]) if x else None


def monday(d):
    return d - dt.timedelta(days=d.weekday())


def busy_on(day, avail, extra):
    """(start, end, label) blocks on this date."""
    out = []
    for r in avail.get("recurring") or []:
        if day.weekday() not in day_set(r.get("days") or r.get("day")):
            continue
        if (r.get("from") and day < as_date(r["from"])) or (r.get("until") and day > as_date(r["until"])):
            continue
        eo = r.get("every_other")
        if eo:
            anchor = as_date(eo if isinstance(eo, str) else r.get("anchor") or r.get("from"))
            if not anchor:
                raise ValueError(f"every_other block {r.get('label', '')!r} needs an \"anchor\" date (a day it happens)")
            if ((monday(day) - monday(anchor)).days // 7) % 2:
                continue
        out.append((hours(r["start"]), hours(r["end"]), r.get("label", "")))
    for o in list(avail.get("one_off") or []) + extra:
        if as_date(o.get("date")) == day:
            out.append((hours(o["start"]), hours(o["end"]), o.get("label", "")))
    return out


def parse_busy(date_s, span):
    m = re.fullmatch(r"\s*([^-]+?)\s*-\s*(.+?)\s*", span)
    if not m:
        raise ValueError(f"--busy wants DATE START-END, e.g. 2026-10-21 12:00-12:45 (got {span!r})")
    return {"date": str(as_date(date_s)), "start": m.group(1), "end": m.group(2), "label": "extra"}


def name_of():
    if not (config.ME / "profile.md").exists():
        return ""
    try:
        return str(config.load_profile().get("name") or "").strip()
    except SystemExit:
        return ""


def draw(weeks, avail, extra, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        sys.exit("matplotlib is missing: run `pip install -r requirements.txt`.")
    win = avail.get("window") or [8, 17]
    start_h, end_h = hours(win[0]), hours(win[1])
    if end_h <= start_h:
        sys.exit("me/availability.json: window end must be after its start, e.g. [8, 17].")
    ndays = 7 if avail.get("weekends") else 5
    fig, axes = plt.subplots(1, len(weeks), figsize=(max(9.0, 6.0 * len(weeks)), 7.0), dpi=200, squeeze=False)
    fig.patch.set_facecolor("white")
    for ax, w in zip(axes[0], weeks):
        days = [w + dt.timedelta(days=i) for i in range(ndays)]
        for i, d in enumerate(days):
            ax.add_patch(Rectangle((i, start_h), 1, end_h - start_h, facecolor=GREEN, edgecolor="none"))
            for s, e, _ in busy_on(d, avail, extra):
                s, e = max(s, start_h), min(e, end_h)  # only the part inside the window
                if s < e:
                    ax.add_patch(Rectangle((i, s), 1, e - s, facecolor=GREY, edgecolor="none"))
                    if e - s >= 0.4:
                        ax.text(i + 0.5, (s + e) / 2, "Busy", ha="center", va="center", fontsize=8, color=MUTED)
        ticks = list(range(int(-(-start_h // 1)), int(end_h) + 1))
        for h in ticks:
            ax.axhline(h, color=LINE, lw=1.2)
        for i in range(1, ndays):
            ax.axvline(i, color=LINE, lw=3)
        ax.set_xlim(0, ndays)
        ax.set_ylim(end_h, start_h)
        ax.set_xticks([i + 0.5 for i in range(ndays)])
        ax.set_xticklabels([f"{d:%a}\n{d:%b} {d.day}" for d in days], fontsize=10, color=INK)
        ax.xaxis.tick_top()
        ax.set_yticks(ticks)
        ax.set_yticklabels([f"{(h % 12) or 12} {'AM' if h % 24 < 12 else 'PM'}" for h in ticks], fontsize=9, color=MUTED)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(f"Week of {w:%B} {w.day}", fontsize=12, color=INK, pad=34, loc="left", fontweight="bold")
    name = name_of()
    fig.suptitle(f"{name} | Availability for a call" if name else "Availability for a call",
                 fontsize=15, color=INK, x=0.06, ha="left", y=0.985, fontweight="bold")
    tz = str(avail.get("tz") or "")
    note = avail.get("note") or (f"All times {TZ_LABEL.get(tz, tz) or 'local'}.   Happy to work around your schedule.")
    fig.text(0.06, 0.035, note, fontsize=10, color=MUTED, ha="left")
    fig.legend(handles=[Rectangle((0, 0), 1, 1, fc=GREEN), Rectangle((0, 0), 1, 1, fc=GREY)], labels=["Open", "Busy"],
               loc="upper left", ncol=2, frameon=False, fontsize=10, bbox_to_anchor=(0.055, 0.945))
    plt.tight_layout(rect=(0.03, 0.06, 0.99, 0.90))
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, facecolor="white")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dates", nargs="*", help="a date in each week to show (YYYY-MM-DD; snaps to Monday)")
    ap.add_argument("--weeks", type=int, help="number of consecutive weeks (default 2 with no date, 1 per date given)")
    ap.add_argument("--busy", nargs=2, action="append", default=[], metavar=("DATE", "START-END"),
                    help="an extra busy block, e.g. --busy 2026-10-21 12:00-12:45 (repeatable)")
    ap.add_argument("--out", help="output file (default data/availability-<first Monday>.png)")
    args = ap.parse_args(argv)
    try:
        starts = [monday(dt.date.fromisoformat(a)) for a in args.dates]
        extra = [parse_busy(d, s) for d, s in args.busy]
    except ValueError as e:
        sys.exit(str(e))
    if not starts:
        today = dt.date.today()
        starts = [monday(today) + dt.timedelta(days=7 if today.weekday() >= 5 else 0)]
        n = args.weeks or 2
    else:
        n = args.weeks if args.weeks and len(starts) == 1 else 1
    if n > 1:
        starts = [starts[0] + dt.timedelta(days=7 * i) for i in range(n)]
    weeks = sorted(dict.fromkeys(starts))
    avail = config.load_availability()
    if not (config.ME / "availability.json").exists():
        print("(no me/availability.json yet: showing the default 8-5 window with nothing busy)")
    out = Path(args.out) if args.out else config.DATA / f"availability-{weeks[0]}.png"
    try:
        draw(weeks, avail, extra, out)
    except (ValueError, KeyError) as e:
        sys.exit(f"me/availability.json problem: {e}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
