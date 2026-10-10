"""outcomes.py labels (the last line wins) and results.py rates on empty and small data."""
import datetime as dt
import json
import time

import pytest

import builders as B
import outcomes as O
import results as R


def sent_at(days_ago):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days_ago * 86400))


def add_sent(ws, file, **kw):
    to = kw.pop("to", f"{file.split('.')[0]}@example.com")
    B.write(ws.sent, file, B.sent_record(to, **kw))


def outcome_lines(ws):
    return [json.loads(l) for l in ws.outcomes.read_text(encoding="utf-8").splitlines() if l.strip()]


# ---------- outcomes.py label ----------

@pytest.fixture
def thread(ws):
    add_sent(ws, "northgate-lee.json", to=B.address(0), name="Jordan Lee", firm="Northgate Partners")
    add_sent(ws, "northgate-lee-fu1.json", to=B.address(0), name="Jordan Lee", firm="Northgate Partners",
             kind="followup", reply_to="northgate-lee.json")
    return ws


def test_label_appends_one_line(thread, capsys):
    O.main(["label", "northgate-lee.json", "replied", "warm", "reply"])
    assert outcome_lines(thread) == [{"file": "northgate-lee.json", "outcome": "replied", "note": "warm reply",
                                      "date": str(dt.date.today())}]
    assert "Labeled northgate-lee.json: replied." in capsys.readouterr().out


def test_last_label_wins(thread, capsys):
    O.main(["label", "northgate-lee", "replied"])
    O.main(["label", "northgate-lee", "call", "Tue 2pm"])
    assert "(was replied)" in capsys.readouterr().out
    assert [o["outcome"] for o in outcome_lines(thread)] == ["replied", "call"]
    latest = O.latest_outcomes()
    assert latest["northgate-lee.json"]["outcome"] == "call"
    assert latest["northgate-lee.json"]["note"] == "Tue 2pm"


def test_labeling_a_follow_up_labels_its_thread(thread):
    O.main(["label", "northgate-lee-fu1.json", "referral", "sent me to the campus team"])
    O.main(["label", "lee", "declined"])  # a name fragment matching both files of one thread
    assert {o["file"] for o in outcome_lines(thread)} == {"northgate-lee.json"}
    assert O.latest_outcomes()["northgate-lee.json"]["outcome"] == "declined"


def test_damaged_outcome_line_is_skipped(thread):
    thread.outcomes.write_text('{"file": "northgate-lee.json", "outcome": "ooo"}\nnot json\n\n', encoding="utf-8")
    O.main(["label", "northgate-lee", "call"])
    assert O.latest_outcomes()["northgate-lee.json"]["outcome"] == "call"
    assert len(O.read_outcomes()) == 2


def test_ambiguous_label_is_refused(thread):
    add_sent(thread, "ridgeway-park.json", to=B.address(1), name="Casey Park")
    with pytest.raises(SystemExit, match="matches 2 threads"):
        O.main(["label", "a", "call"])  # in both northgate-lee.json and ridgeway-park.json
    assert not thread.outcomes.exists()


def test_unknown_outcome_is_refused(thread):
    with pytest.raises(SystemExit):
        O.main(["label", "northgate-lee", "maybe"])
    assert not thread.outcomes.exists()


def test_label_with_nothing_sent(ws):
    with pytest.raises(SystemExit, match="data/sent/ is empty"):
        O.main(["label", "anyone", "call"])


def test_list_shows_latest_outcome(thread, capsys):
    O.main(["label", "northgate-lee", "replied"])
    O.main(["label", "northgate-lee", "call"])
    capsys.readouterr()
    O.main(["list", "--only", "call"])
    out = capsys.readouterr().out
    assert "northgate-lee.json" in out and "[+1 more sent]" in out and "call: 1" in out


# ---------- the 4-day no-reply rule ----------

def test_no_reply_after_four_days():
    first = {"_file": "a.json", "_date": dt.date(2026, 10, 1)}
    assert O.status_of(first, {}, today=dt.date(2026, 10, 4)) == "pending"
    assert O.status_of(first, {}, today=dt.date(2026, 10, 5)) == "no_reply"
    assert O.status_of(first, {"a.json": {"outcome": "call"}}, today=dt.date(2026, 10, 2)) == "call"


