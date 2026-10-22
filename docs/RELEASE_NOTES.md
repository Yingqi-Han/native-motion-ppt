Native Motion PPT v1.8.0 adds an inspectable workflow for existing presentations: `nmp.py plan` creates source-bound groups, an object inventory and a layout review. Review actual slides, edit groups, then apply `enhance`. Titles/context stay visible, native groups remain atomic, and existing animated slides are preserved.

Enhancement now copies unrelated ZIP members directly and changes only target slide timing. It verifies canonical non-timing XML plus original images, relationships, notes and unknown members. Stale plans and invalid object IDs are rejected before writing; originals and existing outputs are preserved.

`nmp.py diagnose` explains raw failed/pending states without changing them. It distinguishes unsupported coverage, missing observations, capture issues, measured changes and evidence-binding problems. Actual issue times and page-context ranges have different labels. The local report server supports a confined `--entry` path; generated serving argv helps standalone diagnoses retain video seeking.

Real Linux WPS evidence covers the simulated existing-PPT workflow, an unchanged-recording normal regression and independent boundary recordings. The existing deck passes four new reveals, one preserved click and six context probes. The normal regression remains 22/22 passed. The boundary deck retains five pending checks for text Morph/rotation coverage; it is not advertised as fully passed. Partial page calibration now yields labelled review-context frames instead of an extraction crash.

139 Python and 11 Node regressions, isolated core-only CLI tests and source-package installation checks accompany the release. Full evidence includes original failed reports and corrected checks using identical recordings; static thresholds were not widened. See docs/verification.md for exact scope and hashes.

The tested desktop backend is pinned international Linux WPS 11.1.0.11723.XA. Windows core CLI CI is separate; Windows WPS and Microsoft PowerPoint remain untested. Repository-authored examples use simulated content. Remotion/browser previews keep separate provenance.
