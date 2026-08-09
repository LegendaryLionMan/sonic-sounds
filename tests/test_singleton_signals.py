"""tests/test_singleton_signals.py — unit tests for build/singleton + build/signals."""
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from build.singleton import SingletonLock, SingletonLockError, is_pid_alive
from build.signals import (
    is_shutdown_requested, request_shutdown, reset_shutdown,
    install_signal_handlers, DEFAULT_SHUTDOWN_SIGNALS,
)


class TestSingleton(unittest.TestCase):
    def setUp(self):
        # Create a unique lock file path for each test
        fd, self.lock_path = tempfile.mkstemp(suffix=".lock")
        os.close(fd)
        Path(self.lock_path).unlink()  # remove the empty file, we create our own
        self.lock_path = self.lock_path + ".lock"
        self.lock = SingletonLock(self.lock_path)

    def tearDown(self):
        if Path(self.lock_path).exists():
            Path(self.lock_path).unlink()
        self.lock.release()

    def test_initial_state(self):
        """A fresh lock is not held."""
        self.assertFalse(self.lock.is_held())

    def test_acquire_writes_pid(self):
        """After acquire, the lock file contains our PID."""
        self.lock.acquire()
        self.assertTrue(Path(self.lock_path).exists())
        pid_in_file = int(Path(self.lock_path).read_text().strip())
        self.assertEqual(pid_in_file, os.getpid())

    def test_same_process_reacquire_is_noop(self):
        """Same-process re-acquire is a no-op (we own it)."""
        self.lock.acquire()
        # Second acquire on a fresh SingletonLock instance should not raise
        lock2 = SingletonLock(self.lock_path)
        lock2.acquire()  # should be silent no-op
        self.assertEqual(lock2.pid, os.getpid())

    def test_stale_lock_is_taken_over(self):
        """A lock with a dead PID is taken over."""
        # Write a stale PID
        Path(self.lock_path).write_text("999999\n", encoding="utf-8")
        # is_pid_alive(999999) should return False (no such process)
        self.assertFalse(is_pid_alive(999999))
        # Acquire should take over the stale lock
        self.lock.acquire()
        pid_in_file = int(Path(self.lock_path).read_text().strip())
        self.assertEqual(pid_in_file, os.getpid())

    def test_release_removes_lock_file(self):
        """After release, the lock file is gone."""
        self.lock.acquire()
        self.assertTrue(Path(self.lock_path).exists())
        self.lock.release()
        self.assertFalse(Path(self.lock_path).exists())

    def test_is_pid_alive_self(self):
        """Our own PID is always alive."""
        self.assertTrue(is_pid_alive(os.getpid()))

    def test_is_pid_alive_dead_pid(self):
        """An unused high PID is dead."""
        # PID 1 is usually init; PID 999999 almost certainly doesn't exist
        # (but is_pid_alive checks if we can signal it; on Linux 1 may be special)
        self.assertFalse(is_pid_alive(999999))


class TestSignals(unittest.TestCase):
    def setUp(self):
        reset_shutdown()
        # Save original signal handlers
        self._orig_sigterm = signal.getsignal(signal.SIGTERM)
        self._orig_sigint = signal.getsignal(signal.SIGINT)

    def tearDown(self):
        # Restore original signal handlers
        signal.signal(signal.SIGTERM, self._orig_sigterm)
        signal.signal(signal.SIGINT, self._orig_sigint)
        reset_shutdown()

    def test_initial_state_not_shutdown(self):
        self.assertFalse(is_shutdown_requested())

    def test_request_shutdown(self):
        request_shutdown()
        self.assertTrue(is_shutdown_requested())

    def test_reset_shutdown(self):
        request_shutdown()
        self.assertTrue(is_shutdown_requested())
        reset_shutdown()
        self.assertFalse(is_shutdown_requested())

    def test_install_signal_handlers(self):
        install_signal_handlers()
        # After install, handlers should be set (not SIG_DFL/SIG_IGN)
        sigterm_handler = signal.getsignal(signal.SIGTERM)
        sigint_handler = signal.getsignal(signal.SIGINT)
        self.assertNotEqual(sigterm_handler, signal.SIG_DFL)
        self.assertNotEqual(sigterm_handler, signal.SIG_IGN)
        self.assertNotEqual(sigint_handler, signal.SIG_DFL)
        self.assertNotEqual(sigint_handler, signal.SIG_IGN)

    def test_default_signals_include_sigterm_sigint(self):
        self.assertIn(signal.SIGTERM, DEFAULT_SHUTDOWN_SIGNALS)
        self.assertIn(signal.SIGINT, DEFAULT_SHUTDOWN_SIGNALS)


if __name__ == "__main__":
    unittest.main()
