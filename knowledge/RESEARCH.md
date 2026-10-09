# How to pick firms and people, and find their real email

Good research is most of the result. Every call in the source system came from an email built on one specific thing the person did or said. Emails built on generic firm facts went 0 for 9. Guessed addresses bounced about 25 times as often as printed ones.

## 1. Pick firms by application window

Only network at a firm when there is a **dated application the user is eligible for**: a program, internship or early-insight event for their class year. No date yet means park the firm.

- Read `me/strategy.md` for the user's firms, tiers and windows.
- Start **3 to 8 weeks before the window opens**. `contact_by` = `est_open` minus 4 to 8 weeks. If that date has passed, use today.
- Once the user has applied somewhere, stop new outreach there. Their contacts get the update email (STRATEGY.md).
- **Skip firms that don't hire students.** Before emailing a firm, find proof it takes students for the user's roles: a program page, a campus posting, a careers page for students, or a 2025-26 intern or analyst on the team page. In the source data, small firms asked about roles answered "we don't hire interns" 4 times out of 4. Put the proof in `application`.

## 2. Pick people: 3 per firm, ever

The default cap is 3 (`max people per firm: 3` in `me/strategy.md`):

1. **One recruiter or campus lead.** The person who owns students for that office or school: campus recruiter, university relations, early careers, talent acquisition. The firm's careers page or a school's career-fair page often names them.
2. **Two people in the group the user would join.** Alumni of the user's school first, then people with a real overlap (same hometown region, language, sport, founder path), then senior people with a strong hook.

What "the group" means:

