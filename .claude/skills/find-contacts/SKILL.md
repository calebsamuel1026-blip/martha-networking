---
name: find-contacts
description: Research a new batch of people to email. Use when the user says /find-contacts, "find people", "find contacts", "who should I email next", or wants more outreach volume. Plans firms from me/strategy.md (application windows, per-firm cap), writes a shared brief, launches several researcher subagents in parallel (published emails only, still-at-firm proof, a hook of theirs), enforces the cap, then runs verify_addresses.py. Sends nothing.
argument-hint: "[n=30] [focus, e.g. recruiters | alumni | <firm> | <field>]"
---
# /find-contacts [n] [focus]

Arguments: `$ARGUMENTS`. `n` is the number of new people wanted (default 30). `focus` is optional free text: a firm, a
tier, a field, "recruiters", or "alumni".

## Steps

1. **Read the plan.** Read `me/strategy.md` (firms by tier, application windows, `max people per firm`, any firm
   marked applied), `me/profile.md` (school, major, year, field and target roles, and the interests usable as
   commonalities), `knowledge/RESEARCH.md` and `knowledge/STRATEGY.md`. If `me/profile.md` is missing, stop and run
   `/onboard` first.

2. **Name the batch.** `<YYYY-MM-DD>-<short-focus-slug>`, for example `2026-10-14-audit-tier1`. Add `-b` or `-c` if
   that name exists. The batch folder is `data/research/<batch>/`.

3. **Build the skip lists.** Write the script below to `data/research/<batch>/_contacts.py` and run it from the repo
   root:
   ```
   python data/research/<batch>/_contacts.py lists <batch>
   ```
   It writes `_domains-already-emailed.txt` (each firm domain already emailed, people emailed, slots left under the
   cap) and `_already-contacted.txt` (every name and address already sent, drafted or researched). Pending drafts
   count against the cap too.
   ```python
   import collections, glob, json, re, shutil, sys
   from pathlib import Path

   mode, batch_name = sys.argv[1], sys.argv[2]
   batch = Path("data/research") / batch_name
   batch.mkdir(parents=True, exist_ok=True)
   cap = 3
   s = Path("me/strategy.md")
   if s.exists():
       m = re.search(r"max people per firm\s*:\s*(\d+)", s.read_text(encoding="utf-8"), re.I)
       if m:
           cap = int(m.group(1))
   FREE = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com", "me.com", "live.com",
           "proton.me", "protonmail.com"}


   def load(f):
       try:
           return json.load(open(f, encoding="utf-8"))
       except Exception:
           return {}


   def key(addr, firm):  # firm key: email domain, or firm name for personal addresses
       dom = addr.split("@")[-1]
       return dom if dom and dom not in FREE else "firm:" + (firm or "").strip().lower()


   emailed = collections.defaultdict(set)  # firm key -> addresses already emailed or drafted (first emails)
   label, seen = {}, set()
   for f in glob.glob("data/sent/*.json") + glob.glob("data/drafts/*/*.json"):
       if Path(f).parent == Path("data/drafts") / batch_name:
           continue
       d = load(f)
       to = (d.get("to") or "").strip().lower()
       if not to:
           continue
       seen.update({to, (d.get("name") or "").strip().lower()})
       if d.get("kind", "first") == "first":
           k = key(to, d.get("firm"))
           emailed[k].add(to)
           label[k] = d.get("firm", "")
   for f in glob.glob("data/research/*/*.json"):
       if Path(f).parent == batch:
           continue
       d = load(f)
       seen.update({(d.get(x) or "").strip().lower() for x in ("email", "name")})
   seen.discard("")

   if mode == "lists":
       rows = [f"{k}\t{label[k]}\t{len(a)} emailed\t{max(cap - len(a), 0)} slots left" for k, a in sorted(emailed.items())]
       (batch / "_domains-already-emailed.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
       (batch / "_already-contacted.txt").write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")
       full = sum(1 for a in emailed.values() if len(a) >= cap)
       print(f"cap {cap}: {len(emailed)} firms already emailed, {full} at cap, {len(seen)} names/addresses to skip")

   elif mode == "check":
       drop_dir = Path("data/research/_dropped") / batch_name
       kept, dropped, new, mine = [], [], collections.defaultdict(list), set()
       files = sorted(p for p in batch.glob("*.json") if not p.name.startswith("_"))
       for p in files:
           d = load(p)
           addr = (d.get("email") or "").strip().lower()
           why = ""
           if not addr or d.get("email_confidence") != "published" or not d.get("email_source_url"):
               why = "not a published address with a source URL"
           elif addr in seen or (d.get("name") or "").strip().lower() in seen:
               why = "already contacted, drafted or researched"
           elif addr in mine:
               why = "duplicate inside this batch"
           if why:
               dropped.append((p, why))
               continue
           mine.add(addr)
           new[key(addr, d.get("firm"))].append((p, d))
       for k, items in new.items():
           room = max(cap - len(emailed.get(k, ())), 0)
           items.sort(key=lambda x: (not x[1].get("alum"), x[1].get("seniority") != "recruiter"))
           kept += [p for p, _ in items[:room]]
           dropped += [(p, f"over the per-firm cap ({cap}) at {k}") for p, _ in items[room:]]
       for p, why in dropped:
           drop_dir.mkdir(parents=True, exist_ok=True)
           shutil.move(str(p), str(drop_dir / p.name))
           print(f"DROPPED {p.name}: {why}")
       print(f"kept {len(kept)}, dropped {len(dropped)} (moved to {drop_dir})")
   ```

