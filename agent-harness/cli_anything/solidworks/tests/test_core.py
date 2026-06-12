from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_anything.solidworks.core import preview
from cli_anything.solidworks.core.session import Session
from cli_anything.solidworks.utils.solidworks_backend import DOC_TYPES, _extract_exe, find_default_part_template


def test_session_new_schema():
    session = Session.new("demo")
    assert session.data["schema"] == "cli-anything-solidworks/session-v1"
    assert session.data["name"] == "demo"


def test_session_save_load(tmp_path: Path):
    path = tmp_path / "session.json"
    session = Session.new("demo")
    session.save(path)
    loaded = Session.load(path)
    assert loaded.data["name"] == "demo"
    assert loaded.project_path == str(path)


def test_session_undo_redo():
    session = Session.new("demo")
    session.snapshot("change")
    session.data["name"] = "changed"
    session.undo()
    assert session.data["name"] == "demo"
    session.redo()
    assert session.data["name"] == "changed"


def test_set_active_document_tracks_documents():
    session = Session.new("demo")
    session.set_active_document(r"C:\tmp\part.SLDPRT", "part.SLDPRT")
    assert session.data["active_document"]["path"].endswith("part.SLDPRT")
    assert session.data["documents"][0]["title"] == "part.SLDPRT"


def test_preview_recipes_contains_active_bmp():
    names = [item["name"] for item in preview.recipes()["recipes"]]
    assert "active-bmp" in names


def test_preview_latest_missing(tmp_path: Path):
    with pytest.raises(RuntimeError):
        preview.latest(tmp_path)


def test_preview_capture_writes_bundle(tmp_path: Path):
    class FakeBackend:
        def active_info(self):
            return {"title": "fake", "path": None, "type": 1}

        def screenshot(self, path, width=1600, height=1000):
            Path(path).write_bytes(b"BMfake")
            return {"output": path, "file_size": 6}

    result = preview.capture(FakeBackend(), tmp_path)
    assert Path(result["_manifest_path"]).exists()
    assert Path(result["primary_artifact"]).read_bytes().startswith(b"BM")
    manifest = json.loads(Path(result["_manifest_path"]).read_text())
    assert manifest["schema"] == "preview-bundle/v1"


def test_extract_exe_from_quoted_command():
    assert _extract_exe(r'"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe" "%1"').endswith("SLDWORKS.exe")


def test_doc_type_mapping():
    assert DOC_TYPES[".sldprt"] == 1
    assert DOC_TYPES[".sldasm"] == 2
    assert DOC_TYPES[".slddrw"] == 3


def test_find_default_part_template_returns_string_or_none():
    value = find_default_part_template()
    assert value is None or value.lower().endswith(".prtdot")
