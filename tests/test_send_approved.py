"""send_approved.py guards, always in DRY RUN. --send is never passed, and smtplib.SMTP_SSL raises (conftest)."""
import json
import smtplib
import socket
import sys
import time

import pytest

import builders as B
import send_approved as S


def stage(ws, *named_drafts):
    """Put drafts in data/approved/ and load them exactly as the sender does."""
    for name, d in named_drafts:
        B.write(ws.approved, name, d)
    return S.load_drafts(S.load_profile_safe())


def problems_for(ws, *named_drafts):
    problems, _ = S.recipient_guards(stage(ws, *named_drafts))
    return problems


def add_sent(ws, name, record):
    B.write(ws.sent, name, record)


def has(problems, fragment):
    return any(fragment in p for p in problems)


def dry_run(monkeypatch, capsys):
    """Run send_approved.py with no flags (dry run). Returns (exit code or None, output)."""
    monkeypatch.setattr(sys, "argv", ["send_approved.py"])
    code = None
    try:
        S.main()
    except SystemExit as e:
        code = e.code
    out = capsys.readouterr()
    return code, out.out + out.err


def test_smtp_is_disabled_in_tests():
    with pytest.raises(AssertionError):
        smtplib.SMTP_SSL("smtp.gmail.com", 465)


def test_network_is_disabled_in_tests(offline):
    import run_send_day
    assert run_send_day.online() is False  # its socket.create_connection hits the conftest guard
    with socket.socket() as s, pytest.raises(OSError):
        s.connect(("smtp.gmail.com", 465))
    assert len(offline) == 2
    offline.clear()  # both attempts were expected here


def test_clean_first_email_has_no_problems(ws):
    assert problems_for(ws, ("northgate-lee.json", B.first_email(0))) == []


# ---------- published only ----------

@pytest.mark.parametrize("confidence, shown", [("pattern", "'pattern'"), ("inferred", "'inferred'"),
                                               ("", "'missing'"), (None, "'none'")])
def test_non_published_confidence_is_blocked(ws, confidence, shown):
    problems = problems_for(ws, ("northgate-lee.json", B.first_email(0, email_confidence=confidence)))
    assert has(problems, f"email_confidence is {shown}")


def test_missing_confidence_is_blocked(ws):
    d = B.first_email(0)
    d.pop("email_confidence")
    assert has(problems_for(ws, ("northgate-lee.json", d)), "email_confidence is 'missing'")


# ---------- fresh address_check ----------

def test_stale_address_check_is_blocked(ws):
    d = B.first_email(0, address_check={"status": "verified", "detail": "", "checked_at": B.stamp(days_ago=3.5)})
    assert has(problems_for(ws, ("northgate-lee.json", d)), "older than 3 days")


def test_address_check_inside_three_days_passes(ws):
    d = B.first_email(0, address_check={"status": "verified", "detail": "", "checked_at": B.stamp(days_ago=2.5)})
    assert problems_for(ws, ("northgate-lee.json", d)) == []


def test_missing_address_check_is_blocked(ws):
    d = B.first_email(0)
    d.pop("address_check")
    assert has(problems_for(ws, ("northgate-lee.json", d)), "address not verified in the last 3 days (never checked)")


@pytest.mark.parametrize("status", ["not-printed", "source-down", "bio-missing-name", "no-source"])
def test_failed_address_check_is_blocked(ws, status):
    d = B.first_email(0, address_check={"status": status, "detail": "", "checked_at": B.stamp()})
    assert has(problems_for(ws, ("northgate-lee.json", d)), f"({status})")


def test_unreadable_checked_at_is_blocked(ws):
    d = B.first_email(0, address_check={"status": "verified", "detail": "", "checked_at": "last Tuesday"})
    assert has(problems_for(ws, ("northgate-lee.json", d)), "older than 3 days")


# ---------- never two first emails to one address ----------

def test_second_first_email_to_same_address_is_blocked(ws):
    add_sent(ws, "old-lee.json", B.sent_record("Jordan.Lee@example.com", firm="Northgate Partners"))
    problems = problems_for(ws, ("northgate-lee.json", B.first_email(0)))
    assert has(problems, "jordan.lee@example.com already got a first email (old-lee.json)")


def test_same_address_twice_in_one_batch_is_blocked(ws):
    problems = problems_for(ws, ("a-lee.json", B.first_email(0)), ("b-lee.json", B.first_email(0)))
    assert has(problems, "b-lee.json: jordan.lee@example.com is also in a-lee.json")


def test_follow_up_to_an_emailed_address_is_fine(ws):
    add_sent(ws, "northgate-lee.json", B.sent_record(B.address(0), firm="Northgate Partners"))
    fu = B.first_email(0, kind="followup", reply_to="northgate-lee.json", attach="none")
    assert problems_for(ws, ("northgate-lee-fu1.json", fu)) == []


# ---------- per-firm cap (me/strategy.md "max people per firm: 3") ----------

