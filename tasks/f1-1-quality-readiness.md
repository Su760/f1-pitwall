# F1.1 — quality-gate repair and evidence reconciliation

Authorized 2026-10-16: implement, verify, document, commit/push, and inspect CI.
No F2, model fitting, RL, source replacement, or relaxed completeness thresholds.
Preserve unrelated `web/next-env.d.ts` and the untracked downloaded spec.

Scope: `src/pitwall_historical/{quality.py,__init__.py}`,
`historical/tests/test_quality.py`, `docs/data-contract.md`,
`docs/reports/f1-1-readiness-review.md`, `docs/{status,decisions}.md`,
`tasks/{todo,lessons,f1-1-quality-readiness}.md`; ignored local evidence/builds only.
The approved specification and synthetic arena remain unchanged.

- [x] Read instructions/contracts and inspect Git; reproduce baseline and defect.
- [x] Add failing regressions; repair purpose-specific stint readiness and version it.
- [x] Reconcile targeted FIA 2023 pit, 2024 control baseline, 2025 car 27 evidence.
- [x] Run focused/full relevant checks; rebuild twice and compare artifacts.
- [x] Obtain independent read-only review; resolve substantive scoped findings.
- [ ] Finish report/status/decisions, inspect staged files, commit/push and check CI.

Diagnosis at baseline c503441: `quality.py:282` detects a missing stint endpoint;
`quality.py:525` only propagates selected start-boundary flags to actual laps;
`quality.py:745–775` computes readiness without the stint audit. Thus the supplied
four-lap classified finisher / stint 1–5 fixture has ready 4/4 and a passed gate.
Fix structural readiness separately from row eligibility, preserving valid laps
and completed-stint bounds for retirement tails. Pit duration purposes stay separate.

Before edits, offline rebuild `historical-data/f1-1-baseline` reproduced all 12
files in `historical-data/f1-final-a` byte-for-byte. Exit 2 / partial is expected:
the original 2023 OpenF1 pit HTTP 404 remains evidence, not successful empty data.
Latest manifest SHA-256:
`22b92984adf14a904d3b3bfd924530dbcb903190a77f101c3280bd4ce6ffdc21`.

Local results: 37 quality, 102 historical, 305 combined core/historical and 250
core/API tests pass; Ruff and wheel packaging pass. Historical env lacks pip;
packaging succeeded in the existing API env. Synthetic comparison/optimization/
replay preserve prior outputs. New v2 builds `f1-1-a`/`f1-1-b` match all 12 files;
all nine normalized tables are unchanged from v1. Both exit 2 / partial.
Independent read-only code and final evidence/doc reviews passed, including
independent cache validation, PDF/HTML comparison and cohort count verification.
Full findings and the unimplemented 382-row cohort proposal are in
[the readiness review](../docs/reports/f1-1-readiness-review.md).
