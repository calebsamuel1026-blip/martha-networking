---
name: daily
description: The whole morning routine in one command. Use when the user says /daily, "morning", "what's today", or "run the day". Checks replies and bounces, labels them, drafts answers, drafts due follow-ups, shows calls coming up and send room left, then asks what to send. Sends nothing without the user's "send".
---
# /daily

1. **Replies first.** Run `/check-replies` (it runs `python tools/digest.py`, labels each new reply with
   `tools/outcomes.py`, and has martha draft answers). Show each reply with its draft, newest first.

2. **Follow-ups.** Run `/follow-ups` for anything due today (day 7 and day 14 after a first email with no reply).
   Skip people who said no, asked to stop, or already have a call booked.

3. **Updates after applying.** If `me/strategy.md` or `data/sent/` shows an application submitted 2+ days ago whose
   contacts haven't heard about it, offer `/update-after-apply <firm>`.

4. **Calls this week.** List calls from `data/call-prep/` and any dates the user mentioned. Offer `/call-prep <who>`
   for anything in the next 3 days without a sheet.

5. **New outreach room.** Show send room left today (from the digest) and how many verified, gated drafts are
   waiting in `data/drafts/`. If fewer than the user's daily target are waiting, offer `/find-contacts` or
   `/find-search-funds`.

6. **Stop and ask.** Summarize in one short table: replies to send, follow-ups to send, new emails ready. Nothing goes
   out until the user types "send" for a specific group; then use `/send-day` (new emails) or send the replies and
   follow-ups through `tools/send_approved.py --send` after moving only those files into `data/approved/`.
