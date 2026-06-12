from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import subprocess
from typing import Any


DOC_TYPES = {
    ".sldprt": 1,
    ".sldasm": 2,
    ".slddrw": 3,
}


class SolidWorksError(RuntimeError):
    pass


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise SolidWorksError("SOLIDWORKS COM automation requires Windows.")


def _import_win32() -> Any:
    _require_windows()
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise SolidWorksError(
            "pywin32 is required for SOLIDWORKS COM automation. Install with: pip install pywin32"
        ) from exc
    pythoncom.CoInitialize()
    return win32com.client


def find_solidworks_executable() -> str | None:
    candidates = [
        r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe",
        r"C:\Program Files\SolidWorks Corp\SolidWorks\SLDWORKS.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    try:
        import winreg

        roots = [
            (winreg.HKEY_CLASSES_ROOT, r"Applications\SLDWORKS.exe\shell\open\command"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\SLDWORKS.exe"),
        ]
        for hive, key_path in roots:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                exe = _extract_exe(value)
                if exe and os.path.exists(exe):
                    return exe
            except OSError:
                continue
    except ImportError:
        pass
    return None


def find_default_part_template() -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    key_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\SolidWorks\SOLIDWORKS 2022\Document Templates"),
        (winreg.HKEY_CURRENT_USER, r"Software\SolidWorks\SOLIDWORKS 2023\Document Templates"),
        (winreg.HKEY_CURRENT_USER, r"Software\SolidWorks\SOLIDWORKS 2024\Document Templates"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SolidWorks\SOLIDWORKS 2022\Document Templates"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SolidWorks\SOLIDWORKS 2023\Document Templates"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SolidWorks\SOLIDWORKS 2024\Document Templates"),
    ]
    value_names = ["Default Part template", "Default Part Template", "Custom Part Document Template"]
    for hive, key_path in key_paths:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                for value_name in value_names:
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if value and os.path.exists(value):
                        return value
        except OSError:
            continue

    roots = [
        Path(r"C:\ProgramData\SOLIDWORKS"),
        Path(r"C:\Program Files\SOLIDWORKS Corp"),
    ]
    for root in roots:
        if root.exists():
            for candidate in root.rglob("*.prtdot"):
                if candidate.name.lower() in {"gb_part.prtdot", "part.prtdot"}:
                    return str(candidate)
    return None


def _extract_exe(command: str) -> str | None:
    text = command.strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        if end > 0:
            return text[1:end]
    lower = text.lower()
    marker = ".exe"
    idx = lower.find(marker)
    if idx >= 0:
        return text[: idx + len(marker)]
    return None


@dataclass
class SolidWorksBackend:
    prog_id: str = "SldWorks.Application"
    visible: bool = True
    app: Any | None = None

    def connect(self, create: bool = True) -> Any:
        client = _import_win32()
        if self.app is not None:
            return self.app
        try:
            self.app = client.GetActiveObject(self.prog_id)
        except Exception:
            if not create:
                raise SolidWorksError(
                    f"No running SOLIDWORKS instance found for {self.prog_id}. Start SOLIDWORKS or allow creation."
                )
            self.app = client.Dispatch(self.prog_id)
        try:
            self.app.Visible = bool(self.visible)
        except Exception:
            pass
        return self.app

    def status(self) -> dict[str, Any]:
        app = self.connect(create=True)
        active = None
        try:
            doc = app.ActiveDoc
            if doc is not None:
                active = self._document_info(doc)
        except Exception:
            active = None
        return {
            "ok": True,
            "prog_id": self.prog_id,
            "visible": self.visible,
            "revision": _safe_call(app, "RevisionNumber"),
            "executable": find_solidworks_executable(),
            "active_document": active,
        }

    def new_part(self, template: str | None = None) -> dict[str, Any]:
        app = self.connect(create=True)
        doc = None
        if template:
            doc = app.NewDocument(str(Path(template).resolve()), 0, 0, 0)
        else:
            template = find_default_part_template()
            if template and os.path.exists(template):
                doc = app.NewDocument(template, 0, 0, 0)
            else:
                try:
                    doc = app.NewPart()
                except Exception as exc:
                    raise SolidWorksError(
                        "Could not create a part. Provide --template with a valid SOLIDWORKS part template."
                    ) from exc
        if doc is None:
            raise SolidWorksError("SOLIDWORKS returned no document for new part.")
        return self._document_info(doc)

    def open_document(self, path: str, doc_type: int | None = None, silent: bool = True) -> dict[str, Any]:
        app = self.connect(create=True)
        target = str(Path(path).resolve())
        if not os.path.exists(target):
            raise SolidWorksError(f"Document not found: {target}")
        doc_type = doc_type or DOC_TYPES.get(Path(target).suffix.lower(), 1)
        errors = 0
        warnings = 0
        try:
            doc = app.OpenDoc6(target, doc_type, 1 if silent else 0, "", errors, warnings)
        except Exception:
            doc = app.OpenDoc(target, doc_type)
        if doc is None:
            raise SolidWorksError(f"SOLIDWORKS could not open: {target}")
        return self._document_info(doc)

    def active_document(self) -> Any:
        app = self.connect(create=True)
        doc = app.ActiveDoc
        if doc is None:
            raise SolidWorksError("No active SOLIDWORKS document.")
        return doc

    def active_info(self) -> dict[str, Any]:
        return self._document_info(self.active_document())

    def save_as(self, path: str) -> dict[str, Any]:
        doc = self.active_document()
        target = str(Path(path).resolve())
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        errors = 0
        warnings = 0
        ok = False
        try:
            ok = bool(doc.SaveAs3(target, 0, 2))
        except Exception:
            try:
                ok = bool(doc.Extension.SaveAs(target, 0, 1, None, errors, warnings))
            except Exception as exc:
                raise SolidWorksError(f"SaveAs failed for {target}: {exc}") from exc
        if not ok and not os.path.exists(target):
            raise SolidWorksError(f"SOLIDWORKS did not save output: {target}")
        return {"output": target, "exists": os.path.exists(target), "document": self._document_info(doc)}

    def rebuild(self) -> dict[str, Any]:
        doc = self.active_document()
        try:
            ok = bool(doc.ForceRebuild3(False))
        except Exception:
            ok = bool(doc.EditRebuild3())
        return {"ok": ok, "document": self._document_info(doc)}

    def close_active(self) -> dict[str, Any]:
        app = self.connect(create=True)
        doc = self.active_document()
        title = _safe_call(doc, "GetTitle") or getattr(doc, "GetTitle", None)
        try:
            app.CloseDoc(title)
        except Exception as exc:
            raise SolidWorksError(f"Could not close active document {title!r}: {exc}") from exc
        return {"closed": title}

    def set_view(self, view: str = "isometric", zoom_to_fit: bool = True) -> dict[str, Any]:
        doc = self.active_document()
        view_map = {
            "front": "*Front",
            "back": "*Back",
            "left": "*Left",
            "right": "*Right",
            "top": "*Top",
            "bottom": "*Bottom",
            "isometric": "*Isometric",
            "trimetric": "*Trimetric",
            "dimetric": "*Dimetric",
        }
        named = view_map.get(view.lower(), view)
        ok = bool(doc.ShowNamedView2(named, -1))
        if zoom_to_fit:
            doc.ViewZoomtofit2()
        return {"ok": ok, "view": named, "document": self._document_info(doc)}

    def screenshot(self, path: str, width: int = 1600, height: int = 1000) -> dict[str, Any]:
        doc = self.active_document()
        target = str(Path(path).resolve())
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        try:
            ok = bool(doc.SaveBMP(target, int(width), int(height)))
        except Exception as exc:
            raise SolidWorksError(f"Screenshot failed. SOLIDWORKS SaveBMP error: {exc}") from exc
        if not ok or not os.path.exists(target):
            raise SolidWorksError(f"SOLIDWORKS did not create screenshot: {target}")
        return {"output": target, "file_size": os.path.getsize(target), "document": self._document_info(doc)}

    def create_box(self, width: float, depth: float, height: float, template: str | None = None) -> dict[str, Any]:
        doc_info = self.new_part(template=template)
        doc = self.active_document()
        try:
            try:
                doc.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
            except Exception:
                # Some localized/template contexts reject plane selection by English name.
                # New part documents still allow a first sketch in the default sketch plane.
                pass
            doc.SketchManager.InsertSketch(True)
            doc.SketchManager.CreateCenterRectangle(0, 0, 0, width / 2.0, depth / 2.0, 0)
            doc.SketchManager.InsertSketch(True)
            feature = doc.FeatureManager.FeatureExtrusion2(
                True, False, False, 0, 0, height, 0, False, False, False, False,
                0, 0, False, False, False, False, True, True, True, 0, 0, False
            )
            if feature is None:
                raise SolidWorksError("FeatureExtrusion2 returned no feature.")
            doc.ViewZoomtofit2()
            return {"ok": True, "operation": "create_box", "dimensions_m": [width, depth, height], "document": doc_info}
        except Exception as exc:
            raise SolidWorksError(f"Could not create box feature: {exc}") from exc

    def create_mounting_plate(
        self,
        width: float,
        depth: float,
        thickness: float,
        corner_hole_radius: float,
        center_hole_radius: float,
        inset_x: float,
        inset_y: float,
        template: str | None = None,
    ) -> dict[str, Any]:
        doc_info = self.new_part(template=template)
        doc = self.active_document()
        try:
            try:
                doc.ClearSelection2(True)
            except Exception:
                pass
            try:
                doc.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
            except Exception:
                pass
            doc.SketchManager.InsertSketch(True)
            doc.SketchManager.CreateCenterRectangle(0, 0, 0, width / 2.0, depth / 2.0, 0)
            for x in (-inset_x, inset_x):
                for y in (-inset_y, inset_y):
                    doc.SketchManager.CreateCircleByRadius(x, y, 0, corner_hole_radius)
            doc.SketchManager.CreateCircleByRadius(0, 0, 0, center_hole_radius)
            doc.SketchManager.InsertSketch(True)
            feature = doc.FeatureManager.FeatureExtrusion2(
                True, False, False, 0, 0, thickness, 0.0, False, False, False, False,
                0.0, 0.0, False, False, False, False, True, True, True, 0, 0, False
            )
            if feature is None:
                raise SolidWorksError("FeatureExtrusion2 returned no feature.")
            doc.ViewZoomtofit2()
            return {
                "ok": True,
                "operation": "create_mounting_plate",
                "dimensions_m": {
                    "width": width,
                    "depth": depth,
                    "thickness": thickness,
                    "corner_hole_radius": corner_hole_radius,
                    "center_hole_radius": center_hole_radius,
                    "inset_x": inset_x,
                    "inset_y": inset_y,
                },
                "document": doc_info,
            }
        except Exception as exc:
            raise SolidWorksError(f"Could not create mounting plate: {exc}") from exc

    def run_macro(self, macro_path: str, module: str = "", procedure: str = "") -> dict[str, Any]:
        app = self.connect(create=True)
        target = str(Path(macro_path).resolve())
        if not os.path.exists(target):
            raise SolidWorksError(f"Macro not found: {target}")
        errors = 0
        try:
            ok = bool(app.RunMacro2(target, module, procedure, 0, errors))
        except Exception as exc:
            raise SolidWorksError(f"RunMacro2 failed: {exc}") from exc
        return {"ok": ok, "macro": target, "module": module, "procedure": procedure}

    def launch(self) -> dict[str, Any]:
        exe = find_solidworks_executable()
        if not exe:
            raise SolidWorksError("Could not find SLDWORKS.exe. Start SOLIDWORKS manually or repair installation.")
        subprocess.Popen([exe], close_fds=True)
        return {"launched": exe}

    def _document_info(self, doc: Any) -> dict[str, Any]:
        path = _safe_call(doc, "GetPathName")
        title = _safe_call(doc, "GetTitle")
        doc_type = _safe_call(doc, "GetType")
        return {"title": title, "path": path or None, "type": doc_type}


def _safe_call(obj: Any, name: str) -> Any:
    try:
        attr = getattr(obj, name)
        if callable(attr):
            return attr()
        return attr
    except Exception:
        return None
