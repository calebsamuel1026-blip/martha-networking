---
name: send-day
description: Send a reviewed batch of first emails safely. Use when the user says /send-day, "send the batch", or "let's send today's emails". Re-verifies every address, gates the batch, plans a chunk order with --order, shows a 3-email spot-check, WAITS for the user's explicit "send", then runs run_send_day.py in the background (chunks of 8, bounce check between chunks, stops on the first bounce) and reports.
argument-hint: "[batch, default = newest folder in data/drafts]"
---
# /send-day [batch]

Arguments: `$ARGUMENTS`. Default: the newest folder in `data/drafts/` with drafts not yet in `data/sent/`. Tell the
user which batch you picked.

Rule 1 applies here more than anywhere: nothing is sent until the user types **send** after seeing the spot-check
in step 5 of this run.

## Steps

1. **Make sure the staging area is empty.** `data/approved/` must have no `.json` files (`run_send_day.py` refuses
   otherwise). If it has some, list them and ask the user what they are. Never delete or send them without asking.

2. **Re-verify every address now**, even if `/find-contacts` already did. Pages change, and the sender refuses any
   check older than 3 days.
   ```
   python tools/verify_addresses.py data/drafts/<batch>
   ```
   Any draft that isn't `verified` stays behind. Tell the user who and why (from `address_check.detail`). Don't
   re-point a failed draft to a guessed address.

3. **Gate the batch.**
   ```
   python tools/gate.py data/drafts/<batch>
   ```
   Fix failures with martha (rewrite) and re-run until it's clean, or leave those drafts out and say so.

4. **Plan the order and today's room.**
   ```
   python tools/run_send_day.py data/drafts/<batch> --order
   python tools/digest.py --no-check
   ```
   `--order` sends nothing. It writes `data/drafts/<batch>/order.txt`, with the file names arranged so every chunk of
   8 passes the gate on its own (repeat limit, at most 5 per firm per chunk, same-firm emails spread out) and a
   `# chunk N` line before each chunk. It lists any draft that fails the gate on its own and leaves it out. The digest
   shows **send room left today** and bounce health. If the order has more emails than the room left, tell the user
   how many will go today. The run stops by itself at the daily cap, and the rest wait for another day (re-verified
   then if their check is older than 3 days). Never raise the cap with `--cap` unless the user asks for that
   explicitly. If bounce health says paused, stop and tell the user.

5. **Spot-check: show the user 3 emails in full**, picked from different chunks (first, middle, last of the order
   list):
   ```
   [1/3] To: <name>, <title> at <firm>   address printed at <email_source_url> (verified <checked_at>)
   Subject: <subject>

   <body>

   Attach: <attach>
   ```
   Then the plan in 3 lines:
   `<k> emails, <c> chunks of 8, about 2 minutes apart, about <minutes> minutes total. Stops on the first bounce.`
   `Left out: <list or none>.`
   `Type **send** to start, or tell me what to change.`

   **Stop and wait.** Only the word "send" (or "send it" / "yes, send") in reply to this exact message counts.
   Anything else, such as edits, questions or "looks good", means no. Handle it, then show the spot-check again.

6. **On "send", run it in the background** (Bash with `run_in_background: true`) so the user can keep talking:
   ```
   python tools/run_send_day.py data/drafts/<batch> --list order.txt --chunk 8 --delay 120
   ```
   (`order.txt` is read from inside the batch folder.) Tell the user it started and roughly when it will finish.
   Don't start a second send while this one runs.

7. **When it finishes, report** from its output:
   - `DONE: <x> of <k> sent; no bounces seen yet.` Report the count, then run `python tools/digest.py --no-check` for
     room left and bounce health.
   - `STOPPED: bounce on [...]`: say who bounced and how many went out before it. Run
     `python tools/check_replies.py` to log it. Don't resume until the user decides. Suggest re-verifying the
     bounced person's source page (they may have left) and checking whether other drafts from the same source share
     the problem.
   - Stopped on a `BLOCKED` guard or the daily cap: show the line (daily cap, per-firm cap, stale check, double
     email, bounce guard). Fix the cause if there is one, and ask before sending again.
   - Anything not sent stays in `data/drafts/<batch>/` and can go in a later `/send-day`.

8. **Close with the next step:** "Replies usually come within 2 days. Run `/check-replies` tomorrow morning."
