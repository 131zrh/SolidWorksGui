---
name: cli-anything-solidworks
description: Use when the user wants Codex to control SOLIDWORKS through a CLI, create or open parts/assemblies/drawings, save/export documents, run macros, or publish preview bundles from the real SOLIDWORKS COM backend.
---

# CLI-Anything SOLIDWORKS

Use `cli-anything-solidworks` to operate the real SOLIDWORKS desktop application through Windows COM automation.

## Requirements

- Windows with SOLIDWORKS installed and licensed
- Python package installed from this harness: `pip install -e agent-harness`
- Python dependencies: `click`, `prompt-toolkit`, `pywin32`

SOLIDWORKS is a hard dependency. Do not fake CAD output in Python.

## Command Pattern

Always prefer `--json` for agent use:

```powershell
cli-anything-solidworks --json doctor
cli-anything-solidworks --project demo.session.json --json status
```

Session-backed commands accept:

- `--project <session.json>` to load or create a session.
- `--dry-run` to suppress auto-save after mutations.
- `--prog-id SldWorks.Application` to override the COM ProgID.
- `--visible` or `--hidden` to control SOLIDWORKS visibility.

## Common Workflows

Create and preview a block part:

```powershell
cli-anything-solidworks --project demo.session.json --json project new demo.session.json
cli-anything-solidworks --project demo.session.json --json part box --width 0.08 --depth 0.05 --height 0.02 --save-as demo_box.SLDPRT
cli-anything-solidworks --project demo.session.json --json view isometric
cli-anything-solidworks --project demo.session.json --json preview capture --output-root .
```

Open an existing model and export a screenshot:

```powershell
cli-anything-solidworks --project inspect.session.json --json open C:\models\part.SLDPRT
cli-anything-solidworks --project inspect.session.json --json status
cli-anything-solidworks --project inspect.session.json --json export screenshot C:\models\part.bmp
```

Run a macro:

```powershell
cli-anything-solidworks --project macro.session.json --json run-macro C:\macros\build.swp --module Module1 --procedure main
```

## Command Groups

- `doctor`: verify COM, SOLIDWORKS revision, and executable discovery.
- `launch`: launch `SLDWORKS.exe` when discoverable.
- `status`: return active document metadata.
- `project`: create, inspect, save, undo, and redo session state.
- `part`: create a new part or a simple extruded box.
- `open`: open `.SLDPRT`, `.SLDASM`, or `.SLDDRW`.
- `save-as`: save the active document.
- `rebuild`: force-rebuild the active document.
- `view`: set a named view such as `front`, `top`, or `isometric`.
- `export`: save active document or capture a BMP screenshot through native APIs.
- `run-macro`: run a SOLIDWORKS macro through `RunMacro2`.
- `preview`: publish truthful preview bundles from the active SOLIDWORKS document.

## Preview

Producer commands:

```powershell
cli-anything-solidworks --json preview recipes
cli-anything-solidworks --project demo.session.json --json preview capture --output-root .
cli-anything-solidworks --project demo.session.json --json preview latest --output-root .
```

Consumer commands are read-only and belong to `cli-hub`, for example:

```powershell
cli-hub previews inspect .\.cli-anything\previews\active-bmp\<bundle-id>
```

The `active-bmp` recipe uses SOLIDWORKS `SaveBMP` from the active document. Returned JSON includes `_bundle_dir`, `_manifest_path`, `_summary_path`, and `primary_artifact`.

## Error Handling

If COM creation fails, ask the user to launch SOLIDWORKS, verify the license, or run `cli-anything-solidworks --json doctor`. If a document operation fails, inspect `status` before retrying.
