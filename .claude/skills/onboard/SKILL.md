---
name: onboard
description: First-time setup for a new user. Use when me/profile.md does not exist yet, when someone has just cloned or pasted this repo's link, or when the user says "set me up", "onboard", "start", "redo my profile", or wants to change their field, targets, voice or availability. Runs a long, friendly interview so the emails sound like them and use only true facts, writes me/profile.md, me/strategy.md and me/availability.json, calibrates their writing voice on two sample emails, walks them through a Gmail app password that they type in themselves, and runs a dry-run test. Sends nothing.
argument-hint: "[redo]"
---
# /onboard

Goal: Claude knows this person well enough to write cold emails that sound like them and that use only true facts,
plus a tested Gmail connection. Plan on 30 to 45 minutes. The interview is long on purpose: every good email in this
system came from a real, specific overlap between the student and the person they wrote to, and you can only find
those overlaps if you know the student well.

Be warm, curious and brief. Many users have barely used a terminal, so explain each step in one plain sentence.
Ask **one round at a time** (3 to 6 questions), wait for the answers, then go on. Tell them up front: "I'm going to
ask a lot of questions so your emails sound like you. Skip anything you'd rather not share. Short answers are fine."
Write down only what they say. Never fill a gap with a guess, never "improve" a fact, never add color.

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

3. **The interview (8 rounds).** After each round, play back in one or two lines what you wrote down, so they can
   correct it. For every personal fact, ask "OK if an email mentions this?" and record the answer.

   **Round 1: basics**
   - Your name as it should appear in emails, and the first name you sign with.
   - School (full name), the short name you'd use in a sentence, class year, standing (freshman, sophomore...).
   - Major, minor, and any concentration or certificate.
   - Where did you grow up? Where do you live now?

   **Round 2: the goal**
   - What field and roles are you going after? Be as concrete as you can ("audit intern at Big 4 and regional
     firms", "summer analyst in industrials coverage", "product marketing intern at consumer brands").
   - Which summers are you recruiting for, nearest first? Any program deadlines you already know?
   - Locations: where would you work? Anywhere you won't?
   - Firm size: is there a floor ("middle market and up", "no startups under 50 people") or firms you'd skip?
   - Dream firms, target firms, safeties. Or say "help me build the list".
   - Why this field? One or two sentences in your own words.

   **Round 3: experience, one item at a time** (jobs, internships, clubs, research, teams, projects, things you
   started). For each one:
   - What it is, your title, and the dates.
   - What you actually did, in plain words. Any real numbers you're comfortable sharing.
   - One specific moment or problem from it that you'd tell someone on a call.
   - Is it on your résumé? OK to mention in an email?

   **Round 4: things you built or started** (a business, an app, a club, a fundraiser, a channel, anything).
   - What it does, who it's for, how far it got. Only true, current facts ("I started X, a ... for ...").
   - What you'd want a professional to find interesting about it, in one line.

   **Round 5: you outside of work** (these become the "real overlap" with people whose pages share them)
   - Heritage, languages you'd use on a call, places you've lived.
   - Sports you play or played (position, level) and teams you follow.
   - Music, art, instruments (how many years), performing.
   - Volunteering, faith or community groups, causes (only if they want these used).
   - Hobbies and anything unusual about you that people remember.
   - Then: "Which three of these would you most like to lead with when someone shares them?"

   **Round 6: your voice**
   - Paste two or three sentences you've written recently to a professor, boss or recruiter (an email you liked).
     If you don't have one, write three sentences about yourself the way you'd say them out loud.
   - How formal do you want to sound: casual, friendly-professional, or formal?
   - Words or phrases you'd never say ("pick your brain", "I'm passionate about", "synergy"...).
   - Punctuation you dislike (some people never want semicolons, em dashes or exclamation marks).
   - Anything you never want an email to do: brag, list your résumé, sound too humble, mention grades...

   **Round 7: never-say and privacy**
   - Facts or topics that must never appear in an email, with the reason (for example a family business that isn't
     yours, a scholarship that's private, a job title that's wrong if shortened).
   - OK to give your phone number in replies once someone agrees to a call?

   **Round 8: logistics and outreach rules**
   - Your usual free hours for 20-minute calls, time zone, recurring classes, practices or work shifts, and dates
     you're already busy.
   - Days or times emails must NOT go out (some people never send on Fridays or weekends).
   - How many emails a day you'd like to send once you're set up (start with 20 to 40 on a new Gmail).
   - Max people per firm (default 3). Who first: recruiters, alumni, seniors or juniors?
   - Upcoming trips or events where you could meet people in person (city and dates).
   - Résumé: drop the PDF into `me/resume/` and tell me the file name. Don't read it unless they ask.

4. **Write the files.** Keep the exact front-matter keys and section headings from `me.example/` so the tools can
   parse them.
   - `me/profile.md`: front matter (lists written as `a; b; c`), then `# Story`, `# Okay to mention (and when)` and
     `# Voice`, exactly as the user gave them. The gate reads these keys, so fill them: `school`, `standing`,
     `interest_line`, `never_say`, `resume_items` (club, job and project names; a first email may name at most one),
     and `facts` (one short true sentence each, in their words). Put their writing sample, formality, banned words
     and punctuation rules under `# Voice`. Add every banned word or phrase to `never_say` too.
   - `me/strategy.md`: fields and roles, firm list by tier with application windows and links (mark unconfirmed
     windows as estimates), `max people per firm: <n>`, firm-size floor, send days and times to avoid, daily volume,
     and any trip with dates.
   - `me/availability.json`: `{"window":[start_hour,end_hour],"tz":"<IANA zone>","recurring":[...],"one_off":[...]}`.
   - `me/lessons.md`: leave it as the template (it starts empty).

   Show a short summary of each file and ask "anything wrong or missing?" Fix it before moving on.

5. **Calibrate the voice (this is what makes the emails good).** Read `knowledge/WINNING-EMAILS.md`. Ask the user
   for one real person they'd like to email, or pick a believable example in their field. Have the **martha**
   subagent write two short first emails to that person using only `me/profile.md`: one leaning on their strongest
   experience, one on a personal overlap. Show both and ask:
   - "Does this sound like you? What would you change?"
   - "Anything here you'd never say?"
   Save every answer right away with `python tools/capture.py note "<rule in their words + a short example>"` and
   any banned phrase with `python tools/capture.py ban "<phrase>"`. Rewrite once and confirm they like it. Nothing
   is sent in this step.

6. **Gmail app password. The user does this themselves.** Never ask for it, never read `me/config.env`, and never
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

7. **Test, sending nothing.**
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

8. **Finish.** Tell the user what's ready and what to do next, in 6 lines or fewer:
   - From now on, open Claude Code inside the `martha-networking` folder so the slash commands work.
   - `/find-contacts 30` to research the first batch, `/draft` to write it, `/send-day` to send it after you read it.
   - Every morning: `/daily` (replies, follow-ups, calls).
   - "If you ever edit an email or tell me how you like things said, I'll save it as a rule in me/lessons.md."
