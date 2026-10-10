"""verify_addresses.py: the address decoders and the live re-check, with every fetch faked (no network)."""
import codecs
import json
import re
import sys
from types import SimpleNamespace

import pytest

import builders as B
import send_approved as S
import verify_addresses as V

ADDRESS = "dana.reyes@example.com"
CF_HEX = "5a3e3b343b74283f233f291a3f223b372a363f74393537"  # ADDRESS, Cloudflare-encoded with key 0x5a
SOURCE = "https://www.example.com/team"
BIO = "https://www.example.com/people/dana-reyes"


def cf_encode(text, key):
    return f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in text)


@pytest.fixture
def web(monkeypatch):
    """Fake pages by URL. A str is served as HTML with status 200; a tuple is (status, content type, bytes, text)."""
    pages, calls = {}, []

    def fake_get(url):
        calls.append(url)
        if url not in pages:
            raise ConnectionError(f"no fake page for {url}")
        page = pages[url]
        return page if isinstance(page, tuple) else (200, "text/html; charset=utf-8", page.encode(), page)

    monkeypatch.setattr(V, "_get", fake_get)
    return SimpleNamespace(pages=pages, calls=calls)


# ---------- pure decoders ----------

def test_cloudflare_known_vector():
    assert V.cf_decode(CF_HEX) == ADDRESS


@pytest.mark.parametrize("key", [0x01, 0x5A, 0xA7, 0xFF])
def test_cloudflare_round_trip(key):
    assert V.cf_decode(cf_encode("jordan.lee+audit@example.com", key)) == "jordan.lee+audit@example.com"


def test_cloudflare_bad_hex_decodes_to_nothing():
    assert V.cf_decode("zz12") == ""


@pytest.mark.parametrize("obfuscated", [
    "dana.reyes [at] example [dot] com",
    "dana.reyes[at]example[dot]com",
    "dana.reyes (at) example (dot) com",
    "dana.reyes {at} example {dot} com",
    "dana.reyes at example dot com",
    "Dana.Reyes [AT] Example [DOT] COM",
])
def test_at_dot_normalization(obfuscated):
    assert ADDRESS in V.normalize(f"Email: {obfuscated} | Phone: on request")


def test_normalize_is_fast_on_pages_with_long_blank_runs():
    # A real 2.7 MB site page with thousands of long whitespace runs hung the old regex for minutes.
    import time
    page = ("<div>" + " " * 600 + "\n" * 50 + "</div>") * 3000 + f"Email: {ADDRESS}"
    start = time.time()
    assert ADDRESS in V.normalize(page)
    assert time.time() - start < 2


def test_rot13_is_its_own_inverse():
    scrambled = codecs.encode(ADDRESS, "rot13")
    assert scrambled == "qnan.erlrf@rknzcyr.pbz"
    assert codecs.decode(scrambled, "rot13") == ADDRESS


def test_first_url():
    assert V.first_url(f"see {SOURCE}/dana, page 2") == f"{SOURCE}/dana"
    assert V.first_url("no link here") is None


# ---------- fetch_text decodes every form of a printed address ----------

PRINTED_FORMS = {
    "plain": f"<p>Dana Reyes, Audit Manager, {ADDRESS}</p>",
    "mailto": f'<a href="mailto:{ADDRESS}">Email Dana</a>',
    "percent-encoded mailto": '<a href="mailto:dana.reyes%40example.com">Email Dana</a>',
    "html entity": "<p>dana.reyes&#64;example.com</p>",
    "cloudflare data-cfemail": f'<a href="/cdn-cgi/l/email-protection" class="__cf_email__" '
                               f'data-cfemail="{CF_HEX}">[email&#160;protected]</a>',
    "cloudflare email-protection#hex": f'<a href="/cdn-cgi/l/email-protection#{cf_encode(ADDRESS, 0x21)}">Email</a>',
    "rot13": '<span class="contact">qnan.erlrf@rknzcyr.pbz</span>',
    "[at] [dot]": "<p>dana.reyes [at] example [dot] com</p>",
}


@pytest.mark.parametrize("form", list(PRINTED_FORMS))
def test_check_verifies_every_printed_form(web, form):
    web.pages[SOURCE] = f"<html><body><h1>Our team</h1>{PRINTED_FORMS[form]}</body></html>"
    status, detail = V.check({"to": ADDRESS, "name": "Dana Reyes", "email_source_url": SOURCE})
    assert status == "verified", detail
    assert web.calls == [SOURCE]


def test_fetch_text_includes_decoded_cloudflare_addresses(web):
    web.pages[SOURCE] = f'<a data-cfemail="{CF_HEX}">[email protected]</a>'
    text, info = V.fetch_text(SOURCE)
    assert ADDRESS in text and info == "HTTP 200"


