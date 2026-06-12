from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _locked_save_json(path: str | os.PathLike[str], data: dict[str, Any], **dump_kwargs: Any) -> None:
    """Atomically write JSON with best-effort exclusive locking."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        file_handle = target.open("r+", encoding="utf-8")
    except FileNotFoundError:
        file_handle = target.open("w+", encoding="utf-8")

    with file_handle as handle:
        locked = False
        lock_kind = None
        try:
            import fcntl  # type: ignore

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            lock_kind = "fcntl"
        except (ImportError, OSError):
            try:
                import msvcrt  # type: ignore

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                locked = True
                lock_kind = "msvcrt"
            except (ImportError, OSError):
                locked = False
                lock_kind = None
        try:
            handle.seek(0)
            handle.truncate()
            json.dump(data, handle, **dump_kwargs)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            if locked and lock_kind == "fcntl":
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # type: ignore[name-defined]
            elif locked and lock_kind == "msvcrt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[name-defined]


@dataclass
class Session:
    data: dict[str, Any] = field(default_factory=dict)
    project_path: str | None = None
    _undo: list[dict[str, Any]] = field(default_factory=list)
    _redo: list[dict[str, Any]] = field(default_factory=list)
    _modified: bool = False

    @classmethod
    def new(cls, name: str = "solidworks-session") -> "Session":
        return cls(
            data={
                "schema": "cli-anything-solidworks/session-v1",
                "name": name,
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "active_document": None,
                "documents": [],
                "last_preview": None,
                "events": [],
            }
        )

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Session":
        target = Path(path)
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls(data=data, project_path=str(target))

    def has_project(self) -> bool:
        return bool(self.data)

    def snapshot(self, label: str) -> None:
        self._undo.append(deepcopy(self.data))
        self._redo.clear()
        self.data.setdefault("events", []).append({"time": utc_now(), "label": label})
        self._modified = True

    def mark(self, label: str) -> None:
        self.data.setdefault("events", []).append({"time": utc_now(), "label": label})
        self.data["updated_at"] = utc_now()
        self._modified = True

    def undo(self) -> dict[str, Any]:
        if not self._undo:
            raise RuntimeError("Nothing to undo.")
        self._redo.append(deepcopy(self.data))
        self.data = self._undo.pop()
        self._modified = True
        return self.data

    def redo(self) -> dict[str, Any]:
        if not self._redo:
            raise RuntimeError("Nothing to redo.")
        self._undo.append(deepcopy(self.data))
        self.data = self._redo.pop()
        self._modified = True
        return self.data

    def set_active_document(self, path: str | None, title: str | None = None) -> None:
        self.data["active_document"] = {"path": path, "title": title, "updated_at": utc_now()}
        if path:
            docs = self.data.setdefault("documents", [])
            if path not in [item.get("path") for item in docs if isinstance(item, dict)]:
                docs.append({"path": path, "title": title, "first_seen_at": utc_now()})
        self.mark("active-document")

    def save(self, path: str | os.PathLike[str] | None = None) -> str:
        if path is not None:
            self.project_path = str(path)
        if not self.project_path:
            raise RuntimeError("No session path supplied.")
        self.data["updated_at"] = utc_now()
        _locked_save_json(self.project_path, self.data, indent=2, ensure_ascii=False)
        self._modified = False
        return self.project_path


_SESSION: Session | None = None


def get_session() -> Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = Session.new()
    return _SESSION


def set_session(session: Session) -> Session:
    global _SESSION
    _SESSION = session
    return session
