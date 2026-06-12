from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _resolve_cli(name: str):
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.solidworks.solidworks_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-solidworks")

    def _run(self, args, check=True):
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "Control SOLIDWORKS" in result.stdout

    def test_project_new_json(self, tmp_path: Path):
        path = tmp_path / "demo.session.json"
        result = self._run(["--json", "project", "new", str(path)])
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert path.exists()

    def test_preview_recipes_json(self):
        result = self._run(["--json", "preview", "recipes"])
        data = json.loads(result.stdout)
        assert data["recipes"][0]["name"] == "active-bmp"


class TestRealSolidWorksBackend:
    CLI_BASE = _resolve_cli("cli-anything-solidworks")

    def _run(self, args, check=True):
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_doctor_real_backend(self):
        result = self._run(["--json", "doctor"])
        data = json.loads(result.stdout)
        assert data["ok"] is True

    def test_box_save_and_preview_real_backend(self, tmp_path: Path):
        session = tmp_path / "solidworks.session.json"
        part = tmp_path / "box.SLDPRT"
        self._run(["--project", str(session), "--json", "project", "new", str(session)])
        self._run(
            [
                "--project",
                str(session),
                "--json",
                "part",
                "box",
                "--width",
                "0.05",
                "--depth",
                "0.04",
                "--height",
                "0.02",
                "--save-as",
                str(part),
            ]
        )
        assert part.exists()
        result = self._run(["--project", str(session), "--json", "preview", "capture", "--output-root", str(tmp_path)])
        data = json.loads(result.stdout)
        artifact = Path(data["primary_artifact"])
        assert artifact.exists()
        assert artifact.stat().st_size > 0
        print(f"\n  Preview BMP: {artifact} ({artifact.stat().st_size:,} bytes)")
