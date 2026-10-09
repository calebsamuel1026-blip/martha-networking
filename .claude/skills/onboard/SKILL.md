---
name: onboard
description: First-time setup for a new user. Use when me/profile.md does not exist yet, or when the user says "set me up", "onboard", "start", "redo my profile", or wants to change their field, targets or availability. Interviews them, writes me/profile.md, me/strategy.md and me/availability.json, walks them through creating a Gmail app password that they type in themselves, and runs a dry-run test. Sends nothing.
argument-hint: "[redo]"
---
# /onboard

Goal: a working `me/` folder that describes the user truthfully, plus a tested Gmail connection, in about 20 minutes.
Be warm and brief. Many users have barely used a terminal, so explain each step in one plain sentence.

## Steps

1. **Check the basics.**
   ```
   python --version
   python -m pip install -r requirements.txt
   ```
   You need Python 3.10 or newer. On a Mac, try `python3` if `python` isn't found. If install fails, show the error
   and fix it before going on.

2. **Create `me/`.** If `me/` doesn't exist, copy `me.example/` to `me/` (all files, including `resume/` and
   `config.env.example`). Then copy `me/config.env.example` to `me/config.env`. If `me/` already exists and the user
   didn't say `redo`, read `me/profile.md` and only ask about what's missing or what they want to change.

3. **Interview the user.** Ask in small groups of 2 or 3 questions, not all at once. Write down only what they
   say, and never fill gaps with guesses.
   - Name as it should appear in emails, school, class year, major and minor, and the student clubs or teams they
     actually belong to.
   - The field(s) and target roles (for example "audit internship, Big 4 and regional firms", "summer analyst,
     industrials coverage", "product marketing intern at consumer brands"), the summer(s) they're recruiting for,
     and any location limits.
   - Interests and story facts that are true and that they're happy to share: hometown, languages, sports, music,
     jobs, a project they built, something they're proud of. For each one, ask "is it OK if an email mentions this?"
   - Never-say list: facts, words or topics they never want in an email.
   - Why this field: one sentence in their words (saved as `why_field`). Then the interest line every first email
     uses, as `interest_line`, for example "a strong interest in audit at <Firm>". The gate allows this exact phrase
     to repeat across a batch.
   - Résumé: ask them to drop the PDF into `me/resume/` and tell you the file name. Don't read its contents
     unless they ask you to.
   - Firms: their list by tier (dream, target, safety), or "help me build it". If they want help, propose a list
     with each firm's student program page and the usual application window. Mark windows you haven't confirmed as
     estimates. They approve the list.
   - Calls: their usual free hours for 20-minute calls, time zone, recurring classes or practices, and any dates
     they're already busy.

4. **Write the files.** Keep the exact front-matter keys and section headings from `me.example/` so the tools can
   parse them.
   - `me/profile.md`: front matter (lists written as `a; b; c`), then the story facts, why_field and never-say
     list, exactly as the user gave them. The gate reads these keys, so fill them: `school`, `standing` (for
     example sophomore), `interest_line`, `never_say`, and `resume_items` (club, job and project names. A first
     email may name at most one).
   - `me/strategy.md`: fields and roles, firm list by tier with application windows and links, and the line
     `max people per firm: 3` (3 unless the user asks for another number).
   - `me/availability.json`: `{"window":[start_hour,end_hour],"tz":"<IANA zone>","recurring":[...],"one_off":[...]}`.
   - `me/lessons.md`: leave it as the template (it starts empty).

   Show the user a short summary of each file and ask "anything wrong or missing?" Fix it before moving on.

5. **Gmail app password. The user does this themselves.** Never ask for it, never read `me/config.env`, and never
   ask them to paste it in the chat. If they paste it anyway, tell them to delete that app password at
   https://myaccount.google.com/apppasswords and make a new one, and don't repeat or store it anywhere. Walk them
   through it:
   1. Use a personal Gmail. School accounts often block app passwords.
   2. Turn on 2-Step Verification: https://myaccount.google.com/security
   3. Create an app password: https://myaccount.google.com/apppasswords. Name it `martha` and copy the 16 letters.
   4. Open `me/config.env` in Notepad (Windows) or TextEdit (Mac). Type your Gmail address after `GMAIL_ADDRESS=`
      and paste the 16 letters with no spaces after `GMAIL_APP_PASSWORD=`. Leave `DAILY_CAP=40`, or set 15 to 20
      if the Gmail account is new or rarely used. Save the file.
   5. Tell me "done" when it's saved.

6. **Test, sending nothing.**
   ```
   python tools/send_approved.py
   python tools/send_approved.py --test-login
   python tools/check_replies.py --dry-run
   ```
   The first is a dry run of the sender: with an empty `data/approved/` it should report nothing to send and no
   config error. The second logs in to Gmail and quits. The third reads the inbox over IMAP (read-only) and writes
   nothing. If login fails, the usual causes are a typo in the address, spaces in the app password, 2-Step
   Verification off, or a school-managed account. Explain the fix, and the user edits the file again themselves.
   Never print the file to debug.

7. **Finish.** Tell the user what's ready and what to do next. Keep it to 5 lines or fewer:
   - `/find-contacts 30` to research the first batch
   - `/draft` to write it, `/send-day` to send it after they read it
   - every morning: `/check-replies`, then `/follow-ups`
   - "If you ever edit an email or tell me how you like things said, I'll save it as a rule in me/lessons.md."
