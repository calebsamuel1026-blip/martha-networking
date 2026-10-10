"""capture.py: dated notes and BAN lines appended to me/lessons.md, never twice, and read back by the gate."""
import datetime as dt

import pytest

import builders as B
import capture
import gate


def lines(ws):
    return (ws.me / "lessons.md").read_text(encoding="utf-8").splitlines()


def test_note_appends_a_dated_line(ws, capsys):
    capture.main(["note", "one shared interest per email,", "not two"])
    assert lines(ws)[-1] == f"- {dt.date.today()} one shared interest per email, not two"
    assert "Saved to me/lessons.md." in capsys.readouterr().out


def test_note_is_never_saved_twice(ws):
    assert capture.note("Use the   interest line word for word") == "Saved to me/lessons.md."
    assert capture.note("use the interest line WORD for word") == "Already in me/lessons.md."
    assert sum("interest line" in l for l in lines(ws)) == 1


def test_ban_appends_a_ban_line(ws, capsys):
    capture.main(["ban", '"grab', 'coffee"'])
    assert lines(ws)[-1] == "BAN: grab coffee"
    assert 'Banned "grab coffee"' in capsys.readouterr().out


def test_ban_is_never_saved_twice(ws):
    assert capture.ban("Grab Coffee").startswith("Banned")
    assert capture.ban("grab   coffee") == "Already banned."
    assert capture.ban("circle back") == "Already banned."  # the dated BAN line from the fixture counts too
    assert sum(l.startswith("BAN:") for l in lines(ws)) == 1


def test_append_adds_a_missing_newline(ws):
    (ws.me / "lessons.md").write_text("# My lessons", encoding="utf-8")
    capture.ban("pick your brain")
    assert lines(ws) == ["# My lessons", "BAN: pick your brain"]


def test_empty_ruling_is_refused(ws):
    with pytest.raises(SystemExit):
        capture.note("   ")
    with pytest.raises(SystemExit):
        capture.ban('""')


def test_no_me_folder(ws, monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "ME", tmp_path / "missing-me")
    with pytest.raises(SystemExit, match="No me/ folder yet"):
        capture.note("anything")


def test_gate_blocks_a_newly_banned_phrase(ws):
    d = B.first_email(0)
    d["body"] = d["body"].replace("I keep the books", "Over a quick coffee chat once, I learned that I keep the books")
    assert gate.check(d, "x.json") == []
    capture.ban("coffee chat")
    ws.reset_rules()
    assert 'banned phrase "coffee chat" (BAN in me/lessons.md)' in gate.check(d, "x.json")
