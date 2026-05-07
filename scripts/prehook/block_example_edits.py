#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys


def main(argv: list[str]) -> int:
    blocked = [path for path in argv[1:] if Path(path).parts[:2] == ("src", "examples")]
    if not blocked:
        return 0

    sys.stderr.write(
        "Example files under src/examples are managed separately and must not be committed:\n"
    )
    for path in blocked:
        sys.stderr.write(f"  - {path}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
