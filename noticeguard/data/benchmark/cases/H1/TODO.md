# H1 — held-out case (to be written by a teammate who did not write the rules)

This folder is reserved for a hand-written benchmark case. It must be authored by someone who has **not** read or written `app/rules/engine.py`, using only `data/benchmark/rubric.md` and the synthetic world in `data/synthetic/` (ClipStream, Glasswork Audio, Northline Rights, "Glasslight").

To complete it:
1. Put 4–8 plain-text documents in `docs/` (claim/removal notices, receipt, certificate, terms, track page, video export, optional licensor email). Name them so the type is obvious (e.g. `01_claim_notice.txt`).
2. Write `expected.json`:
   `{"case_id": "H1", "step": "dispute|appeal|counter_notice", "expected_verdict": "evidence_ready|evidence_gap|needs_adviser", "expected_reason_code": "<code from rubric.md>", "source": "handwritten", "author": "<name>"}`
3. Delete this TODO.md and commit before `make bench` is run for the video.

If this file is still here at bench time, the runner reports "8 of 12 cases; 4 held-out cases not yet authored" and runs on the 8 generated cases only.
