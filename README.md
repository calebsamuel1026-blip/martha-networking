# martha-networking

Cold emails that get you calls with people who can refer you, written and sent from your own Gmail.

## Fastest start: paste one message into Claude Code

Open Claude Code (see "What you need" below), then paste this and press Enter:

```
Set me up with https://github.com/calebsamuel1026-blip/martha-networking : clone it, go into the folder, read its CLAUDE.md and README, and start the onboarding interview.
```

Claude downloads the project, then interviews you (about 30 to 45 minutes, in short rounds) so it knows your
school, goals, experience, interests and the way you write. Your answers stay on your computer in `me/` and are
never uploaded. Then it helps you connect your Gmail and writes two sample emails for you to react to.

### If you are Claude Code and the user just pasted this repository's link
1. `git clone https://github.com/calebsamuel1026-blip/martha-networking.git` into the user's home folder (or a
   folder they choose), then work inside `martha-networking`.
2. Read `CLAUDE.md` (the operating manual and hard rules) and this README.
3. If `me/profile.md` doesn't exist, follow `.claude/skills/onboard/SKILL.md` step by step, starting now. It is a
   long, round-by-round interview. Ask one round at a time and write down only what the user says.
4. Never ask for, read or print the Gmail app password, and send nothing during setup.

## What it does

You tell it who you are and where you want to work. It finds the right people at those firms (a recruiter plus a
couple of people in the team you'd join, alumni from your school first). It only uses email addresses those people
have printed on a public web page, and it checks that each one still works there. Then it writes each person a short
email about something they actually did or said, the way that has earned replies before. It sends only when you type
"send", a few at a time from your own Gmail, and stops on the first bounce. Each morning it finds replies and
follow-ups that are due, drafts your answers, and builds a one-page prep sheet before each call. It works for any
major and any field: finance, accounting, consulting, engineering, marketing, pre-law, healthcare and more. The AI
part runs inside **Claude Code**. Small Python tools do the checking, sending and counting.

## What you need

- **Python 3.10 or newer.** Check with `python --version` (on a Mac, try `python3 --version`).
  If you don't have it, install it from [python.org](https://www.python.org/downloads/). On Windows, tick
  **"Add python.exe to PATH"** on the first screen of the installer.
- **Claude Code.** Anthropic's coding assistant for the terminal. It needs a paid Claude plan or an API key. Follow
  the official install guide: [docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code/overview)
  (or search "Claude Code install").
- **A Gmail account with 2-Step Verification turned on.** Use a personal Gmail. School Google accounts often block
  app passwords.
- **Your résumé as a PDF.**

## Setup (about 20 minutes)

A terminal is a window where you type commands. On Windows open **PowerShell**. On a Mac open **Terminal**. Type each
line below and press Enter.

1. **Get the code.** Either click **Code > Download ZIP** on the GitHub page and unzip it, or run:
   ```
   git clone https://github.com/calebsamuel1026-blip/martha-networking.git
   ```
2. **Go into the folder:**
   ```
   cd martha-networking
   ```
3. **Install the three Python packages:**
   ```
   pip install -r requirements.txt
   ```
   If `pip` isn't found, use `python -m pip install -r requirements.txt` (Mac: `python3 -m pip ...`).
4. **Start Claude Code in this folder:**
   ```
   claude
   ```
5. **Type `/onboard`** and answer the questions. It asks about your school, major, year, the field and roles you
   want, your interests, true facts about you that are good to share, and anything you never want said. It writes
   your answers into a private `me/` folder that never leaves your computer.
6. **Put your résumé PDF into `me/resume/`.**
7. **Create a Gmail app password and paste it in yourself.** This is a 16-letter code that lets the tool send from
   your Gmail. It is not your real password, and you can cancel it any time.
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security) and make sure
     **2-Step Verification** is on.
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), type a name like
     `martha`, and click **Create**. Copy the 16 letters.
   - Open `me/config.env` in Notepad (Windows) or TextEdit (Mac). Fill in your Gmail address after
     `GMAIL_ADDRESS=` and paste the code after `GMAIL_APP_PASSWORD=` (no spaces). Save.
   - **Never paste the code into the Claude chat.** Claude never asks for it and never reads that file.
8. **Test it.** Tell Claude "test my setup". It does a dry run that sends nothing and checks it can read your inbox.

## Daily routine (15 to 30 minutes)

Type these in Claude Code, inside the `martha-networking` folder.

