---
name: find-search-funds
description: Find active search funds (searchers) to email for a part-time, remote analyst role. Use when the user says /find-search-funds, "search funds", "searchers", "ETA", or wants real deal experience before recruiting. Launches researcher subagents in parallel on three lanes (investor portfolio lists, self-funded and local searchers, searchers who hire students or just bought a company), one contact per fund, then verifies addresses. Sends nothing.
argument-hint: "[n=40] [focus, e.g. logistics | Florida | healthcare]"
---
# /find-search-funds [n] [focus]

Arguments: `$ARGUMENTS`. `n` = funds wanted (default 40). `focus` = optional industry or region to rank first.

## Steps

1. **Read** `knowledge/SEARCH-FUNDS.md`, `knowledge/RESEARCH.md` and `me/profile.md` (the user's experiences decide
   which theses fit best). If `me/profile.md` is missing, run `/onboard` first.

2. **Name the batch** `<YYYY-MM-DD>-searchfunds[-focus]` and create `data/research/<batch>/`.

3. **Build skip lists** the same way `/find-contacts` does (step 3 there): every address and email domain already in
   `data/sent/` goes into `_already-contacted.txt` and `_domains-already-emailed.txt`.

4. **Write the brief** `data/research/<batch>/_BRIEF.md` from `knowledge/SEARCH-FUNDS.md` "Rules" plus: the user's
   story facts that fit searchers (jobs, industries, region), the focus, and this JSON schema per fund:
   `{"name","firm","title","co_searcher","search_type":"traditional|self-funded|post-acquisition","thesis","bio_url",
   "email","email_confidence":"published","email_source_url","email_as_printed","email_note","still_active_evidence",
   "takes_interns_evidence","findings":[{"fact","source_url","quote","year","verified"}],"best_hidden_thread",
   "suggested_hook","thin_research","researched"}`. One JSON per fund named `<fundslug>-<lastname>.json`.

5. **Launch three `researcher` subagents in parallel** (one Agent call each, `run_in_background: true`), each told to
   read the brief, skip the lists, and find about n/3 funds:
   - **Lane A:** traditional searchers from search-fund investors' portfolio and "current searchers" pages.
   - **Lane B:** self-funded searchers and searchers in the user's region or with a thesis matching the user's
     experience (the focus first).
   - **Lane C:** searchers who have publicly hired student interns or analysts, and searchers who closed an acquisition
     in the last 18 months and now run the company.
   Tell each lane: published emails only, one contact per fund, prove the search is live, no LinkedIn visits, no
   logins, send nothing.

6. **When all three finish:** remove duplicate funds (same email domain), then run
   `python tools/verify_addresses.py data/research/<batch>`. Move anything not `verified` into `_hold/` with the reason.

7. **Report:** count by lane, the 5 best fits and why, anything held. Next step: `/draft <batch>` (the draft skill
   uses the search-fund ask from `knowledge/SEARCH-FUNDS.md` when the batch name contains "searchfunds").

8. **Searchfunder (optional):** ask the user to sign in at searchfunder.com in the browser pane. Read the Jobs tab with
   them, list the open searcher internships that fit (remote, part-time, open to their year), and draft a short note
   for each in the same style. The user sends those from their own account.
