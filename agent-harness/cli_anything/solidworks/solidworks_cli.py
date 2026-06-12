from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sys
from typing import Any

import click

from cli_anything.solidworks import __version__
from cli_anything.solidworks.core import preview as preview_core
from cli_anything.solidworks.core.project import create_session, open_session
from cli_anything.solidworks.core.session import Session, get_session, set_session
from cli_anything.solidworks.utils.solidworks_backend import SolidWorksBackend, SolidWorksError
from cli_anything.solidworks.utils.repl_skin import ReplSkin


_REPL_MODE = False


def _ctx_obj() -> dict[str, Any]:
    return click.get_current_context().obj or {}


def _backend() -> SolidWorksBackend:
    obj = _ctx_obj()
    backend = obj.get("backend")
    if backend is None:
        backend = SolidWorksBackend(
            prog_id=obj.get("prog_id", "SldWorks.Application"),
            visible=obj.get("visible", True),
        )
        obj["backend"] = backend
    return backend


def _emit(payload: Any, use_json: bool | None = None) -> Any:
    if use_json is None:
        use_json = bool(_ctx_obj().get("json"))
    if use_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, (dict, list)):
                    click.echo(f"{key}: {json.dumps(value, ensure_ascii=False, default=str)}")
                else:
                    click.echo(f"{key}: {value}")
        else:
            click.echo(payload)
    return payload


def _handle_error(exc: Exception) -> None:
    if _ctx_obj().get("json"):
        click.echo(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False), err=True)
    else:
        click.echo(f"Error: {exc}", err=True)
    raise click.Abort()


def _load_project(project_path: str | None) -> Session:
    if project_path:
        if os.path.exists(project_path):
            return set_session(open_session(project_path))
        session = Session.new(name=Path(project_path).stem)
        session.project_path = str(Path(project_path).resolve())
        return set_session(session)
    return get_session()


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output machine-readable JSON.")
@click.option("--project", "project_path", type=click.Path(), help="Session JSON path.")
@click.option("--dry-run", is_flag=True, help="Do not auto-save session mutations.")
@click.option("--prog-id", default="SldWorks.Application", show_default=True, help="SOLIDWORKS COM ProgID.")
@click.option("--visible/--hidden", default=True, show_default=True, help="Show or hide SOLIDWORKS.")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project_path: str | None, dry_run: bool, prog_id: str, visible: bool) -> None:
    """Control SOLIDWORKS through the real Windows COM automation API."""
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "json": use_json,
            "project_path": project_path,
            "dry_run": dry_run,
            "prog_id": prog_id,
            "visible": visible,
        }
    )
    _load_project(project_path)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.result_callback()
def auto_save_on_exit(result: Any, **_: Any) -> None:
    if _REPL_MODE or _ctx_obj().get("dry_run"):
        return
    session = get_session()
    if session.project_path and session._modified:
        try:
            session.save()
        except Exception as exc:
            click.echo(f"Warning: Auto-save failed: {exc}", err=True)


@cli.command()
def repl() -> None:
    """Start an interactive SOLIDWORKS command session."""
    global _REPL_MODE
    _REPL_MODE = True
    skin = ReplSkin("solidworks", version=__version__)
    skin.print_banner()
    skin.info("Type 'help' for commands, 'exit' to quit.")
    pt_session = skin.create_prompt_session()
    while True:
        try:
            line = skin.get_input(pt_session, project_name="solidworks", modified=get_session()._modified)
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip():
            continue
        if line.strip() in {"exit", "quit"}:
            break
        if line.strip() == "help":
            skin.help(
                {
                    "doctor": "Check COM and installation status",
                    "status": "Show SOLIDWORKS and active document status",
                    "part box": "Create a simple extruded box",
                    "open": "Open a SLDPRT/SLDASM/SLDDRW file",
                    "save-as": "Save active document",
                    "preview capture": "Publish a truthful preview bundle",
                }
            )
            continue
        try:
            args = shlex.split(line)
            cli.main(args=args, prog_name="cli-anything-solidworks", standalone_mode=False, obj=_ctx_obj())
        except SystemExit:
            pass
        except Exception as exc:
            skin.error(str(exc))
    skin.print_goodbye()


