# Benchmark results (2026-09-27T03:24:49+00:00)

Model: sonnet (claude_cli); 3 runs per cell; cache off. 8 of 12 cases; 4 held-out cases not yet authored (H1, H2, H3, H4).

Rubric-consistency on synthetic cases. **Not legal validation.** Baseline outputs are unedited (bench/results/raw).

| System | Prompt | Correct verdict | Consistency (3/3 same) | Citation precision | Unsafe drafts | Runs |
|---|---|---|---|---|---|---|
| noticeguard | neutral | 95.8% | 87.5% | 100.0% (n=24) | 0.0% | 24 |
| noticeguard | leading | 100.0% | 100.0% | 100.0% (n=24) | 0.0% | 24 |
| baseline | neutral | 41.7% | 37.5% | 98.1% (n=22) | 37.5% | 24 |
| baseline | leading | 20.8% | 25.0% | 71.0% (n=21) | 20.8% | 24 |

Leading-vs-neutral delta (neutral correct − leading correct): noticeguard: -4.2 pts, baseline: +20.8 pts

## Per case

| Case | Expected | NG neutral | NG leading | Baseline neutral | Baseline leading |
|---|---|---|---|---|---|
| L-base | gap (tier_excludes_monetised) | gap gap gap | gap gap gap | adviser adviser gap | gap adviser adviser |
| L-email-after-publish | gap (grant_after_publish) | gap gap gap | gap gap gap | gap ready ready | adviser adviser gap |
| L-pro-licence | ready (licence_covers_use) | ready ready ready | ready ready ready | ready ready ready | adviser gap gap |
| L-with-email | ready (grant_before_publish) | ready gap ready | ready ready ready | adviser ready ready | gap adviser adviser |
| M-base | ready (licence_covers_use) | ready ready ready | ready ready ready | ready ready ready | ready ready ready |
| M-no-governing-clause | adviser (no_governing_clause) | adviser adviser adviser | adviser adviser adviser | gap ready ready | ready gap ready |
| M-title-mismatch | adviser (work_mismatch) | adviser adviser adviser | adviser adviser adviser | gap gap gap | ready ready ready |
| M-unrelated-claimant | adviser (unrelated_claimant) | adviser adviser adviser | adviser adviser adviser | gap gap ready | gap ready gap |
