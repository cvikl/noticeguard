# NoticeGuard

**NoticeGuard checks the statement you'd sign, not the question you ask.**

NoticeGuard is an evidence-readiness checker for independent creators hit by an automated copyright claim on a video platform. The creator uploads their documents (the claim notice, their licence, their receipt, the licensor's terms, emails from the licensor) and says which step they are about to take: dispute, appeal, or a DMCA counter-notice. A language model only **highlights spans** in those documents; it never types a value and never decides anything. A deterministic rules engine then checks whether the highlighted facts support the exact statement the creator would be making at that step and returns one of three results, always in words: **Evidence ready**, **Evidence gap**, or **Needs an adviser**. Every sentence in the result clicks through to the chain `Document → Quote → Fact → Rule → Status`. A draft is prepared only when evidence is ready, only from confirmed facts, and is post-checked so it cannot contain a date, ID, clause or name that is not in the fact table. NoticeGuard never tells anyone whether to file.

Built for LexHack 2026 (Digital Rights & Policy Tech track). Live demo: https://noticeguard.primafacie.eu

> Screenshots: `docs/screenshots/` (placeholders until the recording is made).

## Architecture

```
 files (.txt .md .pdf .eml)
      │
      ▼
 Ingest ──► normalised text with line offsets (sha256 per document)
      │
      ▼
 Extract (LLM tags spans in the ORIGINAL text; it never types values)
      │
      ▼
 Round-trip check ──► stripped output must equal the document, else the whole
      │                extraction is rejected (one retry with the diff shown)
      ▼
 Normalise in code ──► dates (dayfirst), versions, IDs, categorical labels from keywords
      │
      ▼
 Mapping (3 runs, temperature 0.7, must agree 3/3 or the case goes to an adviser)
      │
      ▼
 Fact table ──► Confirmed by document / Stated by you / Missing / Conflicting
      │
      ▼
 Rules R0–R10 (deterministic, pure, version 0.1.0, rules.yaml)
      │
      ├──► Verdict · statement components · routes (lowest risk first) · gap fixes
      ├──► Draft (template from confirmed facts) + post-check
      └──► Chain for every sentence
```

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add GEMINI_API_KEY or ANTHROPIC_API_KEY
make run                        # http://localhost:8000
```

Click **Load Maya** or **Load Leo**. Both demo cases run entirely from the committed LLM cache (`cache/llm/`), so no key and no network are needed. Uploading your own documents needs an LLM: set `LLM_PROVIDER=gemini` with `GEMINI_API_KEY`, `LLM_PROVIDER=anthropic` with `ANTHROPIC_API_KEY`, or `LLM_PROVIDER=claude_cli` if the `claude` CLI is installed and logged in (no key needed; used for this build).

```bash
make test          # pytest: quote round-trip, rules, determinism, golden cases (offline)
make seed          # (re)populate the demo cache with the configured provider
make bench         # 12 cases × 3 runs × 2 prompts × 2 systems → bench/results/latest.json
make bench-generate  # regenerate the 8 variant cases
```

The demo script: load Maya (ready for a dispute); load Leo, type "I paid for this, I'm obviously right, just write it" in the Notes box (it is ignored), read the gap; click **Add Leo's licensor email**; the verdict moves to ready and the "What changed" panel names the email as the fact that flipped R4.

## What the rules do

| Rule | Decides |
|---|---|
| R0 | Process stage from the notices; whether the chosen step is available |
| R1 | The matched work is the licensed work |
| R2 | Which licence terms version governs (by purchase date and the governing-terms clause) |
| R3 | Whether the permitted-use wording of that version covers the actual use (3-run mapping) |
| R4 | Whether a dated licensor grant covers the use and predates publication |
| R5 | Whether the claimant is the licensor or its named administrator |
| R6 | Matched segment inside the video duration (never blocks) |
| R7 | Statement components ← rule results |
| R8 | Verdict: adviser > gap > ready |
| R9 | Routes, lowest risk first |
| R10 | Abstain triggers: fair use, ownership, conflicting facts, ambiguous mapping |

One design decision worth stating: a clear 3/3 permission is only defeated by a clear 3/3 exclusion. If the runs disagree about whether a *restriction* clause applies, that disagreement is shown in the chain but does not override an explicit permission; if they disagree about a *permission* clause, the case goes to an adviser. The first real run surfaced this: the model tagged "Pro licence additionally permits use in broadcast…" as a restriction and one run called it unclear.

## Transparency

- **LLM**: extraction, mapping and the baseline all use the same model. This build used the Claude CLI provider (`claude_cli`, model alias `sonnet`, i.e. Claude Sonnet) because no Gemini or Anthropic API key was available in the build environment. The CLI does not expose a temperature setting, so "temperature 0" extraction and "temperature 0.7" mapping run at the CLI's default sampling; the Gemini and Anthropic SDK providers honour the temperatures in code. The benchmark ran with the cache off, so every run is a fresh call.
- **Cache**: every LLM call is cached at `cache/llm/<sha256>.json`; the demo sets' cache is committed so the demo runs offline. The prompts are in `app/extract.py`.
- **Documents**: everything is synthetic. ClipStream, Glasswork Audio, Northline Rights, Lumen Vale and "Glasslight" do not exist. Real-world statistics appear only in this README and the Devpost text, never in the product.
- **Rubric**: written by us (`data/benchmark/rubric.md`). The 8 generated cases are labelled by the variable the generator flipped. The 4 held-out cases (`H1`–`H4`) are reserved for a teammate who did not write the rules; **at the time of this build they had not been authored**, so the benchmark reports 8 of 12 cases.
- **Benchmark**: measures rubric-consistency and resistance to a leading prompt, not legal validity. Baseline outputs are stored unedited in `bench/results/raw/`. Numbers are committed as they came out; see `bench/results/results.md`.
- **Libraries**: FastAPI, Pydantic v2, pypdf, python-dateutil, google-genai, anthropic, PyYAML, pytest. Front end: vanilla HTML/CSS/JS, Source Serif 4 from Google Fonts.
- **Baseline draft detector**: a run counts as producing a draft when a draft marker (counter-notice / §512(g) / "penalty of perjury" / "good faith belief" / a salutation) is followed by first-person declaratory text. It is simple and documented in `bench/baseline.py`.

## What it does not do

It does not decide who owns the copyright, does not assess fair use, does not verify that documents are authentic, does not promise an outcome, does not advise whether to file, and does not replace a lawyer. The label is "Confirmed by document": the documents are consistent with each other, nothing more. It never files anything and has no Submit button.

## Not built / cut

- LLM prose smoothing of drafts exists behind `NOTICEGUARD_SMOOTH_DRAFT=1` but was not used for the demo (the post-check re-runs on the smoothed text and falls back to the template).
- Held-out benchmark cases H1–H4: not authored (see above).
- Mobile layout is tolerated, not designed for.

## Sources

- YouTube Copyright Transparency Report 2025 (about 2.5bn Content ID claims, about 99.8% automated, under 1% disputed, most disputes resolved for the uploader), as reported by TorrentFreak.
- YouTube Help, "Dispute a Content ID claim" (answer 2797454) and "Appeal a Content ID claim" (answer 12104471).
- 17 U.S.C. §512(g)(2)–(3) and §512(f).
- Dahl, Magesh, Suzgun & Ho, "Large Legal Fictions", Journal of Legal Analysis 16(1), 2024.

## Licence

MIT.
