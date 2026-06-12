from __future__ import annotations

from pathlib import Path

from cli_anything.solidworks.core.session import Session


def create_session(path: str, name: str = "solidworks-session") -> Session:
    session = Session.new(name=name)
    session.save(path)
    return session


def open_session(path: str) -> Session:
    return Session.load(path)


def default_session_path(directory: str | None = None) -> str:
    base = Path(directory or ".").resolve()
    return str(base / "solidworks.session.json")
