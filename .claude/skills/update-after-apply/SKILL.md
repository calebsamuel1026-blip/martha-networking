---
name: update-after-apply
description: After the user applies to a firm, tell everyone they contacted there. Use when the user says /update-after-apply <firm>, "I applied to <firm>", or "I just submitted my application at...". Drafts the short "I wanted to update you and let you know I applied for the <X> position" note in each existing thread (it doubles as the follow-up for people who never replied), and sends only after the user's explicit "send".
argument-hint: "<firm>"
---
# /update-after-apply <firm>

Arguments: `$ARGUMENTS`. The firm the user applied to.

## Steps

1. **Confirm the application.** Ask for the exact position title as posted (for example "Summer 2028 Audit
   Intern, Chicago") and the date they applied, if they didn't say. Don't guess the title.

2. **Record it.** In `me/strategy.md`, mark the firm `applied <YYYY-MM-DD>: <position>`. From now on
   `/find-contacts` sends no new cold emails there, and `/follow-ups` skips people there.

3. **Find everyone contacted at the firm.** Match `firm` in `data/sent/*.json` (and the email domain, in case the firm
   name was written differently). For each person, take their latest sent record and latest outcome in
   `data/outcomes.jsonl`. Leave out anyone whose latest outcome is `bounce`, `declined` or `negative`, and say who you left
   out. Show the list: `name | role | status (replied / call / no reply)`.

4. **Draft with martha.** Use one Agent call with `subagent_type: "martha"`:
   > Task: update emails after applying to `<firm>` for `<position>`. Do your mandatory reads (STRATEGY.md has the
   > update email). For each person, read the whole thread and write one short note in that thread. Open with the
   > user's line: "I wanted to update you and let you know I applied for the <position> position." Then for people
   > who talked with the user, one true line of thanks tied to the call or reply. For people who never replied, no
   > guilt and no re-pitch, just the update and at most one plain line asking if they'd be open to a quick call or to
   > flagging the application, based on the user's three asks. Keep it under about 70 words. `kind: "followup"`,
   > `reply_to` = their latest sent file, `in_reply_to` = their latest Message-ID, subject `Re: <original subject>`,
   > `attach: "none"`. Never invent. Write to `data/drafts/update-<firmslug>-<YYYY-MM-DD>/` and run the gate.

5. **Gate.**
   ```
   python tools/gate.py data/drafts/update-<firmslug>-<YYYY-MM-DD>
   ```
   Every note opens with the same line on purpose. If the batch repeat check fails only because of that line, tell
   the user and send the notes one at a time in step 7 (one draft in `data/approved/` per send). Don't reword the
   user's own line to get past the check. Fix any other failure by rewriting.

6. **Show every draft in full** (there are at most a few per firm). Then: "Type **send** to send these <k>, or
   tell me what to change."

7. **Stop and wait for "send".** On "send": make sure `data/approved/` is empty, copy the drafts in, dry run with
   `python tools/send_approved.py`, fix anything `BLOCKED`, then `python tools/send_approved.py --send --delay 60`.

8. **Report** who got the update. Remind the user to mention the application in any upcoming call, and to run
   `/check-replies` tomorrow.
