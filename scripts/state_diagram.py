"""scripts/state-diagram - generate a Mermaid state diagram for the
session lifecycle. Per 2026-09-06 user feedback (visual
inspection): the dashboard shows "Album Pipeline · No active album
state yet" but doesn't make clear what states an album can be in.

Outputs Mermaid syntax that can be pasted into any Mermaid renderer.

Usage:
    python scripts/state-diagram.py
    python scripts/state-diagram.py --output docs/session-states.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DIAGRAM = """## Album Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft : create album
    draft --> active : open session
    active --> active : chat / build event
    active --> paused : manual pause
    active --> paused : 12h idle auto-pause
    paused --> active : resume
    active --> done : complete
    paused --> done : complete
    done --> active : reopen (reverse)
    done --> archived : archive
    archived --> [*]

    note right of active
        MAX_ACTIVE_SESSIONS = 3
        Last activity tracked for idle auto-pause
    end note
```

## Build Pipeline Layer State

```mermaid
stateDiagram-v2
    [*] --> todo : queue_job
    todo --> needs_approval : approval-required layer
    needs_approval --> todo : approved
    todo --> running : mark_running
    running --> done : success
    running --> failed : subprocess crash
    running --> blocked : user error
    failed --> todo : retry (retry=True)
    failed --> crashed : process gone (orphan recovery)
    blocked --> todo : user fixes
    done --> [*]
```

## Intake Form State

```mermaid
stateDiagram-v2
    [*] --> empty : page load
    empty --> partial : typing fields
    partial --> autosaved : 800ms debounce
    autosaved --> partial : more typing
    partial --> gate_locked : M-tier incomplete
    gate_locked --> gate_open : 9/9 M-tier filled
    gate_open --> exported : click "Generate Concept-Brief"
    exported --> [*]
```
"""


def main() -> int:
    p = argparse.ArgumentParser(description="state diagram generator")
    p.add_argument("--output", type=str, help="write to file")
    args = p.parse_args()
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(DIAGRAM, encoding="utf-8")
        print(f"[state-diagram] saved to {args.output}")
    else:
        print(DIAGRAM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
