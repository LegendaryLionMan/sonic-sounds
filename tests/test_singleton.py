"""tests/test_singleton.py — Day 1 Hour 24: PID-alive hardening for Windows SystemError trap."""
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from build.singleton import SingletonLock


class TestPidAlive(unittest.TestCase):
    """The hardened _pid_alive must survive every way Windows can lie about a PID."""

    def setUp(self):
        self.lock = SingletonLock(Path(os.environ.get("TEMP", "/tmp")) / "_test_lock.txt")

    def test_current_process_pid_is_alive(self):
        """Fast path: pid == os.getpid() always True."""
        self.assertTrue(self.lock._pid_alive(os.getpid()))

    def test_zero_pid_is_dead(self):
        self.assertFalse(self.lock._pid_alive(0))

    def test_negative_pid_is_dead(self):
        self.assertFalse(self.lock._pid_alive(-1))

    def test_clearly_dead_pid(self):
        """PID 999999 almost certainly doesn't exist."""
        # PID 0 and negatives return immediately; for other PIDs we ask the kernel.
        # Skip if the test runner happens to own this PID.
        if os.getpid() == 999999:
            self.skipTest("PID collision with test runner")
        self.assertFalse(self.lock._pid_alive(999999))

    def test_systemerror_does_not_raise(self):
        """The whole reason this hardening exists: SystemError must be caught."""
        with unittest.mock.patch("os.kill", side_effect=SystemError("result with exception set")):
            # Must NOT raise; should return False for any PID that isn't us.
            result = self.lock._pid_alive(999999)
            self.assertFalse(result)


class TestPidAliveCtypesFallback(unittest.TestCase):
    """Verify the ctypes path on Windows actually queries the kernel correctly."""

    def test_live_process_via_ctypes_path(self):
        """If our own pid is alive (it always is), and we walk the ctypes path, it must return True."""
        lock = SingletonLock(Path(os.environ.get("TEMP", "/tmp")) / "_test_lock.txt")
        # our own pid: fast-path returns True without ctypes; test an unrelated live pid
        # by spawning a quick subprocess.
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        try:
            self.assertTrue(lock._pid_alive(proc.pid))
        finally:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