# ---------- results.py ----------

def test_results_on_empty_data(ws, capsys):
    R.main([])
    assert "No first emails old enough to count yet." in capsys.readouterr().out


def test_results_with_only_pending_mail(ws, capsys):
    add_sent(ws, "fresh.json", sent_at=sent_at(1))
    R.main([])
    assert "(1 pending, under 4 days old)" in capsys.readouterr().out


@pytest.fixture
def small(ws):
    add_sent(ws, "a-call.json", sent_at=sent_at(10), call_prep={"title": "Audit Senior"})
    add_sent(ws, "b-bounce.json", sent_at=sent_at(10), call_prep={"title": "Campus Recruiter"})
    add_sent(ws, "c-silent.json", sent_at=sent_at(10), call_prep={"title": "Managing Director"})
    add_sent(ws, "d-silent.json", sent_at=sent_at(4.1))
    add_sent(ws, "e-pending.json", sent_at=sent_at(2))
    add_sent(ws, "a-call-fu1.json", to="a-call@example.com", kind="followup", reply_to="a-call.json",
             sent_at=sent_at(3))
    with ws.outcomes.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"file": "a-call.json", "outcome": "replied"}) + "\n")
        f.write(json.dumps({"file": "a-call.json", "outcome": "call"}) + "\n")
        f.write(json.dumps({"file": "b-bounce.json", "outcome": "bounce"}) + "\n")
    return ws


def test_results_rows_and_tally(small):
    rows, pending = R.rows_of(dt.date.today())
    status = {d["_file"]: s for d, s in rows}
    assert status == {"a-call.json": "call", "b-bounce.json": "bounce", "c-silent.json": "no_reply",
                      "d-silent.json": "no_reply"}
    assert pending == 1
    t = R.tally(rows)
    assert t == {"sent": 4, "delivered": 3, "human": 1, "positive": 1, "callref": 1, "declined": 0, "bounce": 1,
                 "ooo": 0}


def test_results_report_on_small_data(small, capsys):
    R.main([])
    out = capsys.readouterr().out
    assert "=== Results: 4 first emails" in out
    assert "delivered 3 (bounced 1, out of office 0); 1 pending" in out
    assert "call or referral 1 (33%)" in out
    assert "none yet. Each needs 30+ delivered emails" in out


def test_results_write_lessons_with_too_little_data(small, capsys):
    before = (small.me / "lessons.md").read_text(encoding="utf-8")
    R.main(["--write-lessons"])
    assert "Nothing to write to me/lessons.md." in capsys.readouterr().out
    assert (small.me / "lessons.md").read_text(encoding="utf-8") == before


def test_segments():
    assert R.segment({"call_prep": {"title": "Campus Recruiter"}}) == "recruiter"
    assert R.segment({"call_prep": {"title": "Managing Director"}}) == "senior"
    assert R.segment({"call_prep": {"title": "Vice President, Audit"}}) == "mid"
    assert R.segment({"call_prep": {"title": "Audit Associate"}}) == "junior"
    assert R.segment({}) == "unknown"


def test_candidate_lesson_needs_n_and_z(ws):
    def rows(group, n, positive):
        return [({"grp": group}, "call" if i < positive else "no_reply") for i in range(n)]

    dims = {"grp": lambda d: d["grp"]}
    lessons = R.candidate_lessons(rows("hook", 40, 16) + rows("no hook", 40, 2), dims)
    assert [k for k, _ in lessons] == ["grp: 'hook' beat 'no hook'"]
    assert R.candidate_lessons(rows("hook", 29, 16) + rows("no hook", 40, 2), dims) == []  # n < 30
    assert R.candidate_lessons(rows("hook", 40, 5) + rows("no hook", 40, 4), dims) == []    # z < 2

    added, already = R.write_lessons(lessons)
    assert (added, already) == (1, 0)
    assert R.write_lessons(lessons) == (0, 1)
    text = (ws.me / "lessons.md").read_text(encoding="utf-8")
    assert text.count("[results] grp: 'hook' beat 'no hook'") == 1
