# SOLIDWORKS CLI-Anything Harness

## Target

This harness controls SOLIDWORKS through the real Windows COM automation API exposed by `SldWorks.Application`.

The cloned repository was empty, so this harness is the first implementation in `SolidWorksGui`.

## Backend Analysis

- Backend engine: SOLIDWORKS desktop application.
- Automation surface: Windows COM ProgID `SldWorks.Application` and versioned `SldWorks.Application.30`.
- Native file formats: `.SLDPRT`, `.SLDASM`, `.SLDDRW`.
- Existing CLI: no complete headless SOLIDWORKS CLI exists for normal modeling tasks.
- Render/export path: native COM calls such as `SaveAs3`, `ModelDocExtension.SaveAs`, and `SaveBMP`.

## Command Design

- `doctor` and `status` inspect the installation and active document.
- `part new` and `part box` create real SOLIDWORKS part documents.
- `open`, `save-as`, `rebuild`, `view`, and `close-active` manipulate the active SOLIDWORKS document.
- `export active` and `export screenshot` use native SOLIDWORKS save/export calls.
- `preview recipes`, `preview capture`, and `preview latest` publish preview-bundle/v1 snapshots from real SOLIDWORKS output.
- `project` commands manage the CLI-Anything JSON session with undo/redo and locked saves.

## Limitations

- Requires Windows with SOLIDWORKS installed and licensed.
- Requires `pywin32` for COM automation.
- Most commands need SOLIDWORKS to be launchable or already running.
- `part box` is intentionally a small smoke workflow; advanced feature creation should be added incrementally with real SolidWorks API validation.
