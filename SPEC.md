# martha-networking: design spec

A repo any student clones to run a full networking system: find the right people, find their real published email,
write the email the way that has earned replies, send safely from their own Gmail, catch replies and bounces, follow
up, prep calls, and learn from results. It runs inside **Claude Code** (the AI does the research and writing through
subagents and skills; Python tools do the deterministic parts). Works for ANY major and field (finance, accounting,
consulting, engineering, marketing, pre-law, healthcare...). It was distilled from one student's real outreach
(about 250 cold emails and their replies); see knowledge/RESULTS.md for the aggregate numbers.

## PRIVACY (hard rule for every contributor)
Nothing personal goes in the repo: no names of real people emailed, no email addresses, no reply text, no config.env,
no Gmail password, no résumé, no user facts. Example emails are anonymized (fake names like "Dana Reyes", fake firms
like "Northgate Partners") while keeping the structure that worked. Grep the repo for leaks before every release.

## Layout
```
martha-networking/
  README.md            friend-facing: what it does, 20-minute setup, daily routine, safety rules, FAQ
  CLAUDE.md            Claude Code operating manual: the workflow, the hard rules, which skill does what
  SPEC.md              this file (keep)
  requirements.txt     requests, pymupdf, matplotlib
  .gitignore           me/, data/, *.env, __pycache__/, *.pyc
  me.example/          the user copies this to me/ (gitignored) and fills it in
    profile.md         who they are: name, school, class year, major, field + target roles, interests, story
                       facts (ONLY true facts they wrote), what to never say, résumé file name, interest line
    strategy.md        their targets: fields, firm list by tier, application windows, per-firm cap (default 3)
    lessons.md         their own rulings (starts empty; tools/capture.py appends)
    availability.json  weekly recurring busy blocks + call window, e.g. {"window":[8,17],"tz":"America/New_York",
                       "recurring":[{"days":["Tue","Thu"],"start":"15:00","end":"16:30","label":"class"}],
                       "one_off":[{"date":"2026-10-16","start":"14:00","end":"14:45","label":"call"}]}
    config.env.example GMAIL_ADDRESS=, GMAIL_APP_PASSWORD= (they create an app password themselves), DAILY_CAP=40
    resume/README.md   "put your PDF here"
  knowledge/           shared, field-agnostic knowledge Martha reads before every task
    PLAYBOOK.md        how first emails are written (the winning structure, subject format, length, banned words,
                       one-claim rule, no selling, credit deals/work correctly, hooks of THEIRS), with anonymized examples
    WINNING-EMAILS.md  6 anonymized real winners (4 banker calls/referrals, 2 advisor replies) + why each worked
    RESEARCH.md        how to pick firms and people (application windows, 3 per firm: 1 recruiter + 2 in-group,
                       alumni first), published-email-only rule, still-at-firm proof, hook research, JSON schema
    STRATEGY.md        network backward from application dates; the three asks on every call; the update email
                       after applying; follow-up timing (4 days no reply = no reply; follow-up 1 at day 7, 2 at day 14)
    REPLIES.md         replying: mirror their register, scheduling (one simple availability range, assistants),
                       referrals (thank + bcc + write the new person), declines, thank-you after a call
    CALL-PREP.md       one-page call-prep template
    RESULTS.md         what the data said (anonymized aggregate: 244 delivered, 9.4% replied, bankers 4.6%, advisors
                       18%, all replies within 43 hours, pattern-guessed emails bounced 13% vs 0.5% printed)
  .claude/
    agents/martha.md      the writer (networking only): reads me/profile.md, me/lessons.md, knowledge/*, data/
                          examples; never invents; drafts JSON into data/drafts/<batch>/
    agents/researcher.md  finds people + published emails per knowledge/RESEARCH.md, writes data/research/<batch>/*.json
    skills/<name>/SKILL.md one per command below
  tools/               Python 3.10+, stdlib + requests/pymupdf/matplotlib. Every tool: `python tools/<x>.py --help`.
    config.py          ROOT, ME, DATA paths; load_profile() (parses me/profile.md front matter), load_env(), load_availability()
    verify_addresses.py  re-fetch source page, confirm the exact address (HTML, PDF, Cloudflare data-cfemail, ROT13),
                         confirm bio still names the person; writes address_check {status, detail, checked_at}
    gate.py            pre-send checks. UNIVERSAL rules (no placeholders, no semicolons/em dashes in first emails, word
                       ranges per kind, banned AI-tell phrases, no "I'm reaching out", no expertise claims, no question
                       marks in first emails, batch 4-gram repeat limit int(n*0.3)) + PROFILE rules (house phrases from
                       the profile's interest line, "never say" list, facts-that-must-not-appear) + me/lessons.md bans
    send_approved.py   sends everything in data/approved/ via Gmail SMTP (app password), threading (reply_to,
                       in_reply_to), resume attachment from me/resume/, guards: published-only + fresh address_check
                       (<=3 days) for first emails, no double email, per-firm cap from strategy (default 3 people ever),
                       max 5 per firm per batch, daily cap, bounce guard (published-only window of 40: >3% -> cap 15,
                       >8% -> pause); --send to actually send (default dry run); --delay seconds between emails
    run_send_day.py    chunks of 8 into approved/, send with retries when offline, check bounces between chunks
                       (check_replies with timeout 180), stop on first bounce
    check_replies.py   IMAP: finds replies and bounces from people in data/sent/, saves reply text to data/replies/,
                       appends to data/outcomes.jsonl ("replied"/"bounce"), skips already logged
    outcomes.py        label a reply: `python tools/outcomes.py label <sent-file> call|referral|replied|declined|ooo "note"`
    digest.py          the morning command: runs check_replies, prints replies to answer, follow-ups due (day 7 and
                       day 14 after the first email with no reply), send room left, bounce health, drafts waiting
    results.py         response rates overall / by segment / by thread / by day; lessons when n>=30 and z>=2;
                       broad regexes (learned the hard way: match every phrasing)
    availability.py    PNG of open times for N weeks from me/availability.json (+ --busy extra blocks)
    capture.py         `python tools/capture.py note "<ruling>"` appends a dated ruling to me/lessons.md
  data/                gitignored: research/, drafts/, approved/, sent/, replies/, outcomes.jsonl
```

