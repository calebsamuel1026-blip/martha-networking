---
name: follow-ups
description: Draft follow-ups for first emails that got no reply. Use when the user says /follow-ups, "who do I follow up with", or the digest lists follow-ups due. Day 7 = follow-up 1, day 14 = follow-up 2, then stop. Each follow-up adds one new small real thing, has no guilt, and restates the ask plainly, in the same thread. Sends only after the user's explicit "send".
---
# /follow-ups

Timing comes from `knowledge/STRATEGY.md`: no reply within 4 days means no reply. Follow-up 1 goes on day 7 after the
first email, follow-up 2 on day 14. After that, stop writing to that person and move to the next person at the firm
if the cap allows.

## Steps

1. **Find who is due.**
   ```
   python tools/digest.py --no-check
   ```
   (Run `python tools/digest.py` instead if replies haven't been checked today, so nobody who just replied gets a
   follow-up.) The digest lists follow-ups due: day 7 (follow-up 1) and day 14 (follow-up 2). Before drafting each
   one, re-check `data/outcomes.jsonl` and leave out anyone with a reply, decline, bounce or opt-out. Also leave out
   anyone at a firm marked applied in `me/strategy.md` (they get `/update-after-apply` instead), and anyone whose
   OOO return date hasn't passed yet.

2. **Draft with martha.** Use one Agent call with `subagent_type: "martha"`:
   > Task: follow-ups for `<list of sent files with day 7 / day 14>`. Do your mandatory reads (PLAYBOOK, STRATEGY,
   > WINNING-EMAILS, me/profile.md, me/lessons.md, the user's winners). For each person, read the first email and any
   > earlier follow-up. Write ONE short follow-up in the same thread: `kind: "followup"`, `reply_to` = the latest sent
   > file to them, `in_reply_to` = that file's `message_id`, subject `Re: <original subject>`, `attach: "none"`.
   > Each one adds one new small real thing (a fresh sourced finding about them, or a true update from
   > me/profile.md), carries no guilt ("just bumping", "circling back", "in case you missed it" are banned), and
   > restates the ask plainly. Shorter than the first email. Follow-up 2 is the last one and is shorter still. Never
   > invent. If there is no new real thing, a plain two-line restated ask is fine. Write to
   > `data/drafts/followups-<YYYY-MM-DD>/` and run the gate.

   For a fresh finding, martha may need a quick look at the person's page. Let it use the research file's
   `bio_url` and sources, or run a short researcher pass first.

3. **Gate.**
   ```
   python tools/gate.py data/drafts/followups-<YYYY-MM-DD>
   ```

4. **Show the user** 3 follow-ups in full (one day-7, one day-14 if there is one, and one more), each under its
   original subject line. Then the list of everyone else as `name | firm | day 7 or 14 | the new thing in 6 words`.
   Ask: "Type **send** to send all <k>, or tell me what to change." Apply and capture any edits
   (`python tools/capture.py note "..."`).

5. **Stop and wait for "send".** On "send":
   - 8 or fewer: make sure `data/approved/` is empty, copy the drafts in, dry run with
     `python tools/send_approved.py`, fix anything `BLOCKED`, then `python tools/send_approved.py --send --delay 90`.
   - More than 8: `python tools/run_send_day.py data/drafts/followups-<YYYY-MM-DD> --order`, then in the background
     `python tools/run_send_day.py data/drafts/followups-<YYYY-MM-DD> --list order.txt --chunk 8 --delay 120`.

6. **Report** the number sent and any stop or bounce. For people who just got follow-up 2, list their firms with slots
   left and suggest the next person there in the next `/find-contacts`.
