#!/usr/bin/env python3
"""
Validate a pull request description against the project's required structure.

Run by the "PR Description Check" GitHub Actions workflow on every pull request.
Reads the PR body from the event payload at ``GITHUB_EVENT_PATH`` and enforces:

  1. All six required ``##`` sections are present (any order):
       Summary, Motivation, Changes, Validation, Risk, Rollout and Recovery
  2. Each section has real content — placeholders such as ``TBD``, ``TODO``,
     ``N/A``, ``None`` or bare dashes are rejected.
  3. The Validation section contains at least one checked command checkbox in
     the form ``- [x] `the command you ran```.

On failure it prints a clear, itemized list of every problem and exits 1.
Uses only the Python standard library so the workflow needs no dependencies.
"""

import json
import os
import re
import sys

# Required sections, keyed by their normalized heading name. The value is the
# canonical label shown to the user in error messages.
REQUIRED_SECTIONS = {
    "summary": "Summary",
    "motivation": "Motivation",
    "changes": "Changes",
    "validation": "Validation",
    "risk": "Risk",
    "rollout and recovery": "Rollout and Recovery",
}

# Content that does not count as a real answer when it is the whole section.
PLACEHOLDERS = {
    "tbd", "todo", "tba", "n/a", "na", "none", "nil", "null",
    "wip", "fixme", "xxx", "...", "?",
}

# A line that is only dashes (e.g. an empty bullet "-" or a rule "---").
DASHES_ONLY = re.compile(r"^[-–—\s]+$")

# HTML comments, e.g. the instruction hints in the PR template.
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# A markdown ``##`` heading (exactly H2) and its trailing text.
H2_HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)

# Any markdown heading (H1-H6) — used to find where a section ends.
ANY_HEADING = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)

# Leading list / checkbox markers stripped before judging whether a line is a
# bare placeholder: "- ", "* ", "+ ", "- [ ] ", "- [x] ", "1. " etc.
LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*(?:\[[ xX]\]\s*)?")

# A checked checkbox whose label is a backtick-quoted command, e.g.
# ``- [x] `pytest -q```.
CHECKED_COMMAND = re.compile(r"^\s*[-*+]\s*\[[xX]\]\s+`[^`\n]+`", re.MULTILINE)


def read_pr_body() -> str:
    """Return the PR body from the GitHub event payload (``""`` if absent)."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        fail_hard("GITHUB_EVENT_PATH is not set — is this running in GitHub Actions?")
    try:
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        fail_hard(f"Could not read event payload at {event_path}: {exc}")

    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        fail_hard("Event payload has no 'pull_request' — workflow misconfigured?")
    return pull_request.get("body") or ""


def normalize_heading(text: str) -> str:
    """Lowercase, trim, drop trailing punctuation and treat '&' as 'and'."""
    text = text.strip().lower().rstrip(":.")
    text = text.replace("&", "and")
    return re.sub(r"\s+", " ", text).strip()


def split_sections(body: str) -> dict:
    """Map normalized ``##`` heading -> raw section body text."""
    sections = {}
    matches = list(H2_HEADING.finditer(body))
    for index, match in enumerate(matches):
        start = match.end()
        # Section runs until the next heading of any level, or end of body.
        rest = body[start:]
        next_heading = ANY_HEADING.search(rest)
        content = rest[: next_heading.start()] if next_heading else rest
        sections[normalize_heading(match.group(1))] = content
    return sections


def meaningful_lines(content: str) -> list:
    """Lines with real text after stripping comments, markers and dashes."""
    content = HTML_COMMENT.sub("", content)
    lines = []
    for raw in content.splitlines():
        stripped = LIST_MARKER.sub("", raw).strip()
        if not stripped or DASHES_ONLY.match(stripped):
            continue
        lines.append(stripped)
    return lines


def is_placeholder_only(content: str) -> bool:
    """True if the section is empty or only placeholder tokens."""
    lines = meaningful_lines(content)
    if not lines:
        return True
    for line in lines:
        token = line.strip().strip("`*_").rstrip(".!").lower()
        if token not in PLACEHOLDERS:
            return False
    return True


def validate(body: str) -> list:
    """Return a list of human-readable problems (empty == valid)."""
    problems = []
    sections = split_sections(body)

    for key, label in REQUIRED_SECTIONS.items():
        if key not in sections:
            problems.append(f"Missing required section: ## {label}")
        elif is_placeholder_only(sections[key]):
            problems.append(
                f"Section ## {label} is empty or only a placeholder "
                "(e.g. TBD/TODO/N/A/None/dashes) — add real content."
            )

    # Validation section must show at least one command that was run.
    validation = sections.get("validation")
    if validation is not None and not CHECKED_COMMAND.search(validation):
        problems.append(
            "Section ## Validation must include at least one checked command "
            "checkbox, e.g. - [x] `pytest -q`"
        )

    return problems


def write_step_summary(problems: list) -> None:
    """Render the problem list to the GitHub Actions job summary, if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = ["## ❌ PR description check failed", ""]
    lines += [f"{i}. {p}" for i, p in enumerate(problems, 1)]
    lines += [
        "",
        "Edit the PR description to fix these, then the check re-runs automatically.",
    ]
    try:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        pass  # Summary is a nicety; never fail the run over it.


def fail_hard(message: str) -> None:
    """Print an error annotation and exit non-zero (config/runtime errors)."""
    print(f"::error::{message}")
    sys.exit(1)


def main() -> int:
    # Emit UTF-8 regardless of the host console encoding (e.g. Windows cp1252),
    # so the status glyphs below never crash the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    body = read_pr_body()
    problems = validate(body)

    if not problems:
        print("✅ PR description check passed: all required sections present "
              "with real content.")
        return 0

    print("❌ PR description check failed. Fix the following:\n")
    for index, problem in enumerate(problems, 1):
        print(f"  {index}. {problem}")
        print(f"::error::{problem}")
    print(
        "\nRequired sections (each needs real content): "
        + ", ".join(REQUIRED_SECTIONS.values())
        + ".\nThe Validation section also needs at least one checked command "
        "checkbox, e.g. - [x] `pytest -q`."
    )
    write_step_summary(problems)
    return 1


if __name__ == "__main__":
    sys.exit(main())