def _three_sent_at_example_com(ws):
    for who in ("morgan.shaw", "riley.diaz", "taylor.brooks"):
        add_sent(ws, f"example-{who}.json", B.sent_record(f"{who}@example.com", firm="Example Firm"))


def test_fourth_person_at_a_firm_domain_is_blocked(ws):
    _three_sent_at_example_com(ws)
    problems = problems_for(ws, ("northgate-lee.json", B.first_email(0)))
    assert has(problems, "(example.com) already has 3 people emailed; the per-firm cap is 3")


def test_cap_counts_subdomains_as_the_same_firm(ws):
    _three_sent_at_example_com(ws)
    d = B.first_email(0, to="jordan.lee@audit.example.com")
    assert has(problems_for(ws, ("northgate-lee.json", d)), "per-firm cap is 3")


def test_cap_is_per_domain(ws):
    _three_sent_at_example_com(ws)
    d = B.first_email(0, to="jordan.lee@example.org")
    assert problems_for(ws, ("northgate-lee.json", d)) == []


def test_fourth_person_counting_this_batch_is_blocked(ws):
    add_sent(ws, "example-shaw.json", B.sent_record("morgan.shaw@example.com"))
    batch = [("1-lee.json", B.first_email(0)), ("2-park.json", B.first_email(1)), ("3-diaz.json", B.first_email(3))]
    problems = problems_for(ws, *batch)
    assert problems == [p for p in problems if p.startswith("3-diaz.json")]  # 1 sent + 2 in the batch, then capped
    assert has(problems, "already has 3 people emailed; the per-firm cap is 3")


def test_cap_comes_from_strategy(ws):
    _three_sent_at_example_com(ws)
    (ws.me / "strategy.md").write_text("max people per firm: 4\n", encoding="utf-8")
    assert problems_for(ws, ("northgate-lee.json", B.first_email(0))) == []


def test_cap_defaults_to_three_without_strategy(ws):
    _three_sent_at_example_com(ws)
    (ws.me / "strategy.md").unlink()
    assert has(problems_for(ws, ("northgate-lee.json", B.first_email(0))), "per-firm cap is 3")


# ---------- at most 5 first emails to one firm per batch ----------

def test_sixth_first_email_to_one_firm_in_a_batch_is_blocked(ws):
    (ws.me / "strategy.md").write_text("max people per firm: 10\n", encoding="utf-8")
    batch = [(f"{i:02d}-{B.file_name(i)}", B.first_email(i)) for i in range(6)]
    problems = problems_for(ws, *batch)
    burst = [p for p in problems if "more than 5 first emails" in p]
    assert len(burst) == 1 and burst[0].startswith(batch[5][0])
    assert problems == burst


def test_five_first_emails_to_one_firm_is_fine(ws):
    (ws.me / "strategy.md").write_text("max people per firm: 10\n", encoding="utf-8")
    assert problems_for(ws, *[(B.file_name(i), B.first_email(i)) for i in range(5)]) == []


# ---------- threading ----------

def test_follow_up_without_reply_to_is_blocked(ws):
    fu = B.first_email(0, kind="followup", attach="none")
    assert has(problems_for(ws, ("fu.json", fu)), "a followup must name the sent email it answers (reply_to)")


def test_reply_without_reply_to_is_blocked(ws):
    reply = B.first_email(0, kind="reply", attach="none")
    assert has(problems_for(ws, ("reply.json", reply)), "a reply must name the sent email it answers")


def test_reply_to_must_exist_in_sent(ws):
    fu = B.first_email(0, kind="followup", attach="none", reply_to="missing.json")
    assert has(problems_for(ws, ("fu.json", fu)), "reply_to missing.json not found in data/sent/")


def test_in_reply_to_alone_is_enough(ws):
    reply = B.first_email(0, kind="reply", attach="none", in_reply_to="<their-id@example.com>")
    assert problems_for(ws, ("reply.json", reply)) == []


def test_build_message_threads_under_the_original(ws):
    orig = B.sent_record(B.address(0), subject="Grocery Inventory Counts | Northgate Interest",
                         message_id="<first.northgate-lee@example.com>")
    add_sent(ws, "northgate-lee.json", orig)
    fu = B.first_email(0, kind="followup", attach="none", reply_to="northgate-lee.json", subject="Following up")
    (_, d), = stage(ws, ("fu.json", fu))
    msg = S.build_message(d, {"GMAIL_ADDRESS": "alex.sample@example.com"}, S.load_profile_safe())
    assert msg["In-Reply-To"] == "<first.northgate-lee@example.com>"
    assert msg["References"] == "<first.northgate-lee@example.com>"
    assert msg["Subject"] == "Re: Grocery Inventory Counts | Northgate Interest"
    assert msg["From"] == "Alex Sample <alex.sample@example.com>"
    assert not list(msg.iter_attachments())


