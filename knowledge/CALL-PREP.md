# Call prep: one page per call

Make the sheet the day before. Save it as `data/call-prep/<YYYY-MM-DD>-<lastname>.md`. Everything on it comes from the research file, the sent email, their reply and `me/profile.md`. Never invent a fact for either side.

## The template

```markdown
# Call prep: <Full name>, <Firm>

**<Day, date>, <time> <time zone>** (<length>) | **<Who calls whom>**, <number or video link>
<Flags: time zone mismatch, call not confirmed yet, assistant to check with, invite not received.>

## Who they are
- <Title, group, office. Years at the firm or in the field. School, only if their page says it.>
- <The thing your email was about, with its date and whether they led it or were on the team.>
- <One fresh fact from the last 12 months, with the source and date.>

## Two things to mention
1. Their work: "<one sentence in your own words about the thing of theirs you wrote about>"
2. Your story: "<one true sentence from me/profile.md that ties to it>"

## Tell me about yourself (60 seconds)
"<School, year, major. Where you're from, if it matters here. One or two things you've done, said plainly.
Why this field. Why them. End with: I'd love to hear how you got here.>"

## Questions
1. <About their work: specific to the hook, something only they can answer>
2. <About their view or their path: how they got from X to Y, what surprised them>
3. Ask (a): When does the application for my class year open at <Firm>, and how does the <group> get to know students before then?
4. Ask (b): When I apply, would you be comfortable flagging my application, or is there someone in the group or in recruiting I should talk to next?
5. Ask (c): May I send you a short note when I apply?

## What NOT to say
- No expertise claims about their field.
- Don't name other people at the firm you've emailed. Say "the team".
- No questions their website already answers. No pay, hours or "is this a stepping stone".
- <Watch-outs from the research file: unverified facts, old items, anything private.>

## Thank-you draft (send within 24 hours, after you approve it)
Hi <First name>,

Thank you for the time <day>. I enjoyed hearing [one thing they said, in their words].
<If they offered an introduction: I'd be grateful for that introduction whenever it's convenient.>
I'll send you a short note when I apply.

Best,
<Your first name>
```

## On the call

- **Let them talk about 70% of the time.** Your job is good questions and real listening.
- **Questions 1 and 2 first,** about them. The three asks go last, in order.
- **Write down one thing they said, word for word.** It goes in the thank-you.
- If they ask "any questions for me?" early, start with question 1.
- If they offer to introduce you to someone, say thank you and ask for the person's name, so you can watch for the email.
- Have the résumé open. Don't read from it.

## Field notes for questions 1 and 2

- **Finance:** a deal or report of theirs, how buyers think about a sector, how they chose their group.
- **Accounting:** what makes an engagement go well, how they picked audit, tax or advisory, what strong first-years do.
- **Consulting:** a project type they like, how they chose the office or practice, what a good first year looks like.
- **Tech:** a talk or post of theirs, how their team decides what to build, what good interns did.
- **Marketing:** a campaign they worked on, how they measure it, how they got onto the brand.
- **Engineering, healthcare, law:** a project, program or matter on their page, and the path that led them there.

## After the call

1. Fill in the thank-you with the one thing they said. The user approves it and it goes out within 24 hours.
2. Label the outcome: `python tools/outcomes.py label <sent-file> call "<one-line note>"`.
3. Put any dates they gave (application opening, a time to follow up) on the calendar and in `me/strategy.md`.
4. If they named someone to talk to, research that person (REPLIES.md, referrals).
