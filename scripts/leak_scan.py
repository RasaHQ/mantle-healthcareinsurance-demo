"""Check the repository for content that must not be shared.

    python scripts/leak_scan.py [--terms /path/outside/the/repo/terms.txt]

Generic checks, always on:
- no tracked file that holds secrets or local tool settings (.env, .mcp.json, .claude/)
- no absolute home path (/Users/..., /home/...)
- no e-mail address outside the reserved example.com domain

With --terms, also a case-insensitive search for each line of the terms file, in every tracked
file and in the git history (commit messages, author names, branch names). Keep the terms file
outside the repository: the terms themselves are what must not be shared. Lines that start with
`re:` are regular expressions; other lines are plain text. Empty lines and lines that start with
`#` are skipped.

The exit code is 0 when nothing is found.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_FILES = (".env", ".mcp.json")
FORBIDDEN_DIRS = (".claude/",)
HOME_PATH = re.compile(r"/(Users|home)/[A-Za-z0-9._-]+")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ALLOWED_EMAIL_DOMAINS = ("example.com",)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def _tracked_files() -> list[str]:
    # Tracked and staged files, plus untracked files that are not ignored: everything a commit can add.
    files = _git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    return sorted(set(files))


def _patterns(terms_file: Path) -> list[tuple[str, re.Pattern[str]]]:
    patterns = []
    for line in terms_file.read_text().splitlines():
        term = line.strip()
        if not term or term.startswith("#"):
            continue
        regex = term[3:] if term.startswith("re:") else re.escape(term)
        patterns.append((term, re.compile(regex, re.IGNORECASE)))
    return patterns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--terms", type=Path, default=None, help="terms file, kept outside the repository")
    args = parser.parse_args()

    findings: list[str] = []
    files = _tracked_files()
    for name in files:
        if name in FORBIDDEN_FILES or name.endswith(FORBIDDEN_FILES) or name.startswith(FORBIDDEN_DIRS):
            findings.append(f"{name}: this file must not be in the repository")

    patterns = _patterns(args.terms) if args.terms else []
    if args.terms and args.terms.resolve().is_relative_to(REPO_ROOT):
        findings.append(f"{args.terms}: keep the terms file outside the repository")

    for name in files:
        path = REPO_ROOT / name
        if not path.is_file() or name == "scripts/leak_scan.py":
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if HOME_PATH.search(line):
                findings.append(f"{name}:{number}: absolute home path")
            for match in EMAIL.finditer(line):
                if match.group(1).lower() not in ALLOWED_EMAIL_DOMAINS:
                    findings.append(f"{name}:{number}: e-mail address outside example.com")
            for term, pattern in patterns:
                if pattern.search(line):
                    findings.append(f"{name}:{number}: term {term!r}")

    if patterns:
        try:
            history = _git("log", "--all", "--format=%an %s %b") + _git("branch", "--all", "--format=%(refname)")
        except subprocess.CalledProcessError:
            history = ""  # no commit yet
        for term, pattern in patterns:
            if pattern.search(history):
                findings.append(f"git history or branch names: term {term!r}")

    for finding in findings:
        print(finding)
    scope = f"{len(files)} files" + (f", {len(patterns)} terms" if patterns else ", no terms file")
    print(f"leak scan: {len(findings)} findings ({scope})")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
