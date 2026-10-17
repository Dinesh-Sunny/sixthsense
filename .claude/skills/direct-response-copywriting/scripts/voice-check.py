#!/usr/bin/env python3
"""Enforce VOICE.md on user-facing copy in the web app.

VOICE.md (repo root) is the single source of truth for copy. This checks the mechanical rules from its
frontmatter against prose in UI files (JSX text, prose-like string literals, and template literals):

  banned words (vocabulary.banned) · wrong product-name forms (naming.never, plus a capitalised name)
  em/en dashes (voice.dashes: none) · exclamation marks (voice.exclamation_marks: 0) · emoji (voice.emoji: false)

  voice-check.py check [ROOT]      exit 1 if any UI file breaks a rule (used by `pnpm copy:check`)
  voice-check.py lint [FILE...]    report violations (default: all non-vendored UI files)
  voice-check.py hook              PostToolUse mode (stdin JSON): lint the edited UI file, exit 2 on violations

Allow a deliberate exception on one line with a comment containing `voice-allow: <reason>`. Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
VOICE = Path("VOICE.md")
# Words kept in plain .ts copy modules (email subjects, consent banner) are named *-copy.ts.
UI_GLOBS = ("apps/web/src/**/*.tsx", "packages/*/src/**/*.tsx", "apps/web/src/**/*-copy.ts")
# Same vendored set as design-tokens.py: generated/third-party code isn't our copy.
VENDORED = re.compile(
    r"/components/ui/|/design/_preview|/components/animate-ui/|/components/assistant-ui/elements/"
)
ALLOW = "voice-allow:"
REQUIRED_KEYS = ("banned", "never", "dashes", "exclamation_marks", "emoji")

# `>` that closes a tag (not an arrow `=>`), then text with a letter, up to the next tag or expression.
JSX_TEXT = re.compile(r"(?<!=)>([^<>{}]*[A-Za-z][^<>{}]*)(?=[<{])")
EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿⭐⭕]")
DASHES = re.compile("[–—]")
EXCLAIM = re.compile(r"[A-Za-z0-9)\]]!+(?=\s|$|[\"'`])")
CLASS_WORD = re.compile(r"[a-z0-9:\-\[\]/!.%()_]+")
# A quote opens a JS string only after an operator/opener; in JSX text, quotes and apostrophes are prose.
STRING_OPENER = set("=(,:[{?+!&|;<>")


@dataclass(frozen=True)
class Span:
    text: str
    start: int  # offset into the file


# ----------------------------------------------------------------------------- settings


def frontmatter(root: Path) -> str:
    path = root / VOICE
    if not path.exists():
        sys.exit(f"voice-check: {VOICE} not found at {root}")
    m = re.match(r"---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
    if not m:
        sys.exit(f"voice-check: {VOICE} has no YAML frontmatter")
    fm = m.group(1)
    missing = [k for k in REQUIRED_KEYS if not re.search(rf"(?m)^\s*{k}:", fm)]
    if missing:
        sys.exit(
            f"voice-check: {VOICE} frontmatter is missing {', '.join(missing)} (rules would silently turn off)"
        )
    return fm


def flow_list(fm: str, key: str) -> list[str]:
    """Read an inline list like `banned: ["a", "b"]` (JSON-compatible flow sequence)."""
    m = re.search(rf"(?m)^\s*{key}:\s*(\[[^\]\n]*\])", fm)  # stop at the first ], so trailing # comments are ignored
    if not m:
        sys.exit(f'voice-check: {VOICE} key "{key}" must be an inline list, e.g. {key}: ["a", "b"]')
    try:
        return [str(v) for v in json.loads(m.group(1))]
    except json.JSONDecodeError as e:
        sys.exit(f'voice-check: {VOICE} key "{key}" is not a valid inline list ({e})')


def scalar(fm: str, key: str) -> str:
    m = re.search(rf'(?m)^\s*{key}:\s*"?([^"#\n]*?)"?\s*(#.*)?$', fm)
    return m.group(1).strip() if m else ""


def load_rules(root: Path) -> dict[str, object]:
    fm = frontmatter(root)
    product = scalar(fm, "product")
    never = flow_list(fm, "never")
    if product and product.islower():
        never.append(product.capitalize())
    return {
        "banned": flow_list(fm, "banned"),
        "never": sorted(set(never)),
        "no_dashes": scalar(fm, "dashes") == "none",
        "no_exclaim": scalar(fm, "exclamation_marks") == "0",
        "no_emoji": scalar(fm, "emoji") == "false",
    }


# ----------------------------------------------------------------------------- prose extraction


def scan(text: str) -> tuple[str, list[Span]]:
    """Split a TSX file into (masked text, string literals).

    The masked text keeps offsets and newlines but blanks comments and string contents, so JSX text can be
    found with a regex across lines without matching inside strings or comments.
    """
    masked = list(text)
    strings: list[Span] = []
    i, n = 0, len(text)
    prev = "="  # file start behaves like an operator position

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if masked[k] != "\n":
                masked[k] = " "

    while i < n:
        ch = text[i]
        if ch == "/" and text.startswith("//", i) and (i == 0 or text[i - 1] in " \t\n;{}()"):
            end = text.find("\n", i)
            end = n if end == -1 else end
            blank(i, end)
            i = end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            blank(i, end)
            i = end
            continue
        if ch in "\"'`" and prev in STRING_OPENER:
            j = i + 1
            while j < n and text[j] != ch and not (ch != "`" and text[j] == "\n"):
                j += 2 if text[j] == "\\" else 1
            body = text[i + 1 : j]
            if ch == "`":
                body = re.sub(r"\$\{[^}]*\}", " ", body)
            strings.append(Span(body, i + 1))
            blank(i + 1, j)
            i = j + 1
            prev = ch
            continue
        if not ch.isspace():
            prev = ch
        i += 1
    return "".join(masked), strings


def is_prose(literal: str) -> bool:
    """Literals that read as sentences or labels, not class lists, paths, URLs, or identifiers."""
    s = literal.strip()
    if not s or s.startswith(("@", ".", "#", "http", "/")) or "/" in s.split()[0]:
        return False
    words = s.split()
    if all(CLASS_WORD.fullmatch(w) for w in words):
        # Lowercase runs: prose if several plain words (aria-label="unlock your workflow"), else classes.
        return len(words) >= 2 and all(re.fullmatch(r"[a-z']+[.,?!:;]?", w) for w in words)
    return bool(re.search(r"[A-Za-z]", s))


def prose_spans(text: str) -> list[Span]:
    masked, strings = scan(text)
    spans = [Span(m.group(1), m.start(1)) for m in JSX_TEXT.finditer(masked)]
    spans += [s for s in strings if is_prose(s.text)]
    return spans


def violations(text: str, rules: dict[str, object]) -> list[tuple[int, str]]:
    lines = text.splitlines()
    found: list[tuple[int, str]] = []

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    for span in prose_spans(text):
        first, last = line_of(span.start), line_of(span.start + len(span.text))
        if any(ALLOW in lines[k - 1] for k in range(first, min(last, len(lines)) + 1)):
            continue
        shown = " ".join(span.text.split())
        for word in rules["banned"]:  # type: ignore[union-attr]
            if re.search(rf"(?i)\b{re.escape(word)}\b", span.text):
                found.append((first, f'banned word "{word}" in "{shown}"'))
        for form in rules["never"]:  # type: ignore[union-attr]
            if re.search(rf"\b{re.escape(form)}\b", span.text):
                found.append((first, f'product name written as "{form}" in "{shown}"'))
        if rules["no_dashes"] and DASHES.search(span.text):
            found.append((first, f'em/en dash in "{shown}"'))
        if rules["no_exclaim"] and EXCLAIM.search(span.text):
            found.append((first, f'exclamation mark in "{shown}"'))
        if rules["no_emoji"] and EMOJI.search(span.text):
            found.append((first, f'emoji in "{shown}"'))
    return sorted(found)


# ----------------------------------------------------------------------------- commands


def ui_files(root: Path) -> list[Path]:
    files = {p.resolve() for g in UI_GLOBS for p in root.glob(g)}
    return sorted(p for p in files if not VENDORED.search(p.as_posix()))


def lint(root: Path, files: list[Path]) -> int:
    rules = load_rules(root)
    count = 0
    for f in files:
        for n, msg in violations(f.read_text(encoding="utf-8"), rules):
            shown = f.relative_to(root) if root in f.parents else f
            print(f"{shown}:{n}: {msg}")
            count += 1
    return count


def hook() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    raw = (event.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return 0
    path = Path(raw).resolve()
    if ROOT not in path.parents or path not in set(ui_files(ROOT)):
        return 0  # outside this repo, not a UI file, or vendored
    found = violations(path.read_text(encoding="utf-8"), load_rules(ROOT))
    if not found:
        return 0
    rel = path.relative_to(ROOT)
    lines = "\n".join(f"{rel}:{n}: {m}" for n, m in found)
    print(
        f"Copy breaks VOICE.md rules:\n{lines}\nRewrite it, or mark a deliberate exception with `{ALLOW} <reason>`.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "check":
        root = Path(argv[2]).resolve() if len(argv) > 2 else ROOT
        count = lint(root, ui_files(root))
        print(f"voice: {'ok' if not count else f'{count} violation(s); see VOICE.md'}")
        return 1 if count else 0
    if cmd == "lint":
        files = [Path(a).resolve() for a in argv[2:]] or ui_files(ROOT)
        return 1 if lint(ROOT, files) else 0
    if cmd == "hook":
        return hook()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