4. **Pick the firms.** Network backward from application dates (`knowledge/STRATEGY.md`):
   - First, firms whose student application opens in the next 3 to 8 weeks. Then firms that are open now. Then the
     next wave.
   - Skip firms with 0 slots left, firms marked applied in `me/strategy.md` (they get `/update-after-apply`, not new
     cold emails), and firms with no student program.
   - Aim for about `n / 3` firms with full room, and fewer people at firms with only 1 or 2 slots left. Apply
     `focus` if given.
   - Split the firms into **3 to 5 lanes** of about 8 to 10 people each. **No firm appears in two lanes.** Give
     each lane a clear angle, for example "Lane A: tier-1 firms opening next month", "Lane B: tier-2 firms open
     now", "Lane C: alumni of <school> at any target firm not in lanes A or B", "Lane D: campus recruiters".

   Show the user the lane plan in a few lines (lane, firms, people wanted) and go on unless they object.

5. **Write the shared brief** to `data/research/<batch>/_BRIEF.md`. Use this template, filled in from the files
   above, with no guesses:
   ```markdown
   # Research brief: <batch> (<date>)

   ## Goal
   <n> new people at the firms below, for <target roles / summers from me/strategy.md>. Per firm: 1 recruiter or
   campus lead plus 2 people in the group the user would join. Alumni of <school> first.

   ## The user (for finding commonalities only; never put this in a JSON as a fact about the contact)
   <school, major, class year, field and target roles, plus 3-6 interests or story facts from me/profile.md that
   the user OK'd for emails>

   ## Hard rules (drop the contact if any fails)
   1. Published own address on a live public page. Never a pattern. Cite email_source_url and email_as_printed.
   2. Still at the firm today (live bio, or a source from this year or last year), in still_at_firm_evidence.
   3. A specific hook of THEIRS with a source URL (deal or project, saying whether they LED it or were on the team,
      a quote, an article, podcast, panel, or bio line). Generic firm facts don't count.
   4. Room at the firm: max <cap> people per firm EVER, counting people already emailed. Check
      _domains-already-emailed.txt for slots left. Skip any name or address in _already-contacted.txt.
   5. The firm hires students for these roles (program page, campus posting, or a recent intern on the team page).

   ## Lanes (one researcher each; stay in your lane)
   - Lane A: <firms, each with slots left> | angle: <...> | people wanted: <k>
   - Lane B: ...

   ## Limits
   WebSearch at most 30 per researcher, WebFetch unlimited. No browser, no logins, no LinkedIn profile pages. Send
   nothing. Schema and sourcing rules: knowledge/RESEARCH.md.

   ## Output
   One JSON per person: data/research/<batch>/<firmslug>-<lastname>.json (skip if the file already exists).
   Final reply under 150 words: name | firm | seniority | alum? | hook, then dropped and why.
   ```

6. **Launch the researchers in parallel.** Use one message with one Agent call per lane, all with
   `subagent_type: "researcher"`. Each prompt says: "Read data/research/<batch>/_BRIEF.md and knowledge/RESEARCH.md.
   You are Lane <X>: <firms and angle>. Find <k> people. Write JSON files to data/research/<batch>/." Wait for all
   of them.

7. **Enforce the rules on what came back.**
   ```
   python data/research/<batch>/_contacts.py check <batch>
   ```
   This moves anything without a published address, any repeat contact, and anyone over the per-firm cap into
   `data/research/_dropped/<batch>/` (alumni and recruiters are kept first). Open 2 or 3 of the kept JSONs and make
   sure each has a real `findings` item with a `source_url`.

8. **Verify every address against the live page.**
   ```
   python tools/verify_addresses.py data/research/<batch>
   ```
   This writes `address_check {status, detail, checked_at}` into each file. Only `verified` people go to `/draft`.
   For failures, read `detail`: a page that moved can be re-researched by one more researcher run, but never fix a
   failure by guessing an address.

9. **Report to the user.** Show a short table: name | firm | role | alum? | hook (one line) | check. Then say how many
   were verified, how many were dropped and why, and the slots still open per firm. End with the next step:
   `/draft <batch>`.
