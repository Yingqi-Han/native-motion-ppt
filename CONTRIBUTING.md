# Contributing

Python 3.10+ and Node.js 20+ are required. Install Python dependencies with `python -m pip install -r requirements.txt`.

Run from the repository root:

```bash
python -m unittest discover -s tests -v
node --test tests/test_timeline.mjs
python scripts/validate_skill.py
python scripts/package_skill.py --source-only --out dist
python scripts/verify_delivery.py dist
```

`scripts/` contains export, preview, playback and acceptance code. `assets/` contains the schema, shared timeline and Remotion template. `examples/` contains editable inputs. `references/` contains workflow and capability documentation. Generated files belong under `output/`; release archives belong under `dist/`.

Use meaningful behavioral regression tests for exporter or evidence changes. Preserve automatic, reviewed and final acceptance states. A change to the detector should be checked against the original recording in a new run; a change to the PPT requires new real playback evidence.

The unit/CI checks do not launch WPS. Changes affecting native playback require the full procedure in [acceptance.md](references/acceptance.md). Keep raw recordings and source/PPT hashes; do not relabel a different renderer as WPS.

The default package command without `--source-only` is the legacy multi-demo bundle builder and requires its generated `output/` trees. Use `--source-only` for normal skill distribution; use `accept_project.py` for a complete project delivery.
