# Contributing

Python 3.10+ is required. Native export/preview generation use requirements-core.txt; the full development and playback workflow uses requirements.txt plus Node.js 20+, browser, Office and desktop tools.

Run from the repository root:

```bash
python -m unittest discover -s tests -v
node --test tests/test_timeline.mjs
python tests/smoke_core_cli.py --isolated
python scripts/validate_skill.py
python scripts/package_skill.py --source-only --out dist
python scripts/verify_delivery.py dist
```

`scripts/` contains export, preview, playback and acceptance code. `assets/` contains the schema, shared timeline and Remotion template. `examples/` contains editable inputs. `references/` contains workflow and capability documentation. Generated files belong under `output/`; release archives belong under `dist/`.

Use meaningful behavioral regression tests for exporter or evidence changes. Preserve automatic, reviewed and final acceptance states. A change to the detector should be checked against the original recording in a new run; a change to the PPT requires new real playback evidence.

The unit/CI checks do not launch WPS. Changes affecting native playback require the full procedure in [acceptance.md](references/acceptance.md). Keep raw recordings and source/PPT hashes; do not relabel a different renderer as WPS.

The isolated smoke installs only requirements-core.txt into a clean venv and tests the actual public CLI. It must not rely on NumPy, PyMuPDF, Playwright, a browser or Office. CI runs it on Linux and Windows; this establishes portable core behavior only, not Windows WPS or PowerPoint playback.

The default package command without `--source-only` is the legacy multi-demo bundle builder and requires its generated `output/` trees. Use `--source-only` for normal skill distribution; use `accept_project.py` for a complete project delivery.
