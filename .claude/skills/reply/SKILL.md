---
name: reply
description: Draft a reply to one thread. Use when the user says /reply <name or firm>, "answer <name>", "what do I say back to...", or wants to schedule a call, handle a referral, a decline, or send a thank-you after a call. Uses knowledge/REPLIES.md and me/availability.json, mirrors the other person's register, and sends only after the user's explicit "send".
argument-hint: "<name, last name, firm, or sent file>"
---
# /reply <who>

Arguments: `$ARGUMENTS`. Who to reply to: a name, last name, firm, or sent file name.

## Steps

1. **Find the thread.** Search `data/sent/` (the `name`, `firm` and `to` fields) and `data/replies/` for `<who>`. If
   more than one person matches, list them and ask which. Read everything: every sent record to them in date order,
   every reply from them, their research file, their outcome lines in `data/outcomes.jsonl`, and any call sheet in
   `data/call-prep/`.

2. **Work out what's needed** and tell the user in one line: scheduling, answering a question, a referral, a
   decline, a thank-you after a call, or an out-of-office. If the user is replying after a call, ask for 2 or 3 real
   things from the call to mention. Never make them up.
   - Opt-out or legal words in their message: don't draft. See the stop rules in `CLAUDE.md`.

3. **For scheduling, get real open times.** Read `me/availability.json` (window, recurring blocks, one-off blocks)
   and draw them:
   ```
   python tools/availability.py <next Monday as YYYY-MM-DD>
   ```
   Show the user the PNG path so they can confirm at a glance. The email offers one simple range in the other
   person's time zone (for example "Tuesday or Wednesday, any time 10 to 2 ET"), not a grid. If an assistant is
   scheduling, the reply goes to the assistant.

4. **Draft with martha.** Use one Agent call with `subagent_type: "martha"`:
   > Task: one reply to `<sent file>`. Do your mandatory reads, including `knowledge/REPLIES.md` (and
   > `me/availability.json` for times: `<the range the user confirmed>`). Read the whole thread. Mirror their register:
   > length, formality, greeting, sign-off. Answer what they asked first, then one next step. `kind` =
   > reply | scheduling | thankyou, `reply_to` = `<latest sent file>`, `in_reply_to` = their Message-ID, subject
   > `Re: <subject>`, `attach: "none"` unless they asked for the résumé. Use only facts from me/profile.md, the
   > thread, and what the user told you: `<call notes, if any>`. Write to `data/drafts/replies-<YYYY-MM-DD>/` and run
   > the gate.

   For a referral where the new person wasn't cc'd and only a name was given, find their published address with
   one `researcher` run (same rules as `/find-contacts`) before drafting the email to them. If there isn't one, the
   reply to the referrer can ask them to connect you by email.

5. **Show the draft in full** under their last message (quote the last 2 to 4 lines of theirs for context). Then:
   "Type **send** to send it, or tell me what to change." Apply edits, and save rulings with
   `python tools/capture.py note "..."`.

6. **Stop and wait for "send".** On "send":
   - `data/approved/` must be empty. Copy this draft in.
   - Dry run with `python tools/send_approved.py`. Fix anything `BLOCKED`.
   - Send with `python tools/send_approved.py --send`.

7. **After sending.**
   - Call booked: add it to `me/availability.json` `one_off` (date, start, end, `"label":"call"`), label the thread
     `python tools/outcomes.py label <first sent file> call "booked <date> <time>"`, and suggest
     `/call-prep <who>`.
   - Referral: label `referral` with who they pointed to.
   - Thank-you after a call: remind the user of anything they promised on the call (send a résumé, apply by a date,
     an update when they apply).
