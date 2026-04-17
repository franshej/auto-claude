# auto-agent

Give it an idea — it builds a complete project with Claude Code, then loops forever improving it.

## How it works

1. You describe a project idea
2. A folder is created in `~/auto-claude/<idea-slug>-<timestamp>/`
3. Claude Code builds the full project with tests
4. On every subsequent iteration, Claude reviews what exists, plans new features and improvements, implements them, and re-runs all tests
5. Loops until you stop it (`Ctrl+C`) or tokens run out

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

## Usage

**New project — pass idea as argument:**
```bash
python3 auto_agent.py "I want to build a Rust online game like World of Warcraft in 2D"
```

**New project — interactive prompt:**
```bash
python3 auto_agent.py
# Describe your project idea:
# > I want to build a website where I can calculate the energy it takes to go to a planet
```

**Continue an existing project — interactive picker:**
```bash
python3 auto_agent.py --continue
```
Lists all projects in `~/auto-claude/` sorted by most recently modified. Pick a number to resume.

**Continue a specific project by path:**
```bash
python3 auto_agent.py --continue ~/auto-claude/my-project-20260417-120000
```

## Output

All projects are saved under `~/auto-claude/`. Each run creates its own timestamped directory so nothing is ever overwritten.
