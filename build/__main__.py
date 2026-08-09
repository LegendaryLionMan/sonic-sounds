"""build/__main__.py — python -m build entrypoint."""
import sys
from build.serve import main

if __name__ == "__main__":
    sys.exit(main())
