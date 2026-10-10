"""run_send_day.py --order: plans chunks that each pass gate.run on their own. (The --list send mode is never run.)"""
import shutil
import sys

import pytest

import builders as B
import gate
import run_send_day as RSD

BAD = "zz-bad-semicolon.json"
ALREADY_SENT = "zz-already-sent.json"


def make_batch(ws, with_problems=True):
    folder = ws.drafts / "batch-1"
    for i in range(len(B.CONTACTS)):  # 10 firms plus a second Northgate contact
        B.write(folder, B.file_name(i), B.first_email(i))
    B.write(folder, "_BRIEF.json", {"note": "skipped: starts with an underscore"})
    if with_problems:
        bad = B.first_email(2, to="morgan.shaw2@example.com")
        bad["body"] = bad["body"].replace("going well.", "going well;")
        B.write(folder, BAD, bad)
        B.write(folder, ALREADY_SENT, B.first_email(3, to="riley.diaz2@example.com"))
        B.write(ws.sent, ALREADY_SENT, B.sent_record("riley.diaz2@example.com"))
    return folder


def run_order(monkeypatch, folder, chunk):
    monkeypatch.setattr(sys, "argv", ["run_send_day.py", str(folder), "--order", "--chunk", str(chunk)])
    with pytest.raises(SystemExit) as e:
        RSD.main()
    return e.value.code


def chunks_pass_gate_alone(ws, folder, chunks):
    for n, part in enumerate(chunks, 1):
        alone = ws.root / f"chunk-{n}"
        alone.mkdir()
        for name in part:
            shutil.copy2(folder / name, alone / name)
        drafts, failed = gate.run(alone)
        assert len(drafts) == len(part)
        assert failed == {}, f"chunk {n} fails the gate: {failed}"


def test_order_writes_chunks_that_each_pass_the_gate(ws, monkeypatch, capsys):
    folder = make_batch(ws)
    _, failed_together = gate.run(folder)
    assert failed_together  # the whole folder at once does not pass, so the planner has real work to do

    code = run_order(monkeypatch, folder, 4)
    out = capsys.readouterr().out
    assert code == 1  # one draft failed the gate on its own and was left out
    assert f"FAIL {BAD} (left out): contains semicolon" in out
    assert f"SKIP {ALREADY_SENT}: already in data/sent/" in out

    chunks = RSD.read_list(folder / "order.txt", 4)
    planned = [n for part in chunks for n in part]
    assert sorted(planned) == sorted(B.file_name(i) for i in range(len(B.CONTACTS)))
    assert len(planned) == len(set(planned))
    assert all(1 <= len(part) <= 4 for part in chunks)
    chunks_pass_gate_alone(ws, folder, chunks)

    # the two Northgate contacts share the identical interest sentence: never in the same send
    same_firm = {B.file_name(0), B.file_name(10)}
    assert not any(same_firm <= set(part) for part in chunks)


def test_order_file_format(ws, monkeypatch):
    folder = make_batch(ws, with_problems=False)
    assert run_order(monkeypatch, folder, 8) == 0
    text = (folder / "order.txt").read_text(encoding="utf-8")
    assert text.startswith("# chunk 1\n")
    chunks = RSD.read_list(folder / "order.txt", 8)
    assert text.count("# chunk") == len(chunks) >= 2
    chunks_pass_gate_alone(ws, folder, chunks)


def test_read_list_splits_on_comments_blank_lines_and_size(tmp_path):
    lst = tmp_path / "order.txt"
    lst.write_bytes("﻿# chunk 1\r\na.json\r\nb.json\r\nc.json\r\n\r\nd.json\n# chunk 3\ne.json\n".encode("utf-8"))
    assert RSD.read_list(lst, 2) == [["a.json", "b.json"], ["c.json"], ["d.json"], ["e.json"]]