def test_in_reply_to_overrides_the_thread_header(ws):
    add_sent(ws, "northgate-lee.json", B.sent_record(B.address(0), message_id="<ours@example.com>"))
    reply = B.first_email(0, kind="reply", attach="none", reply_to="northgate-lee.json",
                          in_reply_to="<theirs@example.com>")
    (_, d), = stage(ws, ("reply.json", reply))
    msg = S.build_message(d, {"GMAIL_ADDRESS": "alex.sample@example.com"}, S.load_profile_safe())
    assert msg["In-Reply-To"] == "<theirs@example.com>" and msg["References"] == "<theirs@example.com>"


def test_first_email_attaches_the_resume_and_unwraps(ws):
    d0 = B.first_email(0)
    d0["body"] = d0["body"].replace("mostly the point", "mostly\nthe point")
    (_, d), = stage(ws, ("northgate-lee.json", d0))
    msg = S.build_message(d, {"GMAIL_ADDRESS": "alex.sample@example.com"}, S.load_profile_safe())
    names = [a.get_filename() for a in msg.iter_attachments()]
    assert names == ["Alex-Sample-Resume.pdf"]
    text = msg.get_body(("plain",)).get_content()
    assert "mostly the point" in text and "Best,\nAlex" in text
    assert text.rstrip().endswith("Alex Sample\nLakeshore State University | Accounting | Class of 2029")


def test_missing_resume_is_blocked(ws):
    (ws.me / "resume" / "Alex-Sample-Resume.pdf").unlink()
    assert has(problems_for(ws, ("northgate-lee.json", B.first_email(0))), "no résumé PDF")


# ---------- daily cap and bounce guard ----------

def _published_firsts(ws, n, bounced=0, days_ago=2):
    when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days_ago * 86400))
    for i in range(n):
        add_sent(ws, f"p{i:02d}.json", B.sent_record(f"person{i}@example.net", sent_at=when))
    with ws.outcomes.open("w", encoding="utf-8") as f:
        for i in range(bounced):
            f.write(json.dumps({"file": f"p{i:02d}.json", "outcome": "bounce"}) + "\n")


def test_daily_cap_defaults_and_env(ws):
    _published_firsts(ws, 10)
    assert S.daily_cap({}, quiet=True) == (40, 0)
    assert S.daily_cap({"DAILY_CAP": "20"}, quiet=True) == (20, 0)
    assert S.daily_cap({"DAILY_CAP": "20"}, override=5, quiet=True) == (5, 0)


def test_bounce_guard_lowers_the_cap(ws):
    _published_firsts(ws, 25, bounced=1)  # 4%
    assert S.daily_cap({}, quiet=True)[0] == 15


def test_bounce_guard_pauses_sending(ws):
    _published_firsts(ws, 10, bounced=1)  # 10%
    assert S.daily_cap({}, override=40, quiet=True)[0] == 0


def test_sent_today_counts_cold_mail_only(ws):
    add_sent(ws, "a.json", B.sent_record("a.person@example.com"))
    add_sent(ws, "b.json", B.sent_record("b.person@example.com", kind="reply", reply_to="a.json"))
    assert S.daily_cap({}, quiet=True) == (40, 1)


# ---------- the dry run end to end ----------

def test_dry_run_sends_nothing(ws, monkeypatch, capsys):
    stage(ws, ("northgate-lee.json", B.first_email(0)), ("ridgeway-park.json", B.first_email(1)))
    code, out = dry_run(monkeypatch, capsys)
    assert code is None, out
    assert "2 email(s) ready. Nothing was sent." in out
    assert "--send will refuse" in out  # no Gmail settings in the test me/
    assert sorted(p.name for p in ws.approved.iterdir()) == ["northgate-lee.json", "ridgeway-park.json"]
    assert list(ws.sent.iterdir()) == []


def test_dry_run_reports_guard_blocks(ws, monkeypatch, capsys):
    stage(ws, ("northgate-lee.json", B.first_email(0, email_confidence="pattern")))
    code, out = dry_run(monkeypatch, capsys)
    assert code == "\nNothing was sent."
    assert "BLOCKED northgate-lee.json: email_confidence is 'pattern'" in out
    assert (ws.approved / "northgate-lee.json").exists() and list(ws.sent.iterdir()) == []


def test_dry_run_runs_the_gate(ws, monkeypatch, capsys):
    d = B.first_email(0)
    d["body"] = d["body"].replace("going well.", "going well;")
    stage(ws, ("northgate-lee.json", d))
    code, out = dry_run(monkeypatch, capsys)
    assert "failed the pre-send gate. Nothing was sent." in str(code)
    assert "BLOCKED northgate-lee.json: contains semicolon" in out


def test_dry_run_with_nothing_approved(ws, monkeypatch, capsys):
    code, out = dry_run(monkeypatch, capsys)
    assert code is None
    assert "No approved emails in data/approved/." in out
    assert "Alex-Sample-Resume.pdf" in out and "app password MISSING" in out


def test_invalid_json_blocks_everything(ws, monkeypatch, capsys):
    (ws.approved / "broken.json").write_text("{not json", encoding="utf-8")
    code, _ = dry_run(monkeypatch, capsys)
    assert str(code).startswith("BLOCKED broken.json: not valid JSON")
