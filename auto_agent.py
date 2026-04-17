#!/usr/bin/env python3
"""
auto_agent.py — Give it an idea, it builds and iteratively improves a project using Claude Code.

Usage:
    python auto_agent.py "I want to build a website to calculate energy needed to travel to planets"
    python auto_agent.py          # prompts for idea interactively
    python auto_agent.py --continue           # pick an existing project to resume
    python auto_agent.py --continue <path>    # resume a specific project directory
"""

import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / "auto-claude"

INITIAL_PROMPT = """\
You are an expert software developer. Build a complete, working project based on this idea:

"{idea}"

Requirements:
- Implement a fully functional, polished version of this idea
- Write comprehensive tests covering every function, edge case, and integration point
- Run all tests and make sure they pass before finishing
- Include a README.md with setup instructions and usage examples
- Structure the code cleanly — production-quality, not a prototype

Start coding immediately. Test everything in the slightest little detail.\
"""

ITERATION_PROMPT = """\
Review the current state of this project, then do the following in one pass:

1. Identify meaningful improvements and new features — consider UX, performance, \
missing functionality, security, and code quality
2. Write a brief plan at the top of your response listing what you will add/fix
3. Implement everything you planned
4. Add comprehensive tests for all new code
5. Run the full test suite and ensure everything passes

Be ambitious. Add real, visible value each iteration.\
"""

ANSI_CYAN = "\033[96m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED = "\033[91m"
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"


def log(color: str, label: str, message: str) -> None:
    print(f"{color}{ANSI_BOLD}[{label}]{ANSI_RESET} {message}", flush=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text[:50]


def run_claude(prompt: str, cwd: Path) -> int:
    """Run claude -p in cwd, streaming output to the terminal. Returns exit code."""
    cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]
    try:
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode
    except FileNotFoundError:
        log(ANSI_RED, "ERROR", "'claude' command not found. Install Claude Code CLI first.")
        sys.exit(1)


def pick_existing_project() -> Path:
    """List projects in BASE_DIR sorted by modification time, let user pick one."""
    if not BASE_DIR.exists():
        log(ANSI_RED, "ERROR", f"No projects found — {BASE_DIR} does not exist.")
        sys.exit(1)

    projects = sorted(
        [p for p in BASE_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not projects:
        log(ANSI_RED, "ERROR", f"No projects found in {BASE_DIR}.")
        sys.exit(1)

    print(f"\n{ANSI_BOLD}Existing projects:{ANSI_RESET}")
    for i, p in enumerate(projects):
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {ANSI_CYAN}{i + 1}{ANSI_RESET}  {p.name}  {ANSI_YELLOW}({mtime}){ANSI_RESET}")

    print()
    while True:
        raw = input(f"Pick a project [1-{len(projects)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(projects):
            return projects[int(raw) - 1]
        print("Invalid choice, try again.")


def main() -> None:
    args = sys.argv[1:]
    continuing = False
    project_dir: Path | None = None

    if args and args[0] == "--continue":
        continuing = True
        rest = args[1:]
        if rest:
            # Path provided directly
            project_dir = Path(" ".join(rest)).expanduser().resolve()
            if not project_dir.is_dir():
                log(ANSI_RED, "ERROR", f"Directory not found: {project_dir}")
                sys.exit(1)
        else:
            project_dir = pick_existing_project()

        log(ANSI_CYAN, "RESUME", f"Continuing project: {project_dir}")
        log(ANSI_CYAN, "INFO", "Press Ctrl+C at any time to stop the loop.\n")

    else:
        if args:
            idea = " ".join(args).strip()
        else:
            print(f"{ANSI_BOLD}Describe your project idea:{ANSI_RESET}")
            idea = input("> ").strip()

        if not idea:
            print("No idea provided. Exiting.")
            sys.exit(1)

        slug = slugify(idea)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        project_dir = BASE_DIR / f"{slug}-{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        log(ANSI_CYAN, "PROJECT", f"Directory: {project_dir}")
        log(ANSI_CYAN, "IDEA", idea)
        log(ANSI_CYAN, "INFO", "Press Ctrl+C at any time to stop the loop.\n")

    iteration = 0
    try:
        while True:
            iteration += 1

            if iteration == 1 and not continuing:
                log(ANSI_YELLOW, f"ITER {iteration}", "Building initial project...")
                prompt = INITIAL_PROMPT.format(idea=idea)
            else:
                label = f"ITER {iteration}" if not continuing else f"RESUME ITER {iteration}"
                log(ANSI_YELLOW, label, "Planning and implementing improvements...")
                prompt = ITERATION_PROMPT

            exit_code = run_claude(prompt, project_dir)

            if exit_code != 0:
                log(ANSI_RED, "STOPPED", f"Claude exited with code {exit_code} — likely out of tokens or an error.")
                break

            log(ANSI_GREEN, f"ITER {iteration}", "Complete.\n")

    except KeyboardInterrupt:
        print()
        log(ANSI_YELLOW, "STOPPED", f"Interrupted after {iteration} iteration(s).")

    log(ANSI_GREEN, "DONE", f"Project saved at: {project_dir}")


if __name__ == "__main__":
    main()
