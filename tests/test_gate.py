"""gate.check (one draft) and gate.run (a batch) against the universal rules and the user's own rules."""
import pytest

import builders as B
import gate


def errors_for(draft):
    return gate.check(draft, "draft.json")


def has(errs, fragment):
    return any(fragment in e for e in errs)


def test_clean_first_email_passes():
    for i in range(len(B.CONTACTS)):
        assert errors_for(B.first_email(i)) == [], B.file_name(i)


def _replace(old, new):
    def mutate(d):
        assert old in d["body"], old
        d["body"] = d["body"].replace(old, new, 1)
    return mutate


def _short(d):
    d["body"] = ("Hi Jordan,\n\nHope your week has been going well. I'm a current sophomore at Lakeshore State "
                 "University with a strong interest in audit at Northgate Partners. Resume attached.\n\nBest,\nAlex")


def _long(d):
    hook = B.CONTACTS[0]["hook"]
    d["body"] = d["body"].replace(hook, " ".join([hook] * 3), 1)


def _attach_none(d):
    d["attach"] = "none"


# (rule, how to break it, a fragment of the error the gate must report)
BROKEN = [
    ("semicolon", _replace("going well.", "going well;"), "contains semicolon"),
    ("em dash", _replace("going well.", "going well —"), "contains em dash"),
    ("en dash", _replace("going well.", "going well –"), "contains en dash"),
    ("question mark", _replace("Resume attached.", "Would that work? Resume attached."),
     "first email asks a direct question"),
    ("placeholder [Name]", _replace("Hi Jordan,", "Hi [Name],"), 'leftover placeholder "[Name]"'),
    ("placeholder <Firm>", _replace("at Northgate Partners.", "at <Firm>."), 'leftover placeholder "<Firm>"'),
    ("too short", _short, "words (want 110-180)"),
    ("too long", _long, "words (want 110-180)"),
    ("resume attached with attach none", _attach_none, "says something is attached but no résumé is attached"),
    ("AI-tell opener", _replace("Hope your week has been going well.", "I hope this finds you well."),
     'AI-tell phrase "i hope this finds you"'),
    ("AI-tell passionate", _replace("I keep the books", "I am passionate about audit and I keep the books"),
     'AI-tell phrase "passionate about"'),
    ("I'm reaching out", _replace("Since you have", "I'm reaching out since you have"),
     'AI-tell phrase "i\'m reaching out"'),
    ("I’m reaching out (curly)", _replace("Since you have", "I’m reaching out since you have"),
     'AI-tell phrase "i\'m reaching out"'),
    ("I am reaching out", _replace("Since you have", "I am reaching out since you have"),
     'AI-tell phrase "i am reaching out"'),
    ("expertise claim: I know how", _replace("I keep the books", "I know how audits work and I keep the books"),
     'sells yourself ("i know how")'),
    ("expertise claim: expertise in", _replace("I keep the books", "With my expertise in bookkeeping, I keep the books"),
     'sells yourself ("expertise in")'),
    ("expertise claim: firsthand", _replace("I keep the books", "I learned firsthand when I kept the books"),
     'sells yourself ("firsthand")'),
    ("BAN phrase from lessons.md", _replace("Since you have", "I will circle back soon. Since you have"),
     'banned phrase "circle back" (BAN in me/lessons.md)'),
    ("never_say phrase", _replace("I keep the books", "Outside our family business, I keep the books"),
     'banned phrase "family business" (never_say in me/profile.md)'),
    ("never_say phrase, any case", _replace("I keep the books", "With a solid GPA, I keep the books"),
     'banned phrase "gpa" (never_say in me/profile.md)'),
    ("mentions the application", _replace("Since you have", "I plan to apply this winter. Since you have"),
     "mentions the application"),
    ("ask in the subject", lambda d: d.update(subject="Quick call | Northgate Interest"),
     "subject contains an ask"),
]


@pytest.mark.parametrize("rule, mutate, expected", BROKEN, ids=[b[0] for b in BROKEN])
def test_each_universal_rule_fails_when_broken(rule, mutate, expected):
    draft = B.first_email(0)
    assert errors_for(draft) == []
    mutate(draft)
    errs = errors_for(draft)
    assert has(errs, expected), f"{rule}: expected {expected!r} in {errs}"


def test_word_range_boundaries():
    draft = B.first_email(0)
    n = len(draft["body"].split())
    assert 110 <= n <= 180
    filler = " ".join(["word"] * (181 - n))
    draft["body"] = draft["body"].replace("Resume attached.", f"Resume attached. {filler}.")
    assert has(errors_for(draft), "181 words (want 110-180)")


