"""Fictional first emails and draft records for the test suite.

Every person, firm and address here is made up. Addresses use the reserved example.com domain. The emails follow
knowledge/PLAYBOOK.md (opener, one hook, one tie-in, a "why you" line, the interest line, the call ask) so that a
clean one passes gate.check and any batch of them passes gate.run.
"""
import json
import time
from pathlib import Path

SCHOOL = "Lakeshore State University"
INTEREST = "a strong interest in audit at {firm}"  # me/profile.md interest_line, with <Firm> filled in

# One dict per fictional contact. Hooks, tie-ins, "why you" lines and call asks never share a sentence, so a batch
# of these only repeats the house lines the gate allows.
CONTACTS = [
    dict(first="Jordan", last="Lee", firm="Northgate Partners", short="Northgate", topic="Grocery Inventory Counts",
         hook="Your article this spring on inventory counts at grocery chains was the first thing I noticed on your "
              "bio, mostly the point that a count is only as good as the cutoff around it.",
         tie="I keep the books for our club volleyball team, and closing our first full year of dues and travel is "
             "when I started to see why timing matters so much.",
         why="Since you have audited grocery clients for years, I can't think of a better person to hear from about "
             "what makes a count go well.",
         ask="how you got into retail audits"),
    dict(first="Casey", last="Park", firm="Ridgeway & Cole", short="Ridgeway", topic="Food Bank Grants",
         hook="I saw on the Ridgeway & Cole site that you spoke at a regional nonprofit finance forum about grant "
              "reporting for food banks, and the part about tracking restricted gifts was new to me.",
         tie="Volunteering with free tax preparation in our county last spring put me across the desk from families "
             "who rely on those same pantries.",
         why="Hearing how an auditor thinks about donor restrictions would help me picture what that work looks "
             "like week to week.",
         ask="what drew you to nonprofit clients"),
    dict(first="Morgan", last="Shaw", firm="Harborline Advisors", short="Harborline", topic="Hospital Payroll",
         hook="Before Harborline, you spent several years at a hospital system running payroll for nurses across "
              "three campuses, which is a part of your path I did not expect.",
         tie="Working part time as a bookkeeper at a neighborhood bakery, I do the monthly reconciliations, and even "
             "with a handful of employees the payroll side takes the most care.",
         why="That move from running the numbers to checking them is something I would really like to understand.",
         ask="about that switch from industry to audit"),
    dict(first="Riley", last="Diaz", firm="Alder & Finch", short="Alder", topic="Cherry Growers",
         hook="Your bio mentions the cooperative farm clients you have served around Traverse City since joining "
              "Alder & Finch, including several cherry growers along the bay.",
         tie="Harvest season and cash flow were dinner table topics growing up outside Grand Rapids, because half "
             "our neighbors grew fruit.",
         why="Few people see both the orchards and the ledgers, and that view is why I hoped to reach you.",
         ask="what audit season looks like for growers"),
    dict(first="Taylor", last="Brooks", firm="Meridian Lowe", short="Meridian", topic="Credit Union Sampling",
         hook="The podcast episode where you explained sampling for credit unions was a great listen on my drive "
              "home last weekend, especially the bit about picking which member files get pulled.",
         tie="Statistics was my favorite class this fall, and hearing it used on real member accounts made the "
             "formulas click for me.",
         why="Your way of making sampling plain is the reason I wanted to write to you.",
         ask="how you explain sampling to new staff"),
    dict(first="Avery", last="Grant", firm="Cobalt Street CPAs", short="Cobalt Street", topic="Duplicate Vendor Checks",
         hook="Cobalt Street posted your piece on fraud signs in church bookkeeping, and the example about duplicate "
              "vendor checks has stayed with me since I read it.",
         tie="Treasurer duties for our volleyball club taught me how easy it is to pay the same invoice twice when "
             "nobody compares receipts.",
         why="Since you train other firms on internal controls, you seem like the right person to hear from about "
             "getting started in this area.",
         ask="where fraud work fits into an audit career"),
    dict(first="Quinn", last="Hale", firm="Hartwell Brandt", short="Hartwell", topic="Auto Parts Suppliers",
         hook="Hartwell Brandt's Detroit office lists you on audits for auto parts suppliers, and your quote in a "
              "recent trade piece about tariffs and inventory valuation caught my attention.",
         tie="Growing up near the plants around Grand Rapids, I watched local suppliers ride every swing in car "
             "sales from one year to the next.",
         why="Few auditors sit that close to manufacturing, which is why I wanted to reach you in particular.",
         ask="how tariffs change the audit plan"),
    dict(first="Parker", last="Ford", firm="Brightwater Group", short="Brightwater", topic="Teaching to Assurance",
         hook="Your Brightwater profile says you taught high school math for a decade before moving into assurance "
              "work, a switch I have not seen often.",
         tie="Tutoring algebra at the campus learning center every Wednesday has shown me how much patience a good "
             "explanation takes.",
         why="Changing careers after teaching is a path I rarely hear about, and I would value your perspective on "
             "how it went.",
         ask="what made you leave the classroom"),
    dict(first="Rowan", last="Lane", firm="Pinecrest Audit", short="Pinecrest", topic="Restaurant Tip Reporting",
         hook="In your recent webinar for the county chamber, you walked owners through what auditors look for in "
              "restaurant tip reporting and why the records matter.",
         tie="Speaking Spanish with the kitchen crew at the bakery where I work has given me a feel for how tips get "
             "split by hand.",
         why="Your knack for making the rules clear to owners is what I hoped to learn about.",
         ask="about your work with restaurant owners"),
    dict(first="Emerson", last="Wade", firm="Silverbay Associates", short="Silverbay", topic="Lakeshore Cleanup",
         hook="A photo on the Silverbay news page shows you leading a volunteer trail cleanup along the lakeshore "
              "with your audit team this summer.",
         tie="Hiking those same dunes most weekends is how I clear my head after exams, so the photo felt familiar "
             "right away.",
         why="Seeing a team spend its time that way says a lot about the culture, and it is a big reason I wanted to "
             "write.",
         ask="more about the team"),
    # A second person at Northgate Partners: the identical interest sentence means the gate never lets this one
    # share a send with contact 0.
    dict(first="Jamie", last="Cruz", firm="Northgate Partners", short="Northgate", topic="Spring Food Drive",
         hook="Your name is on the Northgate news page as the coordinator of the firm's spring food drive, which "
              "gathered meals for shelters across the county.",
         tie="Sorting donations at our campus pantry on Friday mornings is one of my favorite parts of the week.",
         why="Learning how a busy audit group makes time for service, even during the winter rush, is high on my "
             "list.",
         ask="how the food drive came together"),
]


