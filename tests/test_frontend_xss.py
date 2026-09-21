"""
Static regression guard for front-end XSS.

The backend test suite cannot see template rendering, so this heuristic check
scans templates and shared JS for user-controlled fields interpolated into HTML
without being wrapped in ``escapeHtml(...)``.

It is intentionally conservative: known-safe contexts (textContent, canvas,
download filenames, locally generated values, etc.) are allowlisted. A failure
means a user-controlled value reaches an HTML sink unescaped.
"""
import re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "src" / "app" / "static"

FILES = sorted((STATIC_DIR / "templates").glob("*.html")) + sorted(
    (STATIC_DIR / "js").glob("*.js")
)

# Fields whose values originate from user input (username, session title, gym
# name, grade label, etc.).
USER_FIELDS = (
    "username|user_username|gym_name|gym_location|title|subtitle|notes|"
    "label|grade_label|display_name|color_hex|location"
)
INTERPOLATION_RE = re.compile(r"\$\{[^}]*\.(" + USER_FIELDS + r")\b")

# Contexts that are not HTML sinks or that are already handled.
SAFE_RE = re.compile(
    r"escapeHtml\(|textContent|window\.location|Number\(|renderAvatar|"
    r"\.dataset|\.download|fillText|canvas|weeks"
)


def find_unescaped_interpolations():
    findings = []
    for path in FILES:
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if INTERPOLATION_RE.search(line) and not SAFE_RE.search(line):
                findings.append(f"{path.relative_to(STATIC_DIR)}:{lineno}")
    return findings


def test_no_unescaped_user_fields_in_html_sinks():
    findings = find_unescaped_interpolations()
    assert findings == [], (
        "User-controlled fields interpolated into HTML without escapeHtml(): "
        + ", ".join(findings)
    )
