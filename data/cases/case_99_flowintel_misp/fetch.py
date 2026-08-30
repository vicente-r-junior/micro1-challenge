"""Fetch the tier-B case on demand instead of redistributing it.

The upstream file is AGPL-3.0. Copying it into this repository would put the
whole submission under that licence, and the challenge requires every component
to be used according to its terms (ground rule 3), so only the URL and the
pinned commit are committed here. Run this script to download it locally; the
result is git-ignored.

    python data/cases/case_99_flowintel_misp/fetch.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
META = json.loads((HERE / "case.json").read_text(encoding="utf-8"))
RAW = (
    "https://raw.githubusercontent.com/flowintel/flowintel/"
    f"{META['commit']}/app/case/case_misp.py"
)
TARGET = HERE / "legacy_app.py"


def main() -> int:
    print(f"fetching {RAW}")
    try:
        with urllib.request.urlopen(RAW, timeout=30) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1

    header = (
        "# Fetched from flowintel/flowintel at commit "
        f"{META['commit']}\n"
        "# Licence: AGPL-3.0. Not redistributed with this project; downloaded\n"
        "# locally for analysis only. See data/cases/case_99_flowintel_misp/case.json\n\n"
    )
    TARGET.write_text(header + body, encoding="utf-8")
    print(f"wrote {TARGET} ({len(body)} bytes, {len(body.splitlines())} lines)")
    print("note: this case is tier B — it cannot be executed in isolation, so it")
    print("      is analysed statically only. See docs/hard-case.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