def stamp(days_ago=0.0):
    """address_check.checked_at format used by verify_addresses.py and read back by send_approved.py."""
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - days_ago * 86400))


def address(i):
    c = CONTACTS[i]
    return f"{c['first'].lower()}.{c['last'].lower()}@example.com"


def file_name(i):
    c = CONTACTS[i]
    return f"{c['short'].split()[0].lower()}-{c['last'].lower()}.json"


def body(i, standing="sophomore"):
    c = CONTACTS[i]
    interest = INTEREST.format(firm=c["firm"])
    return (f"Hi {c['first']},\n\n"
            f"Hope your week has been going well. {c['hook']} {c['tie']}\n\n"
            f"{c['why']}\n\n"
            f"I'm a current {standing} at {SCHOOL} with {interest}. I would love to hop on a call with you and hear "
            f"{c['ask']}. Resume attached.\n\n"
            "Thanks for your time.\n\n"
            "Best,\nAlex")


def first_email(i, **overrides):
    """A clean, verified, published first email to fictional contact i."""
    c = CONTACTS[i]
    name = f"{c['first']} {c['last']}"
    draft = {
        "to": address(i),
        "subject": f"{c['topic']} | {c['short']} Interest",
        "body": body(i),
        "firm": c["firm"],
        "name": name,
        "kind": "first",
        "practice": f"{c['firm']}:{name}",
        "attach": "resume",
        "email_confidence": "published",
        "email_source_url": f"https://www.example.com/team/{c['first'].lower()}-{c['last'].lower()}",
        "address_check": {"status": "verified", "detail": "printed on the team page", "checked_at": stamp()},
        "application": {"title": "Audit intern (fictional)", "url": "https://www.example.com/jobs", "est_open": "2027-01"},
    }
    draft.update(overrides)
    return draft


def write(folder, name, record):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def sent_record(to, firm="Example Firm", kind="first", sent_at=None, **extra):
    """A record as send_approved.py leaves it in data/sent/ (draft + sent_at + message_id)."""
    rec = {"to": to, "subject": "Test Thread | Example Interest", "body": "Hi,\n\nTest body.\n\nBest,\nAlex",
           "firm": firm, "name": "Sample Person", "kind": kind, "attach": "none", "email_confidence": "published",
           "sent_at": sent_at or time.strftime("%Y-%m-%d %H:%M:%S"),
           "message_id": f"<{kind}.{to.replace('@', '.at.')}@example.com>"}
    rec.update(extra)
    return rec
