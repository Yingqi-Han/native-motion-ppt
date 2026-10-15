# Repository instructions

This repository is the portable Native Motion PPT skill. Read SKILL.md for the authoring workflow and references/acceptance.md for playback acceptance.

- Keep user inputs and historical recordings unchanged. New runs use new directories and SHA bindings.
- WPS evidence must come from actual WPS capture. Browser/Remotion previews and Impress recordings certify only their own backends.
- The tested player is the pinned international Linux WPS build. Do not generalize to Windows WPS or Microsoft PowerPoint.
- Keep player binaries, downloaded packages, private profiles, caches and credentials outside Git and release packages.
- docs/verification.md and showcase/ describe historical verified runs; changing source does not re-certify those recordings.
- Check changes with Python unittest, Node timeline tests and validate_skill.py as described in CONTRIBUTING.md. For packaging changes, also build and verify a source-only release.
- Keep VERSION and native_motion.__version__ consistent. Installable releases exclude Git metadata, CI configuration, dist/ and showcase/.
