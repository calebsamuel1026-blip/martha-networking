---
name: call-prep
description: Build a one-page prep sheet before a networking call. Use when the user says /call-prep <name>, "prep me for my call with...", or a call was just booked. Uses knowledge/CALL-PREP.md, the thread, the research file and a quick live refresh of the person's page, and writes data/call-prep/<date>-<lastname>.md. Sends nothing.
argument-hint: "<name, last name, or firm>"
---
# /call-prep <who>

Arguments: `$ARGUMENTS`.

## Steps

1. **Gather what we already know.** Find the person in `data/sent/` (all sent records to them), their replies in
   `data/replies/`, their research JSON (`data/research/*/`), and the draft's `call_prep` block (title, seniority,
   why_them, questions). Ask the user for the call date, time and format (phone, video) if it isn't in the thread or
   `me/availability.json`.

2. **Refresh, live and public only.** WebFetch their `bio_url` to confirm they're still there and their title. Do a
   few WebSearches for anything new since the research date: a recent deal or project, an article, a talk, firm news
   that touches their group. For a deeper look, run one `researcher` agent with "refresh only, no email needed, write
   findings to the existing JSON". Keep only facts with a source URL. Nothing private or personal.

3. **Write the sheet** to `data/call-prep/<YYYY-MM-DD>-<lastname>.md`. Follow the template in
   `knowledge/CALL-PREP.md`, and keep it to one page:
   - **Who:** name, title, group, office, years at the firm, alum or other commonality (sourced).
   - **Why them / how you got here:** your first email's hook and what they replied, in one line each.
   - **Their work:** 3 to 5 sourced facts, each with its link, saying whether they LED it or were on the team.
   - **Your 30-second story:** built only from `me/profile.md` (school, major, year, the 1 or 2 facts that fit this
     person, the interest line). Written so the user can say it out loud.
   - **The three asks** from `knowledge/STRATEGY.md`, worded for this firm and the user's target role: when the
     student application opens and how the firm recruits students; whether they'd be comfortable flagging the
     application or who to talk to next; whether you may send a note when you apply.
   - **Questions:** 4 to 6 that only this person can answer well, from their work. Mark the 2 to ask if time is
     short.
   - **Don't say:** the user's never-say list, plus anything sensitive about this firm.
   - **After the call:** thank-you within 24 hours (`/reply <who>`), log the outcome, add the application date to
     `me/strategy.md`, and send the update when you apply (`/update-after-apply <firm>`).

4. **Show the user the sheet** (the whole page) and its path. Offer one practice run: you play the other person
   for 3 questions, if they want.

5. **After the call** (when the user tells you how it went): label it with
   `python tools/outcomes.py label <first sent file> call "<one-line result: referral? application date? next step?>"`,
   update `me/strategy.md` with any dates or names learned, save any lesson with
   `python tools/capture.py note "..."`, and start the thank-you with `/reply <who>`.
