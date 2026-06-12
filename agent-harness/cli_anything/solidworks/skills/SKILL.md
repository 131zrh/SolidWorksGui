---
name: cli-anything-solidworks
description: Use when the user wants Codex to control SOLIDWORKS through a CLI, create or open parts/assemblies/drawings, save/export documents, run macros, or publish preview bundles from the real SOLIDWORKS COM backend.
---

# CLI-Anything SOLIDWORKS

Use `cli-anything-solidworks` to operate the real SOLIDWORKS desktop application through Windows COM automation.

Always prefer `--json` for agent use:

```powershell
cli-anything-solidworks --json doctor
cli-anything-solidworks --project demo.session.json --json part box --width 0.08 --depth 0.05 --height 0.02 --save-as demo_box.SLDPRT
cli-anything-solidworks --project demo.session.json --json preview capture --output-root .
```

Key commands: `doctor`, `status`, `project`, `part`, `open`, `save-as`, `rebuild`, `view`, `export`, `run-macro`, and `preview`.

SOLIDWORKS is a hard dependency; this harness uses COM automation and native `SaveAs`/`SaveBMP` calls rather than fake CAD output.
