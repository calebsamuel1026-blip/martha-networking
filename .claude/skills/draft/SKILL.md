---
name: draft
description: Write first emails for a researched batch. Use when the user says /draft, "write the emails", "draft the batch", or right after /find-contacts finishes. Launches the martha subagent on the verified research (told to read knowledge/WINNING-EMAILS.md and mirror it), runs the gate on the batch, and shows the user 3 samples to review and edit. Sends nothing.
argument-hint: "[batch, default = newest folder in data/research]"
---
# /draft [batch]

Arguments: `$ARGUMENTS`. If no batch is given, use the newest folder in `data/research/` that has no matching
`data/drafts/<batch>/` yet. Tell the user which batch you picked.

## Steps

1. **Check the input.** Count the JSONs in `data/research/<batch>/` whose `address_check.status` is `verified`. If
   none have an `address_check`, run `python tools/verify_addresses.py data/research/<batch>` first. If zero are
   verified, stop and say why.

2. **Launch martha.** Use one Agent call with `subagent_type: "martha"` and this prompt (fill in the batch):
   > Task: first emails for batch `<batch>`.
   > Before writing, do your mandatory reads. **Read `knowledge/WINNING-EMAILS.md` first and mirror it**: the same
   > subject style, the same order of parts, about the same length, a hook of THEIRS named precisely, and one plain
   > ask. Then read `knowledge/PLAYBOOK.md`, `me/profile.md`, `me/lessons.md` (newest rulings win) and the user's own
   > winners in `data/sent/` (latest outcome call, referral or replied in `data/outcomes.jsonl`).
   > Input: `data/research/<batch>/*.json`, verified and published only.
   > Output: one draft JSON per person in `data/drafts/<batch>/`, using the SPEC.md schema, `kind: "first"`. Carry
   > over `to`, `email_confidence`, `email_source_url`, `address_check`, `application` and `findings`. Fill
   > `research.hook_used` and `call_prep`.
   > Never invent a fact. Skip thin research rather than writing a generic email.
   > Then run `python tools/gate.py data/drafts/<batch>` and fix every failure by rewriting.
   > Return the table, the skipped list, and 3 sample paths.

   If the batch has more than about 25 people, split it across two martha calls in the same message, each with half
   the files. Then run the gate once on the whole folder. The batch repeat check needs every draft at once.

3. **Gate the whole batch yourself.**
   ```
   python tools/gate.py data/drafts/<batch>
   ```
   If anything fails, send the failures back to martha (SendMessage to the same agent) to fix, and re-run. Never
   edit the gate to make a draft pass.

4. **Show the user 3 samples in full:** the strongest, the most typical, and the one martha was least sure of. For
   each, show:
   ```
   To: <name>, <title> at <firm>   (address printed at <email_source_url>)
   Subject: <subject>

   <body>

   Hook source: <findings[0].source_url>   Attach: <attach>
   ```
   Then a one-line summary: `<k> drafts in data/drafts/<batch>/, all passed the gate, <s> skipped (<reasons>)`.
   Ask: "Want changes? Edit any line, or tell me what to change across the batch."
   Remind them in one line to open the hook link of any email that says they read, watched or listened to
   something, so it's true when they send it.

5. **Apply edits and save the rulings.** For every change the user asks for:
   - apply it to every draft in the batch it fits (through martha, or directly for a small fix), not just the
     sample;
   - save it: `python tools/capture.py note "<rule in their words + a short before/after>"`, or
     `python tools/capture.py ban "<phrase>"` for a phrase they never want;
   - re-run `python tools/gate.py data/drafts/<batch>` and show the changed sample again.

6. **Stop here.** Drafting never sends. When the user is happy, the next step is `/send-day <batch>`. Say so in
   one line.