## Draft JSON (data/drafts/<batch>/<firm>-<lastname>.json)
```json
{"to":"","subject":"","body":"","firm":"","name":"","kind":"first|followup|reply|thankyou|scheduling",
 "practice":"<Firm>:<Name>","attach":"resume|none","reply_to":"<sent file name, for followups/replies>",
 "in_reply_to":"<Message-ID they sent, optional>","cc":"",
 "email_confidence":"published","email_source_url":"","address_check":{"status":"verified","detail":"","checked_at":""},
 "application":{"title":"","url":"","est_open":""},
 "call_prep":{"title":"","seniority":"","why_them":"","questions":[]},
 "research":{"findings":[],"hook_used":""}}
```
Sent records = the draft + sent_at + message_id, saved to data/sent/<same name>.

## Skills (Claude Code, .claude/skills/<name>/SKILL.md, user types /<name>)
- `onboard` : interview the user (major, school, year, field, target roles, interests, story facts, never-say), write
  me/profile.md, me/strategy.md, me/availability.json; walk them through creating a Gmail app password (they type it
  into me/config.env themselves; Claude never sees or stores it); test with `python tools/send_approved.py` dry run.
- `find-contacts [n] [focus]` : plan firms from me/strategy.md (application windows, cap 3 per firm), launch researcher
  subagents in parallel (published emails only, still-at-firm proof, hook of theirs), then run verify_addresses.py.
- `draft [batch]` : launch the martha subagent on verified research; gate the batch; show the user 3 samples.
- `send-day [batch]` : on the user's explicit "send": verify again, order chunks so each passes the gate, run_send_day.py.
- `check-replies` : digest.py; label each new reply with outcomes.py; draft responses with martha (never send without OK).
- `follow-ups` : draft day-7 / day-14 follow-ups for no-replies (new small real thing, no guilt, ask restated plainly).
- `reply <who>` : draft a reply to one thread using knowledge/REPLIES.md and me/availability.json.
- `call-prep <who>` : one-page sheet from knowledge/CALL-PREP.md into data/call-prep/.
- `results` : results.py + update me/lessons.md with any n>=30 lesson; suggest what to change.
- `update-after-apply <firm>` : the "I wanted to update you and let you know I applied for the <X> position" email to every contact at that firm.

## Hard rules (put verbatim in CLAUDE.md and martha.md)
1. Never send anything without the user's explicit "send" for that batch or reply.
2. Only email addresses printed on a live public page and re-verified within 3 days. Never guess a pattern.
3. Max 3 people per firm, ever, unless the user changes me/strategy.md.
4. Never invent a fact about the user or the recipient. Only me/profile.md facts and sourced findings.
5. Never handle passwords: the user types their Gmail app password into me/config.env themselves.
6. Each user's data stays in me/ and data/ (gitignored). Never commit them.
