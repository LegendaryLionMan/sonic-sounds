"""__main__.py — album-studio daemon entrypoint (Day 3.4).

Run with: `python -m serve` or `python -m build.serve`

This is the canonical way to start the daemon. Sets up logging, acquires
the singleton lock, runs migrations, installs signal handlers, and starts
the Quart app.

Per plan §7 Day 3 verification:
  curl http://127.0.0.1:8765/api/health → JSON
  curl /site/index.html → HTML
  sc query ServyAlbumStudio → RUNNING (registered via sc create)
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import build/ and db/
PROJ_ROOT = Path(__file__).resolve().parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from build.serve import main

if __name__ == "__main__":
    sys.exit(main())
