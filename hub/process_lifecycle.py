"""Process lifecycle helpers: PID lock and hard-timeout exit cleanup.

Keeps app.py thin. Pure helpers are unit-tested in tests/test_webapp_lifecycle.py.
"""
from __future__ import annotations

import atexit
import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional, Union

# Default lock path (aligned with start_webapp.bat / stop_webapp.bat).
DEFAULT_LOCK_PATH = Path("runtime") / "main.lock"
DEFAULT_CLEANUP_TIMEOUT_SEC = 2.0

_cleanup_lock = threading.Lock()
_cleanup_done = False


def pid_is_alive(pid: int) -> bool:
    """Return True if *pid* refers to a still-running process."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) == 0:
                return False
            return int(code.value) == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but we cannot signal it — treat as alive.
        return True
    except OSError:
        return False
    return True


def _read_lock_pid(path: Path) -> Optional[int]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        # Accept either plain PID or "pid=<n>" lines.
        if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
            return int(raw)
        for line in raw.splitlines():
            line = line.strip()
            if line.isdigit():
                return int(line)
            if line.lower().startswith("pid="):
                return int(line.split("=", 1)[1].strip())
        return None
    except Exception:
        return None


def acquire_pid_lock(path: Union[str, Path] = DEFAULT_LOCK_PATH) -> bool:
    """Acquire a single-instance PID lock.

    Returns True if this process now owns the lock.
    Returns False if another live process already holds it.
    Stale locks (dead PID) are removed and replaced.
    """
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        old_pid = _read_lock_pid(lock_path)
        if old_pid is not None and old_pid != os.getpid() and pid_is_alive(old_pid):
            return False
        # Stale or unreadable — remove and continue.
        try:
            lock_path.unlink(missing_ok=True)
        except TypeError:
            # Python < 3.8 missing_ok not available (we are 3.10+; keep safe).
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except OSError:
                pass
        except OSError:
            pass

    try:
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        return False

    # Best-effort: release on clean interpreter exit.
    atexit.register(release_pid_lock, lock_path)
    return True


def release_pid_lock(path: Union[str, Path] = DEFAULT_LOCK_PATH) -> None:
    """Remove the PID lock if it belongs to this process (or is unreadable)."""
    lock_path = Path(path)
    if not lock_path.exists():
        return
    old_pid = _read_lock_pid(lock_path)
    if old_pid is not None and old_pid != os.getpid() and pid_is_alive(old_pid):
        # Do not steal a live foreign lock.
        return
    try:
        lock_path.unlink(missing_ok=True)
    except TypeError:
        try:
            if lock_path.exists():
                lock_path.unlink()
        except OSError:
            pass
    except OSError:
        pass


def run_exit_cleanup(
    kill_browser: Optional[Callable[[], None]] = None,
    stop_bot_coro_or_fn: Any = None,
    timeout_sec: float = DEFAULT_CLEANUP_TIMEOUT_SEC,
) -> None:
    """Hard-timeout exit cleanup. Never hangs beyond *timeout_sec*.

    Order (critical):
      1) kill Edge hub browser tree first
      2) request bot stop / runner shutdown with remaining budget
    """
    global _cleanup_done
    with _cleanup_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    deadline = time.monotonic() + max(0.05, float(timeout_sec))

    if kill_browser is not None:
        try:
            kill_browser()
        except Exception:
            pass

    if stop_bot_coro_or_fn is None:
        return

    remaining = max(0.05, deadline - time.monotonic())
    try:
        result = stop_bot_coro_or_fn
        if callable(result) and not asyncio.iscoroutine(result):
            result = result()

        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(asyncio.wait_for(result, timeout=remaining))
            except (asyncio.TimeoutError, Exception):
                pass
            finally:
                try:
                    # Cancel leftover tasks so the loop can close cleanly.
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
        # Sync callables already executed above; nothing else to do.
    except Exception:
        pass


def reset_cleanup_flag_for_tests() -> None:
    """Test helper: allow run_exit_cleanup to run again in the same process."""
    global _cleanup_done
    with _cleanup_lock:
        _cleanup_done = False