@cli.command()
def doctor() -> None:
    """Check Python, COM, registry, and SOLIDWORKS availability."""
    try:
        backend = _backend()
        status = backend.status()
        status["pywin32"] = True
        _emit(status)
    except Exception as exc:
        _handle_error(exc)


@cli.command()
def launch() -> None:
    """Launch SOLIDWORKS if SLDWORKS.exe can be found."""
    try:
        _emit(_backend().launch())
    except Exception as exc:
        _handle_error(exc)


@cli.command()
def status() -> None:
    """Show SOLIDWORKS status and active document information."""
    try:
        _emit(_backend().status())
    except Exception as exc:
        _handle_error(exc)


@cli.group()
def project() -> None:
    """Manage CLI-Anything session state."""


@project.command("new")
@click.argument("path", type=click.Path())
@click.option("--name", default="solidworks-session", show_default=True)
def project_new(path: str, name: str) -> None:
    try:
        session = create_session(path, name=name)
        set_session(session)
        _emit({"ok": True, "session_path": session.project_path, "session": session.data})
    except Exception as exc:
        _handle_error(exc)


@project.command("info")
def project_info() -> None:
    session = get_session()
    _emit({"project_path": session.project_path, "modified": session._modified, "session": session.data})


@project.command("save")
@click.argument("path", required=False, type=click.Path())
def project_save(path: str | None) -> None:
    try:
        _emit({"ok": True, "session_path": get_session().save(path)})
    except Exception as exc:
        _handle_error(exc)


@project.command()
def undo() -> None:
    try:
        _emit({"ok": True, "session": get_session().undo()})
    except Exception as exc:
        _handle_error(exc)


@project.command()
def redo() -> None:
    try:
        _emit({"ok": True, "session": get_session().redo()})
    except Exception as exc:
        _handle_error(exc)


@cli.group()
def part() -> None:
    """Create or manipulate SOLIDWORKS part documents."""


@part.command("new")
@click.option("--template", type=click.Path(exists=True), help="Optional part template path.")
def part_new(template: str | None) -> None:
    try:
        get_session().snapshot("part-new")
        result = _backend().new_part(template=template)
        get_session().set_active_document(result.get("path"), result.get("title"))
        _emit({"ok": True, "document": result})
    except Exception as exc:
        _handle_error(exc)


@part.command("box")
@click.option("--width", default=0.1, show_default=True, type=float, help="Width in meters.")
@click.option("--depth", default=0.1, show_default=True, type=float, help="Depth in meters.")
@click.option("--height", default=0.05, show_default=True, type=float, help="Extrusion height in meters.")
@click.option("--template", type=click.Path(exists=True), help="Optional part template path.")
@click.option("--save-as", "save_as_path", type=click.Path(), help="Optional output .SLDPRT path.")
def part_box(width: float, depth: float, height: float, template: str | None, save_as_path: str | None) -> None:
    """Create a simple extruded rectangular block in the real SOLIDWORKS app."""
    try:
        get_session().snapshot("part-box")
        result = _backend().create_box(width=width, depth=depth, height=height, template=template)
        if save_as_path:
            result["save"] = _backend().save_as(save_as_path)
            get_session().set_active_document(save_as_path, result["save"]["document"].get("title"))
        _emit(result)
    except Exception as exc:
        _handle_error(exc)


@cli.command("open")
@click.argument("path", type=click.Path(exists=True))
@click.option("--type", "doc_type", type=click.Choice(["part", "assembly", "drawing"]), help="Override document type.")
def open_doc(path: str, doc_type: str | None) -> None:
    try:
        type_map = {"part": 1, "assembly": 2, "drawing": 3}
        get_session().snapshot("open-document")
        result = _backend().open_document(path, doc_type=type_map.get(doc_type or ""))
        get_session().set_active_document(result.get("path"), result.get("title"))
        _emit({"ok": True, "document": result})
    except Exception as exc:
        _handle_error(exc)


