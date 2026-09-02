"""e2e/run_all.py — bootstrap the daemon + run both E2E suites.

Run:
  python e2e/run_all.py

This is the entry-point a human (or CI) uses. It:
  1. Seeds a fresh tempdb with maren-sol + half-light-hours
  2. Starts the daemon on port 8793 (or ALBUM_STUDIO_E2E_PORT env var)
  3. Runs test_ui_full_ux.py (API contract — no browser needed)
  4. Reports results

For the browser-driven suite, run e2e/test_browser_drive.py directly
inside a `browser_exec` call (it depends on the harness helpers).
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = int(os.environ.get("ALBUM_STUDIO_E2E_PORT", "8793"))


def main() -> int:
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="album-studio-e2e-")
    db = os.path.join(tmpdir, "test.db")
    lock = os.path.join(tmpdir, "test.lock")
    log = os.path.join(tmpdir, "test.log")
    print(f"tmpdir: {tmpdir}")
    print(f"port: {PORT}")

    env = os.environ.copy()
    env["ALBUM_STUDIO_DB_PATH"] = db
    env["ALBUM_STUDIO_LOCK_PATH"] = lock
    env["ALBUM_STUDIO_LOG_PATH"] = log
    env["PYTHONPATH"] = ""  # avoid hermes-venv contamination

    # Seed
    print("\n[setup] seeding db...")
    r = subprocess.run([sys.executable, "-m", "db.seed", "--db", db, "--force"],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    if r.returncode != 0:
        print(f"seed FAILED: {r.stderr}")
        return 1
    print("  ok")

    # Start daemon
    print("\n[setup] starting daemon on :%d..." % PORT)
    daemon = subprocess.Popen(
        [sys.executable, "-m", "build.serve",
         "--host", "127.0.0.1", "--port", str(PORT),
         "--lock", lock, "--log", log],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, cwd=ROOT,
    )
    print(f"  pid: {daemon.pid}")
    time.sleep(3)
    if daemon.poll() is not None:
        out, err = daemon.communicate()
        print(f"  daemon FAILED: {err.decode()[:500]}")
        return 1

    # Run the API/UX contract suite
    print(f"\n[test] running e2e/test_ui_full_ux.py against :{PORT}...")
    env["ALBUM_STUDIO_E2E_BASE"] = f"http://127.0.0.1:{PORT}"
    r = subprocess.run([sys.executable, os.path.join(HERE, "test_ui_full_ux.py")],
                       capture_output=True, text=True, env=env, cwd=ROOT,
                       timeout=120)
    print(r.stdout)
    if r.returncode != 0:
        print(f"FAILURES (stderr): {r.stderr[:1000]}")
        api_pass = False
    else:
        api_pass = True

    # Tear down daemon
    print("\n[teardown] stopping daemon...")
    daemon.terminate()
    try:
        daemon.wait(timeout=5)
    except subprocess.TimeoutExpired:
        daemon.kill()
    print("  done")

    return 0 if api_pass else 1


if __name__ == "__main__":
    sys.exit(main())
