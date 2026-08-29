#!/usr/bin/env python3
"""Require durable documentation changes alongside implementation changes."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DOCUMENTATION_PREFIXES = ("docs/", "docs-site/docs/")
DOCUMENTATION_ROOT_SUFFIXES = (".md", ".mdx", ".rst")
DOCUMENTATION_FILES = {
    ".github/PULL_REQUEST_TEMPLATE.md",
    "AGENTS.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
}
ZERO_SHA = "0" * 40


def git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def changed_paths(base_ref: str | None) -> set[str]:
    base_ref = base_ref or None
    if base_ref == ZERO_SHA:
        base_ref = None

    if base_ref:
        return set(
            git("diff", "--name-only", "--diff-filter=ACMRD", f"{base_ref}...HEAD")
        )

    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            return set(
                git("diff", "--name-only", "--diff-filter=ACMRD", "HEAD^", "HEAD")
            )
        except subprocess.CalledProcessError:
            return set(
                git("show", "--pretty=", "--name-only", "--diff-filter=ACMRD", "HEAD")
            )

    return set(git("diff", "--name-only", "--diff-filter=ACMRD", "HEAD")) | set(
        git("ls-files", "--others", "--exclude-standard")
    )


def is_documentation(path: str) -> bool:
    normalized = Path(path).as_posix()
    if normalized in DOCUMENTATION_FILES:
        return True
    if normalized.startswith(DOCUMENTATION_PREFIXES):
        return normalized.lower().endswith(DOCUMENTATION_ROOT_SUFFIXES)
    return "/" not in normalized and normalized.lower().endswith(
        DOCUMENTATION_ROOT_SUFFIXES
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        default=os.environ.get("SAFEGLOSS_BASE_REF"),
        help="Git base commit/ref for CI; defaults to the local working tree.",
    )
    args = parser.parse_args()

    paths = changed_paths(args.base_ref)
    implementation_paths = sorted(path for path in paths if not is_documentation(path))
    documentation_paths = sorted(path for path in paths if is_documentation(path))

    if not implementation_paths:
        print("Documentation check: no implementation paths changed.")
        return 0
    if not documentation_paths:
        print(
            "Documentation check failed: implementation paths changed without "
            "a durable documentation update."
        )
        print(
            "Review docs/DOCUMENTATION_MAINTENANCE.md and update the governing documents."
        )
        print("Implementation paths:")
        for path in implementation_paths:
            print(f"  - {path}")
        return 1

    print("Documentation check passed: implementation and documentation paths changed.")
    for path in documentation_paths:
        print(f"  - {path}")
    print(
        "This path check is evidence only; semantic documentation review is still required."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
