# sonic-sounds · developer tooling

This directory contains the developer-facing scripts and configs
that augment the standard repo structure. Use them as building blocks
for your own workflow — they compose, they don't fight each other.

## Quick reference

| Need | Command |
|---|---|
| Start the daemon on :8765 | `python scripts/dev.py` |
| Start on a different port | `python scripts/dev.py --port 9000` |
| Stop daemon on :8765 | `python scripts/dev.py --stop` |
| Restart daemon | `python scripts/dev.py --restart` |
| Check daemon status | `python scripts/dev.py --status` |
| Run advanced E2E suite | `python scripts/e2e.py` |
| Spawn daemon + run E2E | `python scripts/e2e.py --spawn --stop-after` |
| Tail daemon log | `python scripts/log_tail.py` |
| Tail last 100 lines | `python scripts/log_tail.py --last 100` |
| Log level histogram | `python scripts/log_tail.py --stats` |
| Interactive SQL shell | `python scripts/db_shell.py` |
| One-shot SQL | `python scripts/db_shell.py "SELECT * FROM albums"` |
| List all DB tables | `python scripts/db_shell.py --tables` |
| Dump DB schema | `python scripts/db_shell.py --dump` |
| Audit CSS for hardcoded colors | `python scripts/css_audit.py` |
| Find CSS hardcoded colors | `python scripts/css_audit.py --strict` |
| Profile request timing | `python scripts/profile.py` |
| Screenshot regression diff | `python scripts/screenshot_diff.py` |
| Update baseline screenshots | `python scripts/screenshot_diff.py --update` |

## Component index

### `dev.py` — single-command daemon launcher
Consolidates the "find the daemon, kill it, restart it" workflow.
Auto-port (scans for next free port if 8765 is busy), writes logs to
`C:/Users/lion_/AppData/Local/Temp/sonic-sounds-smoke/daemon-stdout.log`.

### `e2e.py` — one-shot E2E orchestrator
Wraps `e2e/test_advanced.py` with daemon lifecycle management. By
default runs against the live daemon. With `--spawn` it spawns a
fresh daemon (so the test runs in isolation from the live one).

### `log_tail.py` — structured log viewer
Tail -f equivalent with ANSI color coding. Supports `--last N`,
`--grep PATTERN`, and `--stats` (level histogram + recent errors).

### `db_shell.py` — interactive SQLite shell
Resolves the canonical DB path automatically. Tabular output, REPL or
one-shot mode, schema dump.

### `css_audit.py` — hardcoded-color linter
Scans every CSS file in `site/` for color literals (`#hex`, `rgb()`,
`hsl()`) outside `:root` and `:root[data-theme=...]` blocks. Used in
pre-commit hook + CI to catch ad-hoc color values that should use
theme tokens.

### `profile.py` + `profile_patch.py` — request profiler
Set `SONIC_SOUNDS_PROFILE=1` in the daemon env, run traffic, then
`python scripts/profile.py` for a top-20 by time + p95 + slowest-single
report.

### `screenshot_diff.py` — visual regression detector
Compares the e2e screenshot sweep to a baseline directory. Catches
unintended visual regressions (e.g. someone changes a CSS rule and
breaks the cassette aspect ratio).

### `daemon_spawn.py` — shared daemon lifecycle helper
Foundation for `dev.py` and `e2e.py`. Provides `spawn`, `kill_port`,
`wait_healthy`, `is_port_free`.

### CI workflow — `.github/workflows/tests.yml`
Three jobs:
1. **unit** — pytest on Python 3.11/3.12/3.13
2. **e2e-advanced** — boots daemon + runs the advanced suite
3. **css-audit** — runs `css_audit.py` and uploads the report

### Pre-commit — `.pre-commit-config.yaml`
Local-only hooks (no network). Catches syntax errors, hardcoded CSS
colors, accidental debugger imports, and oversized files before
they reach CI.
