#!/usr/bin/env python3
"""
auto_agent.py — Give it an idea, it builds and iteratively improves a project using Gemini or Claude.

Usage:
    python auto_agent.py "I want to build a website to calculate energy needed to travel to planets"
    python auto_agent.py          # prompts for idea interactively
    python auto_agent.py --continue           # pick an existing project to resume
    python auto_agent.py --continue <path>    # resume a specific project directory
    python auto_agent.py --agent claude       # use Claude instead of Gemini
"""

import re
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / "auto-claude"

INITIAL_PROMPT = """\
You are an expert software developer. Build a complete, working project based on this idea:

"{idea}"

Requirements:
- Implement a fully functional, polished version of this idea
- Write exhaustive tests covering every function, edge case, and integration point. TESTING IS SUPER IMPORTANT.
- Run all tests and make sure they pass before finishing
- Include a README.md with setup instructions and usage examples
- Create a MEMORY.md file documenting the project's architecture, current state, and potential future improvements
- Structure the code cleanly — production-quality, not a prototype
- Commit your changes with a descriptive message once everything is working and tested

Start coding immediately. Test everything in the slightest little detail.\
"""

ITERATION_PROMPT = """\
Review the current state of this project, then do the following in one pass:

1. Identify meaningful improvements and new features — think outside the box, \
considering UX, performance, missing functionality, security, and code quality
2. Write a brief plan at the top of your response listing what you will add/fix
3. Implement everything you planned
4. Add exhaustive tests for all new code and edge cases (TESTING IS SUPER IMPORTANT)
5. Run the full test suite and ensure absolutely everything passes
6. Update the README.md to reflect the new features and current state of the project
7. Update MEMORY.md to document recent changes, current architecture, and future ideas
8. Commit your changes with a descriptive message

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


def generate_slug_with_llm(idea: str, agent: str) -> str | None:
    """Ask the LLM to generate a short kebab-case slug for the idea."""
    prompt = f"Generate a short, descriptive kebab-case folder name for a project based on this idea: '{idea}'. Return ONLY the folder name, nothing else."

    if agent == "gemini":
        cmd = ["gemini", "-p", prompt, "-y", "--output-format", "text"]
    else:
        cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]

    try:
        # We use a short timeout and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            slug = result.stdout.strip().split("\n")[-1].strip()  # Take last line in case of noise
            slug = re.sub(r"[^\w\s-]", "", slug)
            slug = re.sub(r"[\s_-]+", "-", slug).lower()
            return slug if slug else None
    except Exception:
        pass
    return None


def run_claude(prompt: str, cwd: Path) -> int:
    """Run claude -p in cwd, streaming output to the terminal. Returns exit code."""
    cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]
    try:
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode
    except FileNotFoundError:
        log(ANSI_RED, "ERROR", "'claude' command not found. Install Claude Code CLI first.")
        sys.exit(1)


def run_gemini(prompt: str, cwd: Path) -> int:
    """Run gemini -p in cwd, streaming output to the terminal. Returns exit code."""
    cmd = ["gemini", "-p", prompt, "-y"]
    try:
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode
    except FileNotFoundError:
        log(ANSI_RED, "ERROR", "'gemini' command not found. Install Gemini CLI first.")
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
    parser = argparse.ArgumentParser(description="Auto-Agent: Build and improve projects with AI.")
    parser.add_argument("idea", nargs="*", help="The project idea to build.")
    parser.add_argument("--continue", dest="continue_project", action="store_true", help="Resume an existing project.")
    parser.add_argument("--path", type=str, help="Specific path to a project to resume (used with --continue).")
    parser.add_argument("--agent", choices=["gemini", "claude"], default="gemini", help="The AI agent to use (default: gemini).")

    args = parser.parse_args()

    project_dir: Path | None = None
    idea = " ".join(args.idea).strip()

    if args.continue_project:
        if args.path:
            project_dir = Path(args.path).expanduser().resolve()
            if not project_dir.is_dir():
                log(ANSI_RED, "ERROR", f"Directory not found: {project_dir}")
                sys.exit(1)
        elif idea and Path(idea).is_dir():
            # Handle case where user might have done: python auto_agent.py --continue /path/to/project
            project_dir = Path(idea).expanduser().resolve()
            idea = ""
        else:
            project_dir = pick_existing_project()

        log(ANSI_CYAN, "RESUME", f"Continuing project: {project_dir}")
        log(ANSI_CYAN, "INFO", "Press Ctrl+C at any time to stop the loop.\n")
        continuing = True
    else:
        if not idea:
            print(f"{ANSI_BOLD}Describe your project idea:{ANSI_RESET}")
            idea = input("> ").strip()

        if not idea:
            print("No idea provided. Exiting.")
            sys.exit(1)

        log(ANSI_CYAN, "IDEA", idea)
        log(ANSI_YELLOW, "INFO", "Generating descriptive project name...")
        slug = generate_slug_with_llm(idea, args.agent)
        if not slug:
            slug = slugify(idea)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        project_dir = BASE_DIR / f"{slug}-{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git so agents can commit
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)

        log(ANSI_CYAN, "PROJECT", f"Directory: {project_dir}")
        log(ANSI_CYAN, "INFO", "Press Ctrl+C at any time to stop the loop.\n")
        continuing = False

    iteration = 0
    try:
        while True:
            iteration += 1

            if iteration == 1 and not continuing:
                log(ANSI_YELLOW, f"ITER {iteration}", f"Building initial project using {args.agent}...")
                prompt = INITIAL_PROMPT.format(idea=idea)
            else:
                label = f"ITER {iteration}" if not continuing else f"RESUME ITER {iteration}"
                log(ANSI_YELLOW, label, f"Planning and implementing improvements using {args.agent}...")
                prompt = ITERATION_PROMPT

            if args.agent == "gemini":
                exit_code = run_gemini(prompt, project_dir)
            else:
                exit_code = run_claude(prompt, project_dir)

            if exit_code != 0:
                log(ANSI_RED, "STOPPED", f"{args.agent.capitalize()} exited with code {exit_code} — likely out of tokens or an error.")
                break

            log(ANSI_GREEN, f"ITER {iteration}", "Complete.\n")

    except KeyboardInterrupt:
        print()
        log(ANSI_YELLOW, "STOPPED", f"Interrupted after {iteration} iteration(s).")

    log(ANSI_GREEN, "DONE", f"Project saved at: {project_dir}")


if __name__ == "__main__":
    main()
