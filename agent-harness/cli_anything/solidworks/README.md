# cli-anything-solidworks

Control SOLIDWORKS from a CLI using the real Windows COM automation API.

## Requirements

- Windows
- SOLIDWORKS installed and licensed
- Python 3.10+
- `pywin32`, `click`, and `prompt-toolkit`

Install locally:

```powershell
cd agent-harness
python -m pip install -e .
```

## Quick Start

```powershell
cli-anything-solidworks --json doctor
cli-anything-solidworks --json status
cli-anything-solidworks --project demo.session.json project new demo.session.json
cli-anything-solidworks --project demo.session.json part box --width 0.08 --depth 0.05 --height 0.02 --save-as demo.SLDPRT --json
cli-anything-solidworks --project demo.session.json part mounting-plate --save-as plate.SLDPRT --json
cli-anything-solidworks --project demo.session.json view isometric
cli-anything-solidworks --project demo.session.json export screenshot preview.bmp --json
```

Running without a subcommand starts the REPL:

```powershell
cli-anything-solidworks
```

## Commands

- `doctor`: verify SOLIDWORKS COM automation and installation details.
- `launch`: start `SLDWORKS.exe` when discoverable.
- `status`: inspect the current SOLIDWORKS instance and active document.
- `project new/info/save/undo/redo`: manage session state.
- `part new`: create a new part from a template or default part template.
- `part box`: create a simple extruded rectangular block in a real part document.
- `part mounting-plate`: create a plate with four mounting holes and a center bore.
- `open`: open `.SLDPRT`, `.SLDASM`, or `.SLDDRW` files.
- `save-as`: save the active document to a target path.
- `rebuild`: force rebuild the active document.
- `view`: set a named view such as `front`, `top`, or `isometric`.
- `export active`: export the active document through SOLIDWORKS SaveAs.
- `export screenshot`: create a BMP screenshot through SOLIDWORKS SaveBMP.
- `run-macro`: run a SOLIDWORKS macro through `RunMacro2`.

## Preview

Preview is a producer surface. Publish bundles with this CLI, then inspect them with a preview consumer such as `cli-hub previews`.

```powershell
cli-anything-solidworks --project demo.session.json preview recipes --json
cli-anything-solidworks --project demo.session.json preview capture --output-root . --json
cli-hub previews inspect .\.cli-anything\previews\active-bmp\<bundle-id>
```

The `active-bmp` recipe captures the active SOLIDWORKS document through the real `SaveBMP` API and writes a `preview-bundle/v1` directory with `manifest.json`, `summary.json`, and `artifacts/active.bmp`.

## Agent Guidance

Use `--json` for every command when another program will parse the result. Treat SOLIDWORKS as a hard dependency: if COM automation fails, fix the installation or license state rather than using a fake fallback.
