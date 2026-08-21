"""Nur eine Instanz je Datenordner.

Zwei Instanzen auf demselben Datenordner sind kein theoretisches Problem: Die
zweite liest den Stand beim Start, die erste schreibt weiter, und wer zuletzt
speichert gewinnt. Der Nutzer merkt es erst, wenn Eingaben verschwunden sind.

Gesperrt wird ausdruecklich nur der Datenordner, nicht das Programm: Zwei
Instanzen mit getrennten Datenordnern duerfen nebeneinander laufen, und die
anderen Programme der Suite sowieso.

Warum ``os.mkdir`` und keine Sperrdatei von Qt: Ein Qt-Stale-Timeout kann eine
lange laufende Anwendung faelschlich fuer abgestuerzt halten. ``os.mkdir`` ist
atomar, und ob der Eigentuemer noch lebt, beantwortet seine PID.

Wortgleich mit BudgetManager/main.py, wo dieser Schutz zuerst entstand.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path

_log = logging.getLogger(__name__)


def is_pid_alive(pid: int | str | None) -> bool:
    """Ob die PID wahrscheinlich zu einem laufenden Prozess gehoert.

    Unter POSIX das uebliche, nicht-destruktive ``os.kill(pid, 0)``. Unter
    Windows bewusst *kein* ``os.kill`` - das wuerde den Prozess beenden -,
    sondern ein Handle mit Abfragerecht.

    Im Zweifel gilt der Prozess als lebendig. Ein faelschlich entferntes Lock
    waere schlimmer als eines, das einmal zu lange liegen bleibt.
    """
    try:
        wert = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if wert <= 0:
        return False
    if os.name == "nt":
        return _lebt_windows(wert)
    return _lebt_posix(wert)


def _lebt_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Es gibt ihn, er gehoert nur jemand anderem.
        return True
    except OSError:
        return True
    return True


def _lebt_windows(pid: int) -> bool:  # pragma: no cover - nur unter Windows
    import ctypes

    SYNCHRONIZE = 0x00100000
    QUERY_LIMITED = 0x1000
    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(SYNCHRONIZE | QUERY_LIMITED, False, pid)
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) != 0
    finally:
        kernel.CloseHandle(handle)


class SingleInstanceGuard:
    """Sperrt einen Datenordner fuer genau eine laufende Instanz."""

    def __init__(self, lock_dir: Path | str, *, app_id: str) -> None:
        self.lock_dir = Path(lock_dir)
        self.app_id = app_id
        self.acquired = False

    def _gespeicherte_pid(self) -> int | None:
        try:
            return int((self.lock_dir / "pid").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def acquire(self) -> tuple[bool, str]:
        """(True, "") wenn die Sperre uns gehoert, sonst (False, Grund)."""
        self.lock_dir.parent.mkdir(parents=True, exist_ok=True)
        for _versuch in range(2):
            try:
                os.mkdir(self.lock_dir)
            except FileExistsError:
                pid = self._gespeicherte_pid()
                if pid is not None and is_pid_alive(pid):
                    return False, f"{self.app_id} laeuft bereits (PID {pid})."
                # Zurueckgebliebene Sperre eines abgestuerzten Laufs.
                try:
                    shutil.rmtree(self.lock_dir)
                except OSError as fehler:
                    return False, f"Sperre nicht uebernehmbar: {fehler}"
                continue
            except OSError as fehler:
                return False, f"Sperre nicht anlegbar: {fehler}"

            (self.lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")
            (self.lock_dir / "owner.json").write_text(
                json.dumps(
                    {"app_id": self.app_id, "pid": os.getpid(), "cmdline": sys.argv},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.acquired = True
            return True, ""
        return False, "Sperre nicht anlegbar."

    def release(self) -> None:
        """Gibt die Sperre frei - nur die eigene."""
        if not self.acquired:
            return
        try:
            if self._gespeicherte_pid() == os.getpid():
                shutil.rmtree(self.lock_dir)
        except OSError as fehler:
            _log.debug("Sperre nicht entfernbar: %s", fehler)
        finally:
            self.acquired = False

    def __enter__(self) -> SingleInstanceGuard:
        return self

    def __exit__(self, *_ausnahme: object) -> None:
        self.release()
