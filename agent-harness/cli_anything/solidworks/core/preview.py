from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cli_anything.solidworks.utils.solidworks_backend import SolidWorksBackend


RECIPES = {
    "active-bmp": {
        "description": "Capture the active SOLIDWORKS document with SaveBMP.",
        "artifact_role": "hero",
        "extension": ".bmp",
    }
}


def recipes() -> dict[str, Any]:
    return {"recipes": [{"name": name, **data} for name, data in RECIPES.items()]}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fingerprint(paths: list[str | None]) -> str:
    h = hashlib.sha256()
    for item in paths:
        if not item:
            continue
        p = Path(item)
        h.update(str(p.resolve()).encode("utf-8", "ignore"))
        if p.exists():
            h.update(str(p.stat().st_mtime_ns).encode("ascii"))
            h.update(str(p.stat().st_size).encode("ascii"))
    return h.hexdigest()


def capture(
    backend: SolidWorksBackend,
    output_root: str | os.PathLike[str],
    recipe: str = "active-bmp",
    command: str = "preview capture",
    width: int = 1600,
    height: int = 1000,
) -> dict[str, Any]:
    if recipe not in RECIPES:
        raise RuntimeError(f"Unknown preview recipe {recipe!r}. Use preview recipes.")
    active = backend.active_info()
    bundle_id = f"{recipe}-{_stamp()}"
    bundle_dir = Path(output_root).resolve() / ".cli-anything" / "previews" / recipe / bundle_id
    artifact_dir = bundle_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"active{RECIPES[recipe]['extension']}"
    shot = backend.screenshot(str(artifact_path), width=width, height=height)
    fingerprint = _fingerprint([active.get("path"), shot.get("output")])

    manifest = {
        "schema": "preview-bundle/v1",
        "bundle_id": bundle_id,
        "software": "solidworks",
        "recipe": recipe,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_fingerprint": fingerprint,
        "command": command,
        "artifacts": [
            {
                "path": "artifacts/" + artifact_path.name,
                "role": RECIPES[recipe]["artifact_role"],
                "mime": "image/bmp",
                "file_size": os.path.getsize(artifact_path),
            }
        ],
    }
    summary = {
        "status": "complete",
        "truthfulness": "Captured from the real SOLIDWORKS active document through SaveBMP.",
        "active_document": active,
        "artifact_count": 1,
        "primary_artifact": str(artifact_path),
    }
    manifest_path = bundle_dir / "manifest.json"
    summary_path = bundle_dir / "summary.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_path = bundle_dir.parent / "latest.json"
    latest = {
        "bundle_id": bundle_id,
        "_bundle_dir": str(bundle_dir),
        "_manifest_path": str(manifest_path),
        "_summary_path": str(summary_path),
        "primary_artifact": str(artifact_path),
    }
    latest_path.write_text(json.dumps(latest, indent=2), encoding="utf-8")
    return {**latest, "manifest": manifest, "summary": summary}


def latest(output_root: str | os.PathLike[str], recipe: str = "active-bmp") -> dict[str, Any]:
    latest_path = Path(output_root).resolve() / ".cli-anything" / "previews" / recipe / "latest.json"
    if not latest_path.exists():
        raise RuntimeError(f"No latest preview exists for recipe {recipe!r}. Run preview capture first.")
    return json.loads(latest_path.read_text(encoding="utf-8"))
