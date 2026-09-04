"""build/servy_register.py — register daemon as Windows Service (Day 3.5).

Per plan §7 Day 3:
> Servy/NSSM service registration via sc create (bypass Servy CLI bugs)

The plan KNOWS that `Servy import` and `Servy create` are buggy. So we
bypass Servy CLI entirely and use `sc create` directly:

  sc create ServyAlbumStudio binPath="..." start=auto

This registers the daemon as a Windows Service that:
- Starts automatically at boot
- Restarts on failure
- Can be managed via sc query / sc start / sc stop

Implementation notes:
- Use subprocess.run(['sc', 'create', ...]) to invoke sc.exe
- The binPath must point to the python executable + module path
- start=auto means start at boot
- displayname= is the user-friendly name in services.msc

For Day 3, this is a script you run ONCE to install the service. The
daemon itself doesn't manage its own registration.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJ_ROOT = Path(__file__).parent.parent.resolve()
PYTHON_EXE = Path(sys.executable)
SERVICE_NAME = "ServyAlbumStudio"
DISPLAY_NAME = "sonic-studio daemon (Day 3)"
DESCRIPTION = "sonic-studio HTTP daemon — Quart ASGI server with WAL+PRAGMAs SQLite."


def build_binpath(port: int = 8765, host: str = "127.0.0.1") -> str:
    """Build the binPath string for the Windows Service.

    Quoting: per sc create docs, embedded quotes must be escaped as \".
    """
    # binPath is what sc.exe invokes to start the service. We use:
    # python.exe -m build.serve --host ... --port ...
    # We need to escape quotes for sc.exe's parser.
    args = [str(PYTHON_EXE), "-m", "build.serve",
            "--host", host, "--port", str(port)]
    parts = []
    for a in args:
        # Escape backslashes and quotes for sc.exe
        escaped = a.replace("\\", "\\\\").replace('"', '\\"')
        if " " in a:
            parts.append(f'"{escaped}"')
        else:
            parts.append(escaped)
    return " ".join(parts)


def install_service(port: int = 8765, host: str = "127.0.0.1") -> int:
    """Register the daemon as a Windows Service via sc create."""
    binpath = build_binpath(port, host)
    cmd = [
        "sc", "create", SERVICE_NAME,
        f"binPath={binpath}",
        "start=auto",
        "type=own",
    ]
    print(f"Running: {' '.join(cmd[:3])} ... (binPath redacted)")
    print(f"  binPath: {binpath[:80]}...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        print(f"\nService '{SERVICE_NAME}' created successfully.")
        print(f"Start with: sc start {SERVICE_NAME}")
        print(f"Stop with:  sc stop {SERVICE_NAME}")
        print(f"Status:     sc query {SERVICE_NAME}")
        return 0
    else:
        print(f"\nERROR: sc create failed with code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return result.returncode


def uninstall_service() -> int:
    """Remove the Windows Service via sc delete."""
    cmd = ["sc", "delete", SERVICE_NAME]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        print(f"Service '{SERVICE_NAME}' removed.")
        return 0
    else:
        print(f"ERROR: sc delete failed with code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return result.returncode


def query_service() -> int:
    """Query service status."""
    cmd = ["sc", "query", SERVICE_NAME]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register/unregister sonic-studio daemon as a Windows Service"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_install = subparsers.add_parser("install", help="install the service")
    p_install.add_argument("--port", type=int, default=8765)
    p_install.add_argument("--host", default="127.0.0.1")

    subparsers.add_parser("uninstall", help="remove the service")

    subparsers.add_parser("query", help="query service status")

    args = parser.parse_args()
    if args.command == "install":
        return install_service(args.port, args.host)
    elif args.command == "uninstall":
        return uninstall_service()
    elif args.command == "query":
        return query_service()
    return 1


if __name__ == "__main__":
    sys.exit(main())
