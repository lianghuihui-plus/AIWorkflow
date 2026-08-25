#!/usr/bin/env python3
"""Sync validator source into skill-local tool directories."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "validator_source" / "validate.py"
TARGETS = [
    ROOT / "wf" / "tools" / "validate.py",
    ROOT / "wf-status" / "tools" / "validate.py",
]


def check() -> list[Path]:
    mismatched: list[Path] = []
    for target in TARGETS:
        if not target.exists() or not filecmp.cmp(SOURCE, target, shallow=False):
            mismatched.append(target)
    return mismatched


def sync() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing validator source: {SOURCE}")
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify targets match source without writing")
    args = parser.parse_args()

    if args.check:
        mismatched = check()
        if mismatched:
            for target in mismatched:
                print(f"out of sync: {target.relative_to(ROOT)}")
            return 1
        print("validator tools are in sync")
        return 0

    sync()
    print("validator tools synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
