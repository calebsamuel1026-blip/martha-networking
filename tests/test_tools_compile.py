"""Every tool compiles on the running Python. CI runs 3.11 and SPEC promises 3.10+, so 3.12-only syntax (for
example a backslash inside an f-string expression) fails here before it reaches a user."""
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


@pytest.mark.parametrize("name", sorted(p.name for p in TOOLS.glob("*.py")))
def test_tool_compiles(name):
    path = TOOLS / name
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