| Field | The group |
|---|---|
| Investment banking | the industry or product group in one office (healthcare, industrials, restructuring) |
| Accounting / Big 4 | the service line in one office (audit, tax, advisory), ideally the industry practice inside it |
| Consulting | the office the user would join (most firms hire by office), then a practice or industry area |
| Tech | the product area or team (payments, infrastructure, data platform), engineers and engineering managers |
| Marketing | the brand team or function (a product line's brand team, growth, communications) |
| Engineering | the division, site or project group |
| Healthcare | the department, unit or administrative fellowship |
| Law (pre-law) | the practice group in one office, plus the legal recruiting manager |
| Wealth management | the advisor's team or branch |

**Seniority.** Recruiters and senior people (manager, VP, director, partner, MD) first. A junior person (analyst, associate, staff) is fine when there is a real overlap, especially an alum. Write to them like a peer a few years behind.

**Move on after 7 days.** If nobody at a firm answered in 7 days and the firm still has room under the cap, research the next person.

**Recruiting contacts are a little different.** The hook is the firm's own careers-page line, the person's path, or a talk they gave. In the email, name their role in plain words ("the careers page sends student questions your way") because the gate blocks "recruit", "hiring" and "program" in first emails.

## 3. Published emails only

Use only an address **the person themselves has printed on a live public page.** Never build one from a pattern (first.last@, flast@), even when the pattern looks obvious.

Why: in the source data, pattern-guessed addresses bounced **4 of 30 (13%)**. Printed addresses bounced **1 of 191 (0.5%)**. Bounces hurt the Gmail account's sender reputation, and the send tool pauses after too many. A guess can also reach the wrong person (Tom vs Thomas).

Re-verify every address within 3 days of sending. `tools/verify_addresses.py` re-fetches the source page and confirms the exact address is still there.

### Where printed addresses live
- **Bio and team pages:** an "Email" button or envelope icon is often a `mailto:` link. Read the page source, not just the visible text. Some bios also offer a vCard (`.vcf`) download with the address inside.
- **Market updates, industry reports and newsletters (PDF):** the last page usually has a contact block listing each author with an email.
- **Press releases:** "For more information, contact" and media-contact blocks. Deal and project announcements sometimes list the lead people.
- **Conference and webinar speaker pages,** association committee pages, school and alumni pages (public ones only, never behind a login).
- **Law firms and accounting firms** often print every professional's address on their bio.

### Hidden but published
- **Cloudflare email protection:** the page shows "[email protected]" and the source has `data-cfemail="..."` or `/cdn-cgi/l/email-protection#...`. The hex string decodes by XOR-ing every byte with the first byte. `verify_addresses.py` decodes it.
- **ROT13:** some sites scramble addresses with ROT13 and unscramble them with JavaScript. The scrambled form looks like an address with nonsense letters. `verify_addresses.py` decodes it.
- **Spelled out:** "dana [at] northgate [dot] example". Fine, write it back as a normal address and record it exactly as printed.

Record `email_as_printed` exactly as it appears, and `email_source_url` as a bare URL. If you can't find the person's own printed address, drop them and pick someone else. A general inbox (info@, careers@) is only for a recruiting contact, and only if the page says it reaches them.

## 4. Prove they still work there

You need one of:
- a live bio on the firm's own site, or
- a 2025-26 source naming them at the firm (a deal release, article, talk, award).

A search-result snippet is not proof. Open the page. Put the evidence in `still_at_firm_evidence`.

## 5. Find a hook of THEIRS

Something they said, wrote, led or worked on, named precisely, with a source and a year. Generic firm facts ("your firm is a leader in...") don't count.

**Good hooks:** a line from their own bio, a deal or project on their page, a quote in a release, an article, a podcast or panel, a talk at a conference, a sector report they wrote, an award write-up, student press about them, a nonprofit board seat.

**By field, where to look:**
- **Finance:** deal pages and tombstones (say whether they led it or were on the team), sector reports and market updates, podcasts, panels.
- **Accounting:** firm insight articles, CPA society talks, webinars, local business journal awards, client-alert authorship.
- **Consulting:** authored articles and reports on the firm's insights pages, conference talks, case studies that name the team.
- **Tech:** engineering blog posts, conference talks, open-source projects, product launch posts.
- **Marketing:** campaign launches, trade-press interviews, award entries.
- **Engineering:** project pages, society talks and papers, local news on a project.
- **Healthcare:** hospital news releases, publications, community programs they lead.
- **Law:** matters on their bio, client alerts and articles, bar association talks.

**Rules for hooks**
- **Credit it correctly.** "Led" only when the source says so. Otherwise "on the team", "on your group's deal list". Record which in the finding.
- **Live and dated.** A 2025-26 sign that it is current. Anything older is "years ago" and gets paraphrased. A side project on a bio needs proof it still exists.
- **Their words, not more.** If the page says "enjoys sailing", the finding says "enjoys sailing", not "avid sailor".
- **Public and professional only.** Nothing about family, health, religion, politics, home address or personal social accounts. Never infer heritage from a name.
- **Deep beats obvious.** The best calls came from less obvious finds: an old scholarship profile, a podcast point, a hobby line in a bio. Spend the extra five minutes.

**Overlap with the user.** Read `me/profile.md`. If something real connects (same school, same sport, same hometown region, same language, same kind of work), note it in `best_hidden_thread`. An alumni tie must show on a firm, school or alumni-org page. If nothing connects at all, set `thin_research: true` and say why. The writer will skip them.

## 6. The research file

One JSON per person: `data/research/<batch>/<firmslug>-<lastname>.json`.

```json
{"name":"Dana Reyes","firm":"Ridgeway & Cole","title":"Audit Partner","seniority":"partner",
 "group":"Audit, real estate practice","office":"Columbus",
 "bio_url":"https://ridgewaycole.example/people/dana-reyes",
 "email":"dreyes@ridgewaycole.example","email_confidence":"published",
 "email_source_url":"https://ridgewaycole.example/people/dana-reyes","email_as_printed":"dreyes@ridgewaycole.example",
 "still_at_firm_evidence":"Live bio on the firm site, checked 2026-10-09",
 "alum":false,"alum_evidence":"",
 "application":{"title":"Sophomore Leadership Program","url":"https://ridgewaycole.example/students",
                "status":"upcoming","est_open":"2026-12-01","contact_by":"2026-10-20"},
 "hires_students_evidence":"Student programs page lists sophomore and intern programs for 2027",
 "referral_plan":"If she replies, ask on the call who runs campus programs for the office",
 "identity_confirmed":"Bio photo, title and office match the conference speaker page",
 "sources_tried":["firm bio","state CPA society spring conference page"],
 "findings":[{"fact":"Spoke on first-year audits of newly public companies","source_url":"https://cpasociety.example/spring-2026",
              "quote":"","year":"2026","verified":true,"credit":"speaker"}],
 "best_hidden_thread":"User keeps the books for a club team and closed its first full year this spring",
 "suggested_hook":"Her spring 2026 talk on first-year audits",
 "questions":["What makes a first-year audit go well?","How did you choose the real estate practice?","What do strong first-year associates do differently?"],
 "thin_research":false,"researched":"2026-10-09"}
```

Field notes:
- `seniority`: analyst, associate, vp, director, md, partner, manager, recruiter or other.
- `email_confidence`: always `"published"`. Anything else is not sent.
- `findings[].credit`: `led`, `team`, `firm` (the firm's work, not theirs), `author`, `speaker`, or `bio`.
- `questions`: three questions only this person can answer well. They go to the call sheet, never into the first email.
- `verify_addresses.py` adds `address_check {status, detail, checked_at}`. Don't write it by hand.

The writer copies `email`, `email_confidence`, `email_source_url`, `address_check`, `application` and `findings` into the draft (schema in SPEC.md), and fills `research.hook_used` and `call_prep`.

## 7. Drop the contact if

- no printed address of their own
- no proof they are still at the firm
- no hook of theirs (or only generic firm facts)
- the firm has no student hiring for the user's roles
- the firm is at its cap, or the person was already emailed (check `_already-contacted.txt` and `_domains-already-emailed.txt` in the batch folder)
