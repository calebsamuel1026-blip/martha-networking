---
name: results
description: Show what's working. Use when the user says /results, "how am I doing", "what's my reply rate", "what should I change", or weekly. Runs results.py (rates overall, by segment, thread and day, plus candidate lessons when n>=30 and z>=2), adds data-backed lessons to me/lessons.md with the user's OK, and suggests concrete changes. Sends nothing.
---
# /results

## Steps

1. **Make sure the data is current.**
   ```
   python tools/check_replies.py
   ```
   Then run `python tools/outcomes.py list --only replied` and open the matching files in `data/replies/`. Any that
   was really a call, referral, decline or opt-out gets relabeled first
   (`python tools/outcomes.py label <file> call|referral|replied|declined|negative "note"`), or the call and
   referral rates will read low.

2. **Run the numbers.**
   ```
   python tools/results.py
   ```
   It prints response rates overall, by segment, by thread (first email vs follow-ups) and by day. Then it lists
   candidate lessons wherever a difference has n>=30 and z>=2. Run `python tools/results.py --help` for any extra
   breakdowns or chart options, and if it saved a chart, give the user its path.

3. **Explain it in plain words**, in 6 lines or fewer, for example:
   - "112 delivered, 9 replies (8%), 3 calls, 1 referral."
   - "Alumni replied 3 times as often as non-alumni (n=34, z=2.4)."
   - "Follow-up 1 brought 3 of the 9 replies, so keep sending it."
   - Compare with the original user's aggregate numbers in `knowledge/RESULTS.md` only as a rough benchmark. Fields
     differ.
   - Say clearly when a group is too small to conclude anything (n<30). Don't turn noise into a rule.

4. **Lessons (only the strong ones).** For each candidate lesson with n>=30 and z>=2, show it and ask "save this as
   a rule?". On yes:
   ```
   python tools/capture.py note "<lesson in one line> (n=<n>, z=<z>, <date range>)"
   ```
   If the user says yes to all of them, `python tools/results.py --write-lessons` appends every qualifying lesson
   at once. Martha reads `me/lessons.md` before every task, so the next drafts change.

5. **Suggest at most 3 concrete changes**, each tied to a number above. Examples: more alumni and recruiters in the
   next `/find-contacts` focus, a different send day or hour, dropping a segment with 0 replies in 40 or more emails,
   or rewording the ask if calls per reply are low. Also flag hygiene problems: bounce rate over 3% (go back to
   printed addresses only and re-verify), or many follow-ups due and not sent.

6. **Stop.** Nothing changes in `me/strategy.md` unless the user says so.