def test_fetch_text_caches_each_url(web):
    web.pages[SOURCE] = f"<p>{ADDRESS}</p>"
    V.fetch_text(SOURCE)
    V.fetch_text(SOURCE)
    assert web.calls == [SOURCE]


def test_pdf_source(web):
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), f"Audit team contacts: Dana Reyes {ADDRESS}")
    raw = doc.tobytes()
    web.pages[SOURCE + ".pdf"] = (200, "application/pdf", raw, "")
    status, detail = V.check({"to": ADDRESS, "name": "Dana Reyes", "email_source_url": SOURCE + ".pdf"})
    assert status == "verified", detail


def test_unreadable_pdf_is_source_down(web):
    web.pages[SOURCE + ".pdf"] = (200, "application/pdf", b"not a pdf at all", "")
    status, detail = V.check({"to": ADDRESS, "email_source_url": SOURCE + ".pdf"})
    assert status == "source-down"


# ---------- check() statuses ----------

def test_not_printed(web):
    web.pages[SOURCE] = "<p>someone.else@example.com</p>"
    status, detail = V.check({"to": ADDRESS, "email_source_url": SOURCE})
    assert status == "not-printed" and ADDRESS in detail


def test_no_source():
    assert V.check({"to": ADDRESS, "email_source_url": ""})[0] == "no-source"


def test_http_error_is_source_down(web):
    web.pages[SOURCE] = (404, "text/html", b"", "")
    status, detail = V.check({"to": ADDRESS, "email_source_url": SOURCE})
    assert status == "source-down" and "HTTP 404" in detail


def test_network_error_is_source_down(web):
    status, detail = V.check({"to": ADDRESS, "email_source_url": SOURCE})  # no fake page: fetch raises
    assert status == "source-down" and "unreachable" in detail


def test_bio_still_names_the_person(web):
    web.pages[SOURCE] = f"<p>{ADDRESS}</p>"
    web.pages[BIO] = "<h1>Dana Reyes</h1><p>Audit manager.</p>"
    status, detail = V.check({"to": ADDRESS, "name": "Dana Reyes", "email_source_url": SOURCE, "bio_url": BIO})
    assert status == "verified" and "bio live" in detail


def test_bio_without_the_name_means_they_may_have_left(web):
    web.pages[SOURCE] = f"<p>{ADDRESS}</p>"
    web.pages[BIO] = "<h1>Morgan Shaw</h1>"
    status, _ = V.check({"to": ADDRESS, "name": "Dana Reyes", "email_source_url": SOURCE, "bio_url": BIO})
    assert status == "bio-missing-name"


def test_bio_down(web):
    web.pages[SOURCE] = f"<p>{ADDRESS}</p>"
    web.pages[BIO] = (410, "text/html", b"", "")
    status, _ = V.check({"to": ADDRESS, "name": "Dana Reyes", "email_source_url": SOURCE,
                         "call_prep": {"bio_url": BIO}})
    assert status == "bio-down"


# ---------- main() writes address_check, and the sender accepts it ----------

def _verify_folder(ws, web, monkeypatch, extra_args=()):
    folder = ws.drafts / "batch-1"
    draft = B.first_email(0)
    draft.pop("address_check")
    B.write(folder, "northgate-lee.json", draft)
    B.write(folder, "_notes.json", {"to": "skip.me@example.com"})
    B.write(folder, "northgate-lee-fu1.json", B.first_email(0, kind="followup", reply_to="northgate-lee.json"))
    web.pages[draft["email_source_url"]] = f"<p>Jordan Lee, Audit Senior, {draft['to']}</p>"
    monkeypatch.setattr(sys, "argv", ["verify_addresses.py", str(folder), *extra_args])
    V.main()
    return folder


def test_main_writes_address_check(ws, web, monkeypatch, capsys):
    folder = _verify_folder(ws, web, monkeypatch)
    d = json.loads((folder / "northgate-lee.json").read_text(encoding="utf-8"))
    assert d["address_check"]["status"] == "verified"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", d["address_check"]["checked_at"])
    assert "address_check" not in json.loads((folder / "_notes.json").read_text(encoding="utf-8"))
    fu = json.loads((folder / "northgate-lee-fu1.json").read_text(encoding="utf-8"))  # follow-ups are skipped
    assert fu["address_check"]["detail"] == "printed on the team page"
    assert "verified: 1" in capsys.readouterr().out
    # send_approved.py reads the stamp back and lets the address through
    B.write(ws.approved, "northgate-lee.json", d)
    problems, _ = S.recipient_guards(S.load_drafts(S.load_profile_safe()))
    assert problems == []


def test_main_dry_writes_nothing(ws, web, monkeypatch):
    folder = _verify_folder(ws, web, monkeypatch, ["--dry"])
    d = json.loads((folder / "northgate-lee.json").read_text(encoding="utf-8"))
    assert "address_check" not in d