def test_attach_none_without_attachment_words_is_fine():
    draft = B.first_email(0, attach="none")
    draft["body"] = draft["body"].replace(" Resume attached.", " Thanks again for reading.")
    assert not has(errors_for(draft), "attached")


def test_ban_comes_from_lessons_file(ws):
    draft = B.first_email(0)
    draft["body"] = draft["body"].replace("Since you have", "I will circle back soon. Since you have")
    assert has(errors_for(draft), "BAN in me/lessons.md")
    (ws.me / "lessons.md").write_text("# My lessons\n", encoding="utf-8")
    ws.reset_rules()
    errs = errors_for(draft)
    assert not has(errs, "BAN in me/lessons.md")
    assert has(errs, 'AI-tell phrase "circle back"')  # still a universal AI tell


def test_question_mark_allowed_outside_first_emails():
    draft = {"to": "jordan.lee@example.com", "subject": "Re: Grocery Inventory Counts | Northgate Interest",
             "kind": "followup", "firm": "Northgate Partners", "name": "Jordan Lee", "attach": "none",
             "reply_to": "northgate-lee.json",
             "body": "Hi Jordan,\n\nI wanted to follow up on my note from last week about grocery inventory counts. "
                     "Would a short call sometime next week work for you? Happy to fit around your schedule.\n\n"
                     "Best,\nAlex"}
    errs = errors_for(draft)
    assert not has(errs, "direct question"), errs
    assert errs == []


# ---------- gate.run: batch rules ----------

def write_batch(folder, indexes):
    for i in indexes:
        B.write(folder, B.file_name(i), B.first_email(i))


def test_interest_line_may_repeat_across_a_batch(ws):
    folder = ws.drafts / "batch-1"
    write_batch(folder, range(6))
    drafts, failed = gate.run(folder)
    assert len(drafts) == 6
    assert failed == {}


def test_interest_line_allowance_comes_from_profile(ws):
    """Same batch, but the profile's interest line names a different field: the repeated audit wording is caught."""
    profile = ws.me / "profile.md"
    profile.write_text(profile.read_text(encoding="utf-8").replace(
        "interest_line: a strong interest in audit at <Firm>", "interest_line: a strong interest in tax at <Firm>"),
        encoding="utf-8")
    ws.reset_rules()
    folder = ws.drafts / "batch-1"
    write_batch(folder, range(6))
    _, failed = gate.run(folder)
    assert len(failed) == 6
    assert all(has(errs, 'phrase "interest in audit at" appears in 6 of 6 emails') for errs in failed.values())


def test_copied_non_house_sentence_is_caught(ws):
    folder = ws.drafts / "batch-1"
    write_batch(folder, range(6))
    copied = "Closing the books on our spring volleyball tournament taught me to chase every receipt."
    for i in (0, 3):
        d = B.first_email(i)
        d["body"] = d["body"].replace("\n\nI'm a current", f" {copied}\n\nI'm a current", 1)
        assert gate.check(d, B.file_name(i)) == []  # fine on its own
        B.write(folder, B.file_name(i), d)
    _, failed = gate.run(folder)
    assert set(failed) == {B.file_name(0), B.file_name(3)}
    for errs in failed.values():
        assert has(errs, "sentence reused in 2 emails")


def test_same_firm_identical_interest_sentence_is_caught(ws):
    """Two people at one firm would get the identical interest sentence: the gate flags it (PLAYBOOK batch rules)."""
    folder = ws.drafts / "batch-1"
    write_batch(folder, [0, 10])
    _, failed = gate.run(folder)
    assert set(failed) == {B.file_name(0), B.file_name(10)}
    assert all(has(errs, "sentence reused in 2 emails") for errs in failed.values())


def test_template_phrase_over_30_percent_is_caught(ws):
    folder = ws.drafts / "batch-1"
    write_batch(folder, range(6))
    for i in range(4):  # 4 of 6 > max(3, int(6 * 0.3))
        d = B.first_email(i)
        d["body"] = d["body"].replace("\n\nI'm a current", " Our treasury committee meets weekly.\n\nI'm a current", 1)
        B.write(folder, B.file_name(i), d)
    _, failed = gate.run(folder)
    assert set(failed) == {B.file_name(i) for i in range(4)}
    assert all(has(errs, 'phrase "treasury committee meets weekly" appears in 4 of 6 emails')
               for errs in failed.values())


def test_three_copies_stay_under_the_batch_limit(ws):
    folder = ws.drafts / "batch-1"
    write_batch(folder, range(6))
    for i in range(3):  # 3 of 6 is within the limit
        d = B.first_email(i)
        d["body"] = d["body"].replace("\n\nI'm a current", " Our treasury committee meets weekly.\n\nI'm a current", 1)
        B.write(folder, B.file_name(i), d)
    _, failed = gate.run(folder)
    assert failed == {}
