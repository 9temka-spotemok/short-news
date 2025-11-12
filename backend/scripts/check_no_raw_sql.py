"""
Static safeguard ensuring we do not reintroduce raw SQL into runtime code.

Scans `app/` for `.execute()` or `text()` calls with SQL statements.
Intended to run in CI (see `.github/workflows/ci.yml`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"

ALLOWED_PATHS = {
    # Add relative paths here if a specific module must contain raw SQL.
}

EXECUTE_PATTERN = re.compile(
    r"execute\([^#\n]*['\"]\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP)\s",
    re.IGNORECASE,
)
TEXT_PATTERN = re.compile(
    r"text\(\s*['\"]\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP)\s",
    re.IGNORECASE,
)


def _scan_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    matches: list[str] = []
    for pattern in (EXECUTE_PATTERN, TEXT_PATTERN):
        for match in pattern.finditer(content):
            line_number = content.count("\n", 0, match.start()) + 1
            line = content.splitlines()[line_number - 1].strip()
            matches.append(f"L{line_number}: {line}")
    return matches


def main() -> int:
    failures: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT)
        if str(rel) in ALLOWED_PATHS:
            continue
        findings = _scan_file(path)
        if findings:
            failures.append(
                f"{rel} contains potential raw SQL usage:\n  " + "\n  ".join(findings)
            )

    if failures:
        print("❌ Raw SQL guard detected issues:")
        for failure in failures:
            print(failure)
        print("\nAdd the file to ALLOWED_PATHS if this usage is intentional.")
        return 1

    print("✅ Raw SQL guard: no issues found in app/")
    return 0


if __name__ == "__main__":
    sys.exit(main())




