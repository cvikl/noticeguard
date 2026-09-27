# NoticeGuard benchmark rubric (v0.1.0)

This is the document a human labels against. It defines the three verdicts and the reason codes used in every `expected.json`. The benchmark measures **consistency with this rubric**, not legal correctness.

## Verdicts

**evidence_ready** — every component of the statement the creator would make at the chosen step is supported by the documents:
- a licence or permission clause (of the version in force at purchase, or a dated grant from the licensor) covers the actual use (monetised or not, on the platform, on the creator's channel, for the holder's tier);
- the licence or grant was in force on the publish date (or on the date monetisation started, if the video was published unmonetised);
- the claimant is the licensor or an administrator the licensor names;
- the matched work is the licensed work;
- the chosen step is available at the current process stage.

**evidence_gap** — the step is available, nothing needs a person's judgement, but at least one component above is not supported (for example the licence tier excludes monetised use and there is no dated grant, or the grant is dated after publication). The gap must be closable by a specific document.

**needs_adviser** — a question the tool does not decide: the claimant cannot be connected to the licensor (possible ownership question); the matched work differs from the licensed work; the certificate version and the current terms differ and no clause says which version governs; a permitted-use or grant wording is ambiguous (the three mapping runs disagree); documents conflict with each other; the creator relies on fair use or disputes ownership; the chosen step is not available at the current stage.

Precedence: needs_adviser > evidence_gap > evidence_ready.

## Reason codes

| code | meaning |
|---|---|
| `licence_covers_use` | a permitted-use clause of the version in force covers the actual use (ready) |
| `grant_before_publish` | a dated licensor grant covers the use and predates publication (ready) |
| `tier_excludes_monetised` | the held tier's terms exclude monetised use and no grant exists (gap) |
| `grant_after_publish` | the only grant is dated after publication (gap) |
| `no_governing_clause` | certificate version differs from current terms and no governing-terms clause is present (adviser) |
| `unrelated_claimant` | the claimant is neither the licensor nor a named administrator (adviser) |
| `work_mismatch` | the matched work is not the licensed work (adviser) |
| `ambiguous_wording` | mapping runs disagree on a decisive clause (adviser) |
| `conflicting_documents` | two documents give incompatible values for the same fact (adviser) |
| `step_unavailable` | the chosen step is not available at the detected stage (adviser) |

## Labelling procedure

1. Read every document in `docs/`. 2. Determine the stage from the notices. 3. Walk the five bullets under *evidence_ready* in order; the first one that fails decides the verdict and reason code, applying the precedence rule. 4. Record the label in `expected.json` with `author` and `source` (`generated` or `handwritten`).
