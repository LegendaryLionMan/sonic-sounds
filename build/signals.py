"""build/signals.py — signal handlers for graceful shutdown (per Day 3).

Per plan §7 Day 3: "signal handlers" + "startup sequence".

Cross-platform signal handling:
- On Unix: SIGTERM, SIGINT, SIGHUP are the standard shutdown signals
- On Windows: SIGINT is Ctrl+C, SIGBREAK is Ctrl+Break. SIGTERM is supported
  for service shutdown but the default Ctrl+Break signal is mapped to SIGBREAK.

We register handlers that:
1. Set a global "shutdown_requested" flag (the main loop checks this)
2. Log the signal received

The main daemon loop polls shutdown_requested every iteration.
"""
import logging
import signal
import sys
import threading

# Cross-platform signal handling
# SIGTERM (15) is supported on both Unix and Windows for service shutdown
# SIGINT (2) is Ctrl+C on both
# SIGHUP (1) is Unix-only (terminal hangup); on Windows we skip it
DEFAULT_SHUTDOWN_SIGNALS = [signal.SIGTERM, signal.SIGINT]
if sys.platform != "win32":
    DEFAULT_SHUTDOWN_SIGNALS.append(getattr(signal, "SIGHUP", None))
    DEFAULT_SHUTDOWN_SIGNALS = [s for s in DEFAULT_SHUTDOWN_SIGNALS if s is not None]

# Module-level state (shared across the daemon)
_shutdown_event = threading.Event()
_log = logging.getLogger("sonic_studio.daemon")


def is_shutdown_requested() -> bool:
    """Return True if a shutdown signal has been received."""
    return _shutdown_event.is_set()


def request_shutdown() -> None:
    """Programmatically request shutdown (used by internal handlers)."""
    _shutdown_event.set()


def reset_shutdown() -> None:
    """Reset the shutdown flag (used in tests)."""
    _shutdown_event.clear()


def install_signal_handlers(signals=None) -> None:
    """Install signal handlers that set the shutdown event.

    Args:
        signals: list of signal numbers to handle. Defaults to SIGTERM + SIGINT
                 (and SIGHUP on non-Windows).
    """
    if signals is None:
        signals = DEFAULT_SHUTDOWN_SIGNALS

    def _handler(signum, frame):
        try:
            signame = signal.Signals(signum).name
        except (ValueError, AttributeError):
            signame = f"signal {signum}"
        _log.warning(f"received {signame} — initiating graceful shutdown")
        _shutdown_event.set()

    for s in signals:
        try:
            signal.signal(s, _handler)
            _log.info(f"installed handler for signal {s}")
        except (ValueError, OSError) as e:
            _log.debug(f"could not install handler for signal {s}: {e}")


def wait_for_shutdown(timeout: float = None) -> bool:
    """Block until shutdown is requested or timeout (None = forever).

    Returns True if shutdown was requested, False if timeout elapsed.
    """
    return _shutdown_event.wait(timeout=timeout)