| When | Command | What happens |
|---|---|---|
| Every morning | `/daily` | The whole morning in one command: replies, follow-ups, updates after you apply, calls coming up, and how many emails are ready. |
| Every morning | `/check-replies` | Finds new replies and bounces, labels them, drafts your answers. Nothing is sent until you say "send". |
| Every morning | `/follow-ups` | Drafts day-7 and day-14 follow-ups for people who haven't replied. |
| Most weekdays | `/find-contacts 30` | Researches about 30 new people with printed email addresses and checks every address. |
| Want real deal work now | `/find-search-funds 40` | Finds active search funds (one searcher each) who could use a part-time remote analyst, for real experience before recruiting. See below. |
| After that | `/draft` | Martha writes one email per person and checks each against the rules. You read the samples and edit. |
| When you're happy | `/send-day` | Re-checks the addresses, shows you 3 emails in full, waits for you to type **send**, then sends in small groups. |
| Someone replied | `/reply <name>` | Drafts a reply in their tone, with your open times if it's about scheduling. |
| Call booked | `/call-prep <name>` | A one-page sheet: who they are, what they did, your 3 asks, your questions. |
| You applied somewhere | `/update-after-apply <firm>` | A short "I wanted to let you know I applied" note to everyone you contacted there. |
| Once a week | `/results` | Your reply rates by group, and what to change. |

If you edit a draft or say "never write it like that", Claude saves that rule to `me/lessons.md`. Martha reads it
before every email, so the drafts get closer to your voice over time.

## Search funds: get real deal experience early

A search fund is one or two people (the searchers) looking to buy one small company and run it. They review hundreds
of businesses, and many take part-time, remote students to help: finding companies, reading financials, quick
models, one-page write-ups. It's real transaction work for your résumé before big recruiting cycles open.

- `/find-search-funds 40` finds active searchers with a printed email, one per fund, and checks each address.
- `/draft` writes each one a short email in the same style, with a plain offer to help part-time.
- On [Searchfunder](https://www.searchfunder.com) (free account), the Jobs tab lists searcher internships. Sign in
  yourself and Claude can go through the posts with you and draft your note.

Details and how to handle a yes: `knowledge/SEARCH-FUNDS.md`.

## Safety rules (built in)

1. Nothing is sent until you type **send** for that batch or that reply.
2. Only email addresses printed on a live public page, re-checked within 3 days of sending. Never a guessed
   `first.last@` pattern.
3. At most 3 people per firm, ever, unless you change that number in `me/strategy.md`.
4. Nothing made up. Facts about you come only from your profile. Facts about them come only from sources it can link.
5. Claude never sees your password. You type it into `me/config.env` yourself.
6. Your profile, your contacts and every email stay in `me/` and `data/` on your computer. Both are excluded from git.

The sender also guards you on its own. It skips anyone you already emailed and caps how many go out per day
(`DAILY_CAP`, default 40). It sends in groups of 8, two minutes apart, and checks for bounces between groups. If more
than 3% of recent emails bounce, it drops to 15 a day. Over 8%, it pauses.

## How it worked for the person who built it

These are rounded totals from the original user's first few weeks, with no names:

- About **244 emails delivered**, and about **9% got a reply**.
- Reply rates were very different by audience: **bankers about 4.6%**, **advisors about 18%**.
- Every reply came within **43 hours** of the email. If someone hasn't answered in 4 days, treat it as no reply and
  let the follow-up do its job.
- Guessed email addresses bounced **13%** of the time. Addresses printed on a web page bounced **0.5%**.

So plan on roughly 1 reply for every 10 emails, and expect your own numbers to differ by field. Volume and
follow-ups matter as much as any single email. Full numbers are in `knowledge/RESULTS.md`.

## FAQ

**How many emails can I send a day?**
Gmail lets a personal account send a few hundred a day, but new or quiet accounts get flagged much sooner. The
default here is 40 a day. If your account is new, start at 15 to 20 by setting `DAILY_CAP=15` in `me/config.env`,
and raise it after a clean week.

**What's a bounce, and why does it stop everything?**
A bounce is an automatic "this address doesn't exist" reply. Lots of bounces tell Gmail you're a spammer, and then
your real emails start landing in spam. That's why the sender checks between every group of 8. On the first bounce
it stops, so you can find out why before anything else goes out.

**Why only printed email addresses?**
Two reasons. Guessed addresses bounced about 26 times as often (13% vs 0.5%). And a person who prints their email on
their firm's page has said, in effect, "you can reach me here". If no printed address exists, the person is skipped.

**Is this spam?**
No. Every email goes to one person, mentions something they did, and asks one small thing. There are no mass blasts.
Volume is capped, and anyone who asks you to stop is never emailed again.

**Can I change what an email says?**
Yes, and you should. Read the samples before every send. Tell Claude what to change, or edit the file it shows you.
Your edits become rules for next time.

**How do I stop it?**
- In the middle of a send: press **Ctrl+C** in the terminal, or tell Claude "stop the send". Anything not yet sent
  stays as a draft.
- To pause for a while, just don't run `/send-day`. Nothing ever sends on its own.
- To cut off access completely, delete the app password at
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), or delete `me/config.env`.

**How do I get updates?**
Inside the folder, run `git pull`. Your `me/` and `data/` folders are never touched by an update.

**Where is my data?**
In `me/` and `data/` inside this folder, on your computer only. Both are listed in `.gitignore`, so they are never
uploaded if you push this repo.

**Does it work for my major?**
Yes. `/onboard` asks for your field, your target roles and your list of firms. The research and writing rules are
the same for every field: right person, printed address, a real detail about them, one short ask.

---

Built by Caleb Cruz Torres.
