"""build/ — daemon infrastructure (per PLAN-2026-07-28-v3.4 §Day 3).

Day 3 implements:
- serve.py — Quart ASGI app with singleton lock + startup sequence
- http_router.py — dispatch table for Day 3 endpoints (5 implementable)
- signals.py — signal handlers (SIGTERM/SIGINT graceful shutdown)

Day 6+ adds build/lock.py, build/invoke.py, build/runner.py (under same
build/ package).
"""