@cli.command("save-as")
@click.argument("path", type=click.Path())
def save_as(path: str) -> None:
    try:
        get_session().snapshot("save-as")
        result = _backend().save_as(path)
        get_session().set_active_document(result["output"], result["document"].get("title"))
        _emit({"ok": True, **result})
    except Exception as exc:
        _handle_error(exc)


@cli.command()
def rebuild() -> None:
    """Force-rebuild the active document."""
    try:
        get_session().snapshot("rebuild")
        _emit(_backend().rebuild())
    except Exception as exc:
        _handle_error(exc)


@cli.command("close-active")
def close_active() -> None:
    """Close the active SOLIDWORKS document."""
    try:
        get_session().snapshot("close-active")
        _emit(_backend().close_active())
    except Exception as exc:
        _handle_error(exc)


@cli.command("view")
@click.argument("name", default="isometric")
@click.option("--no-zoom", is_flag=True, help="Do not zoom to fit after changing view.")
def view(name: str, no_zoom: bool) -> None:
    """Set a named view on the active document."""
    try:
        get_session().snapshot("view")
        _emit(_backend().set_view(name, zoom_to_fit=not no_zoom))
    except Exception as exc:
        _handle_error(exc)


@cli.group()
def export() -> None:
    """Export active SOLIDWORKS document through native SaveAs/SaveBMP calls."""


@export.command("active")
@click.argument("path", type=click.Path())
def export_active(path: str) -> None:
    try:
        get_session().snapshot("export-active")
        _emit({"ok": True, **_backend().save_as(path)})
    except Exception as exc:
        _handle_error(exc)


@export.command("screenshot")
@click.argument("path", type=click.Path())
@click.option("--width", default=1600, show_default=True, type=int)
@click.option("--height", default=1000, show_default=True, type=int)
def export_screenshot(path: str, width: int, height: int) -> None:
    try:
        get_session().snapshot("export-screenshot")
        _emit({"ok": True, **_backend().screenshot(path, width=width, height=height)})
    except Exception as exc:
        _handle_error(exc)


@cli.command("run-macro")
@click.argument("macro_path", type=click.Path(exists=True))
@click.option("--module", default="", help="Macro module name.")
@click.option("--procedure", default="", help="Macro procedure name.")
def run_macro(macro_path: str, module: str, procedure: str) -> None:
    """Run a SOLIDWORKS macro through RunMacro2."""
    try:
        get_session().snapshot("run-macro")
        _emit(_backend().run_macro(macro_path, module=module, procedure=procedure))
    except Exception as exc:
        _handle_error(exc)


@cli.group()
def preview() -> None:
    """Publish truthful preview bundles from the active SOLIDWORKS document."""


@preview.command("recipes")
def preview_recipes() -> None:
    _emit(preview_core.recipes())


@preview.command("capture")
@click.option("--recipe", default="active-bmp", show_default=True)
@click.option("--output-root", type=click.Path(), default=".", show_default=True)
@click.option("--width", default=1600, show_default=True, type=int)
@click.option("--height", default=1000, show_default=True, type=int)
def preview_capture(recipe: str, output_root: str, width: int, height: int) -> None:
    try:
        result = preview_core.capture(
            _backend(),
            output_root=output_root,
            recipe=recipe,
            command="cli-anything-solidworks preview capture",
            width=width,
            height=height,
        )
        get_session().data["last_preview"] = {
            "bundle_dir": result["_bundle_dir"],
            "manifest_path": result["_manifest_path"],
            "summary_path": result["_summary_path"],
        }
        get_session().mark("preview-capture")
        _emit(result)
    except Exception as exc:
        _handle_error(exc)


@preview.command("latest")
@click.option("--recipe", default="active-bmp", show_default=True)
@click.option("--output-root", type=click.Path(), default=".", show_default=True)
def preview_latest(recipe: str, output_root: str) -> None:
    try:
        _emit(preview_core.latest(output_root=output_root, recipe=recipe))
    except Exception as exc:
        _handle_error(exc)


def main() -> None:
    try:
        cli.main(prog_name="cli-anything-solidworks")
    except SolidWorksError as exc:
        _handle_error(exc)


if __name__ == "__main__":
    main()
