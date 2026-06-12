# Test Plan

## Test Inventory Plan

- `test_core.py`: 9 unit tests planned for session locking, preview metadata, and backend helper behavior.
- `test_full_e2e.py`: 4 subprocess and real-backend tests planned.

## Unit Test Plan

### `core.session`

- Create a new session with expected schema.
- Save and load a session JSON file.
- Undo and redo session mutations.
- Save through the locked writer without truncation.

### `core.preview`

- List preview recipes.
- Report an error for missing latest preview.
- Generate valid preview bundle metadata using a fake backend that writes a BMP-like artifact.

### `utils.solidworks_backend`

- Extract executable paths from registry command strings.
- Resolve known SOLIDWORKS document extensions to API document type IDs.

## E2E Test Plan

### CLI subprocess smoke

- Run `cli-anything-solidworks --help`.
- Run `cli-anything-solidworks --json project new <path>`.
- Run `cli-anything-solidworks --json preview recipes`.

### Real SOLIDWORKS backend workflow

- Run `doctor` against the installed command.
- Create a simple box part with `part box`.
- Save the part to `.SLDPRT`.
- Capture a BMP preview bundle and verify artifact existence and nonzero size.

## Realistic Workflow Scenarios

### Simple machined block

- Simulates: agent creating a basic part for downstream CAD inspection.
- Operations chained: create session, create box, save part, set isometric view, capture preview.
- Verified: `.SLDPRT` path returned, BMP preview exists, preview manifest follows `preview-bundle/v1`.

### Existing document inspection

- Simulates: agent opening a user-supplied SolidWorks file and producing a preview.
- Operations chained: open document, status, view, export screenshot.
- Verified: active document path matches input and screenshot exists.

## Test Results

Full installed-command run on 2026-06-12:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.0.3, pluggy-1.6.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Zwh\Documents\Codex\2026-06-12\hkuds-cli-anything-git-https-github\work\SolidWorksGui\agent-harness
collecting ... [_resolve_cli] Using installed command: C:\Users\Zwh\AppData\Roaming\Python\Python312\Scripts\cli-anything-solidworks.EXE
[_resolve_cli] Using installed command: C:\Users\Zwh\AppData\Roaming\Python\Python312\Scripts\cli-anything-solidworks.EXE
collected 15 items

cli_anything/solidworks/tests/test_core.py::test_session_new_schema PASSED
cli_anything/solidworks/tests/test_core.py::test_session_save_load PASSED
cli_anything/solidworks/tests/test_core.py::test_session_undo_redo PASSED
cli_anything/solidworks/tests/test_core.py::test_set_active_document_tracks_documents PASSED
cli_anything/solidworks/tests/test_core.py::test_preview_recipes_contains_active_bmp PASSED
cli_anything/solidworks/tests/test_core.py::test_preview_latest_missing PASSED
cli_anything/solidworks/tests/test_core.py::test_preview_capture_writes_bundle PASSED
cli_anything/solidworks/tests/test_core.py::test_extract_exe_from_quoted_command PASSED
cli_anything/solidworks/tests/test_core.py::test_doc_type_mapping PASSED
cli_anything/solidworks/tests/test_core.py::test_find_default_part_template_returns_string_or_none PASSED
cli_anything/solidworks/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/solidworks/tests/test_full_e2e.py::TestCLISubprocess::test_project_new_json PASSED
cli_anything/solidworks/tests/test_full_e2e.py::TestCLISubprocess::test_preview_recipes_json PASSED
cli_anything/solidworks/tests/test_full_e2e.py::TestRealSolidWorksBackend::test_doctor_real_backend PASSED
cli_anything/solidworks/tests/test_full_e2e.py::TestRealSolidWorksBackend::test_box_save_and_preview_real_backend
  Preview BMP: C:\Users\Zwh\AppData\Local\Temp\pytest-of-Zwh\pytest-3\test_box_save_and_preview_real0\.cli-anything\previews\active-bmp\active-bmp-20260612T082445Z\artifacts\active.bmp (4,800,054 bytes)
PASSED

============================= 15 passed in 4.42s ==============================
```

Summary: 15 tests, 15 passed, 100% pass rate.

Coverage notes: the suite validates installed-command subprocess use, session behavior, preview-bundle metadata, and a real SOLIDWORKS COM workflow that creates a part, saves it, and captures a real BMP preview.
