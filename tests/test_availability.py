"""availability.py: busy blocks from a fixture me/availability.json, and the PNG it renders."""
import datetime as dt
import json

import pytest

import availability as A

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
AVAILABILITY = {
    "window": [8, 17],
    "tz": "America/New_York",
    "recurring": [
        {"days": ["Tue", "Thu"], "start": "15:00", "end": "16:30", "label": "class"},
        {"days": ["Wed"], "start": "13:15", "end": "14:15", "every_other": True, "anchor": "2026-10-14",
         "label": "1:1"},
        {"days": "weekdays", "start": "7:00am", "end": "8:30am", "until": "2026-10-16", "label": "practice"},
    ],
    "one_off": [{"date": "2026-10-16", "start": "14:00", "end": "14:45", "label": "call"}],
}


@pytest.fixture
def avail(ws):
    (ws.me / "availability.json").write_text(json.dumps(AVAILABILITY), encoding="utf-8")
    return ws


def blocks(day, extra=()):
    return sorted((s, e) for s, e, _ in A.busy_on(dt.date.fromisoformat(day), AVAILABILITY, list(extra)))


@pytest.mark.parametrize("text, hours", [(8, 8.0), (8.5, 8.5), ("08:30", 8.5), ("8:30am", 8.5), ("3:05 PM", 15 + 5 / 60),
                                         ("12:00 am", 0.0), ("12pm", 12.0)])
def test_hours(text, hours):
    assert A.hours(text) == pytest.approx(hours)


def test_bad_time_and_day_are_errors():
    with pytest.raises(ValueError):
        A.hours("noonish")
    with pytest.raises(ValueError):
        A.day_set(["Funday"])


def test_busy_blocks():
    assert blocks("2026-10-13") == [(7.0, 8.5), (15.0, 16.5)]          # Tue: practice + class
    assert blocks("2026-10-14") == [(7.0, 8.5), (13.25, 14.25)]        # Wed, anchor week of the every-other 1:1
    assert blocks("2026-10-16") == [(7.0, 8.5), (14.0, 14.75)]         # Fri: one-off call
    assert blocks("2026-10-21") == []                                  # Wed, off week, practice ended
    assert blocks("2026-10-28") == [(13.25, 14.25)]                    # Wed, on week again
    assert blocks("2026-10-21", [A.parse_busy("2026-10-21", "12:00-12:45")]) == [(12.0, 12.75)]


def test_renders_png_to_data_folder(avail, capsys):
    A.main(["2026-10-14", "--weeks", "2", "--busy", "2026-10-21", "12:00-12:45"])
    out = avail.data / "availability-2026-10-12.png"  # snapped to the Monday
    assert out.exists() and out.read_bytes()[:8] == PNG_MAGIC and out.stat().st_size > 5000
    assert f"saved {out}" in capsys.readouterr().out


def test_renders_png_to_out_path(avail, tmp_path):
    out = tmp_path / "pics" / "open-times.png"
    A.main(["2026-10-19", "--out", str(out)])
    assert out.read_bytes()[:8] == PNG_MAGIC


def test_without_availability_file_uses_default_window(ws, tmp_path, capsys):
    out = tmp_path / "default.png"
    A.main(["2026-10-19", "--out", str(out)])
    assert out.read_bytes()[:8] == PNG_MAGIC
    assert "no me/availability.json yet" in capsys.readouterr().out


def test_bad_busy_argument_exits(avail):
    with pytest.raises(SystemExit):
        A.main(["2026-10-19", "--busy", "2026-10-21", "noon"])
