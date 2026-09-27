# NoticeGuard — Build Prompt for Claude Code

You are building **NoticeGuard**, a hackathon demo for LexHack 2026 (Devpost). Hard deadline: **today, Sunday 27 Sept 2026, 22:00 UK time**. Everything below is scoped for one build session. Work in the priority order given in section 12 and stop at the cut lines when time runs out. Do not gold-plate. Do not fake any result. If something can't be made real in time, leave it out and say so in the README.

---

## 0. One-paragraph summary of what this is

NoticeGuard is an **evidence-readiness checker** for independent creators hit by an automated copyright claim on a video platform. The creator uploads their documents (the claim notice, their licence, their receipt, any emails from the licensor) and tells the tool which step they're about to take (dispute, appeal, or a DMCA counter-notice). An LLM **only extracts facts**, and every fact must carry a verbatim quote from a source document, or it is rejected. A **deterministic rules engine** then checks whether those facts support the exact statement the creator would be making at that step, and returns one of three results: **Evidence ready**, **Evidence gap**, or **Needs an adviser**. Every sentence in the result clicks through to the chain `Document → Quote → Fact → Rule → Status`. A draft (dispute text or counter-notice) is generated only when evidence is ready, only from confirmed facts, and is post-checked so it can't contain any date, ID or clause that isn't in the confirmed fact table. The tool **never tells anyone whether to file**; it reports whether the paperwork backs the step.

The pitch line: **"NoticeGuard checks the statement you'd sign, not the question you ask."**

The demo contrast: a general chatbot given the same documents and the prompt "I paid for this track, write my counter-notice" will usually just write it. NoticeGuard gives the same answer to a leading question as to a neutral one.

---

## 1. Non-negotiables (read twice)

1. **The LLM never decides anything.** It extracts structured facts with quotes. Rules code makes every decision. If you find yourself letting the model output a verdict, stop.
2. **Every fact carries a verbatim quote and a source document ID.** A quote that cannot be found in the document text (after whitespace normalisation) causes the fact to be dropped. Log dropped facts.
3. **Deterministic.** Same documents + same step → same result, every run. Rules must be pure functions over the fact table. No randomness outside the extraction layer, and the extraction layer is cached by document hash.
4. **Leading-question resistance.** The creator's free-text framing must not reach the rules engine at all. The only user inputs the rules see are: documents, chosen step, and a small set of structured "stated by you" fields (e.g. "my video was monetised: yes/no"). Anything the user types in free text is ignored by the decision path.
5. **Three outcomes only:** `evidence_ready`, `evidence_gap`, `needs_adviser`. Always shown in words, never by colour alone.
6. **Labels are "Confirmed by document", never "Verified".** We check documents are consistent with each other, not that they are authentic. Say this in the UI footer.
7. **Never advise filing.** UI copy says "your evidence is ready for X" and "here is a draft prepared for your review", not "you should file".
8. **Abstain is a feature.** Fair use arguments, ownership questions, unrelated claimants, conflicting documents, or extraction disagreement → `needs_adviser`. Do not guess.
9. **No faked demo outputs.** The benchmark numbers are whatever they are. The baseline chatbot output is shown unedited. If the baseline does well, we show that too.
10. **Synthetic everything.** Platform is fictional ("ClipStream"), licensor is fictional ("Glasswork Audio"), claimant is fictional ("Northline Rights"), track is fictional ("Glasslight"). Never use a real platform name inside the product. Real-world stats are cited only in the README/Devpost.

---

## 2. Domain background you need to get the rules right

### 2.1 The platform process (ClipStream, modelled on YouTube's published process)

Stages, in order. A creator can only be at one stage at a time:

1. **claim** — an automated content-match claim is placed on the video. Not a strike. Typical effect: monetisation redirected to claimant, or video blocked in some regions, or tracking only.
2. **dispute** — creator disputes the claim in-platform. Claimant has **30 days** to respond: release the claim, or reject the dispute (claim reinstated), or let it expire.
3. **appeal** — after a rejected dispute, creator can appeal. Claimant has **7 days**. If claimant rejects the appeal they must file a **copyright removal request** to keep the claim.
4. **removed_with_strike** — claimant filed a removal request. Video is taken down and the channel gets a **copyright strike**. **Three strikes within 90 days can terminate the channel.** A single strike expires after 90 days (and after completing platform "copyright school"), or can be cleared if the claimant retracts.
5. **counter_notice** — only available after removal. This is the legal step under US DMCA **17 U.S.C. §512(g)**. After a counter-notice the claimant has **10 US business days** to show they have filed a lawsuit; if not, the platform restores the video.

Important nuance: the claimant can file a removal request **at any point** during dispute or appeal, not only at the end. The status strip must warn about this at the dispute and appeal stages.

### 2.2 What the creator is actually asserting at each step

This is the core of the product. Each step has a statement with components, and each component maps to facts that must be confirmed.

**Dispute (reason: "I have a licence")** — platform-level statement, not sworn:
- S-D1: "I have a licence or permission from the copyright owner or their authorised representative that covers this use of the content in this video."
- S-D2: "The licence was in force when the video was published."
- S-D3: "The claimant is the owner or their representative for this content" (i.e., the claim is a licensed-use conflict, not a mismatch or an unrelated party).

**Appeal** — same as dispute, plus the user must acknowledge (structured checkbox, not a fact) that a rejected appeal can lead to a removal request and strike. Evidence requirement is the same as dispute, but the UI shows the higher risk.

**Counter-notice (17 U.S.C. §512(g)(3))** — sworn, legal. Required elements:
- CN1: Identification of the material removed and where it appeared before removal.
- CN2: **"A statement under penalty of perjury that the subscriber has a good faith belief that the material was removed or disabled as a result of mistake or misidentification of the material."** ← this is the sentence the evidence check targets.
- CN3: Creator's name, address, telephone number.
- CN4: Consent to jurisdiction of the US Federal District Court for the district of the creator's address, or (if outside the US) any judicial district in which the platform may be found; and agreement to accept service of process from the claimant or their agent.
- CN5: Physical or electronic signature.

Consequence to display: **17 U.S.C. §512(f)** — knowingly materially misrepresenting that material was removed by mistake creates liability for damages, costs and attorney's fees.

For NoticeGuard, CN2 is "supported" only if the facts show: a licence/permission (a) from the licensor or a party in the licensor's chain, (b) whose permitted use covers the actual use (monetised / non-monetised, platform, channel), (c) in force on the publish date (correct version, or a dated grant before the publish date), (d) for the same work that was matched. CN1 and CN3 are filled from the claim notice and the creator's structured profile fields (label: Stated by you). CN4 and CN5 are acknowledgements the creator makes in the UI, not facts.

### 2.3 The licence-version problem (this is Maya's case)

Licensors change their terms. A creator who bought under v2 may look at the licensor's website today, see v3, and wrongly conclude they are not covered. The rule: the licence version in force is the one attached to the purchase, and a "governing terms" clause in the current terms usually says so ("your licence is governed by the terms in force on the date of purchase"). NoticeGuard must resolve which version applies **by purchase date**, and cite both the old permission clause and the governing-terms clause.

### 2.4 Content-ID administrators (part of Maya's case)

Licensors frequently hand the matching/claiming of their catalogue to a rights administrator. So the claimant name on a claim notice ("Northline Rights") may differ from the licensor ("Glasswork Audio") and still be legitimate. If the licensor's track page lists the claimant as administrator, the claim is a **licensed-use conflict** — inside the chain — and the dispute route is appropriate. If the claimant is unrelated to the licensor, that's potentially an ownership question → `needs_adviser`.

### 2.5 Least-risky route

Before any dispute or counter-notice, the cheapest fix is often: ask the licensor to have its administrator release the claim, or ask the claimant to retract the removal request (which also clears the strike). NoticeGuard always lists the lowest-risk route first and marks what the evidence is ready for.

---

## 3. Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLite via `sqlite3` or SQLModel (keep it thin). `uvicorn` for serving.
- **Frontend:** single-page app served by FastAPI as static files. Plain HTML + vanilla JS + Tailwind via CDN. No build step. (If you strongly prefer, Vite + React is acceptable, but only if `npm run build` output is committed so the demo runs with `uvicorn` alone.)
- **LLM:** provider-agnostic module `llm.py` with two implementations selected by env var `LLM_PROVIDER`: `gemini` (default; `google-genai` SDK, model from `LLM_MODEL`, default `gemini-2.5-flash`) and `anthropic` (`anthropic` SDK, model from `LLM_MODEL`). Both must support JSON-schema-constrained output or robust JSON parsing with a retry. Temperature 0 for extraction; for the "mapping" step run 3 calls at temperature 0.7 (see §5.4).
- **Caching:** every LLM call is cached to `cache/llm/<sha256 of (provider, model, prompt, docs)>.json`. Cached results are committed to the repo for the demo document sets so the demo runs offline / without a key. Add `--no-cache` flag for the benchmark.
- **PDF/text input:** accept `.txt`, `.md`, `.pdf` (use `pypdf` for text extraction), `.eml` (parse with stdlib `email`). Everything is normalised to plain text with line numbers for quoting.
- **Testing:** `pytest`. Rules engine must have unit tests. The two demo cases (Maya, Leo before email, Leo after email) are the golden tests.
- **Repo:** `noticeguard/` at root, `README.md`, `DEVPOST.md`, `LICENSE` (MIT), `.env.example`, `Makefile` or `justfile` with `run`, `test`, `bench`, `seed`.

Environment file `.env.example`:
```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
NOTICEGUARD_CACHE=1
```

---

## 4. Repository layout

```
noticeguard/
  app/
    main.py              # FastAPI app, routes, static serving
    models.py            # Pydantic models: Document, Fact, Rule result, CaseResult, etc.
    ingest.py            # file → normalised text with line offsets
    extract.py           # LLM extraction with quote-grounding + agreement check
    quote_match.py       # verbatim quote verification
    rules/
      __init__.py
      engine.py          # run_rules(facts, step, stated) → CaseResult
      rules.yaml         # declarative rule definitions (versioned)
      stages.py          # process-stage detection from notices
      routes.py          # least-risk route selection
    draft.py             # draft generator + post-check
    chain.py             # builds Document→Quote→Fact→Rule→Status chain for UI
    llm.py               # provider abstraction + cache
    store.py             # SQLite persistence of cases
  static/
    index.html
    app.js
    styles.css
  data/
    synthetic/
      maya/              # her document set
      leo/               # his document set (pre-email)
      leo_email/         # the 2 Sept support email, added live in the demo
      templates/         # base documents used by the variant generator
    benchmark/
      cases/             # 12 case folders, each with docs/ + expected.json
      rubric.md
      generate_variants.py
  bench/
    run_benchmark.py     # 12 cases × 3 runs × 2 prompts × 2 systems
    baseline.py          # plain-LLM baseline runner
    results/             # JSON + a results.md summary, committed
  tests/
    test_rules.py
    test_quote_match.py
    test_golden_cases.py
  cache/llm/             # committed cache for demo docs
  README.md
  DEVPOST.md
  .env.example
  requirements.txt
```

---

## 5. Pipeline in detail

### 5.1 Ingest (`ingest.py`)

- Input: list of uploaded files + a `doc_type` hint per file chosen by the user from: `claim_notice`, `dispute_response`, `appeal_response`, `removal_notice`, `strike_notice`, `receipt`, `licence_certificate`, `licensor_terms`, `track_page`, `licensor_email`, `video_metadata`, `other`.
- Output: `Document{ id, filename, doc_type, text, lines: list[str], sha256 }`.
- Normalise: unify line endings, collapse runs of spaces, keep line breaks. Store the normalised text; quotes are matched against it.

### 5.2 Extraction schema (`extract.py`)

One extraction call per document. The prompt tells the model: "You are extracting facts from a single document. For each fact you must include the exact verbatim quote from the document that supports it. If you cannot quote it, do not output the fact. Output JSON only."

Extracted fact types (each is `{ type, value, quote, doc_id, confidence_note }`), pick per doc_type:

From **claim_notice / removal_notice / strike_notice / dispute_response / appeal_response**:
- `platform_case_id`, `claimant_name`, `matched_work_title`, `matched_segment` (e.g. "0:12–1:04"), `video_id`, `video_title`, `claim_date`, `claim_effect` (monetised_to_claimant | blocked | tracked), `notice_kind` (claim | dispute_rejected | appeal_rejected | removal | strike), `deadline_date` (if the notice states one), `strike_count`, `strike_date`, `claimant_contact`.

From **receipt**:
- `purchase_date`, `order_id`, `purchased_work_title`, `licence_tier` (e.g. "Standard"), `licence_version_on_receipt` (if shown), `licensor_name`, `buyer_name`.

From **licence_certificate**:
- `licence_version`, `licence_tier`, `licensed_work_title`, `licensee_name`, `issue_date`, `permitted_uses[]` (each a separate fact: e.g. "monetised video on social platforms"), `excluded_uses[]`, `governing_terms_clause` (quote), `clause_ref` for each (e.g. "4.1").

From **licensor_terms** (current terms):
- `terms_version`, `effective_date`, `permitted_uses[]`, `excluded_uses[]`, `governing_terms_clause` (e.g. "your licence is governed by the terms in force on the date of purchase"), `administrator_clause` (if terms name a rights administrator).

From **track_page**:
- `work_title`, `licensor_name`, `content_id_administrator_name`, `page_date_or_version`.

From **licensor_email**:
- `email_date`, `sender_domain`, `grant_statement` (quote: e.g. "you're cleared to use Glasslight in monetised ClipStream videos on your channel"), `granted_work_title`, `granted_use_scope`, `granted_channel_or_video`.

From **video_metadata** (a JSON/txt export of channel data):
- `video_id`, `publish_date`, `monetised_on_publish` (bool), `monetisation_start_date`, `channel_name`, `platform_name`.

Rules for extraction output:
- Dates in ISO `YYYY-MM-DD`. If the document has a date in another format, the quote is the original string and the value is the ISO conversion.
- The `quote` must be ≤ 300 characters and must be a contiguous substring of the document.
- Include `clause_ref` when the document has numbered clauses.

### 5.3 Quote-match check (`quote_match.py`)

`verify_quote(doc: Document, quote: str) -> Optional[Span]`:
- Normalise both sides: collapse whitespace, unify quotes/dashes (`’`→`'`, `“”`→`"`, `–—`→`-`), case-sensitive.
- Exact substring match first. If it fails, try a fuzzy fallback with `difflib.SequenceMatcher` ratio ≥ 0.95 over a sliding window of the same length. If still no match → fact is **rejected**, logged to `case.rejected_facts` with the reason, and shown in a collapsible "Rejected extractions" panel in the UI (this is a demo talking point).
- Return the line number(s) and char span so the UI can highlight.

### 5.4 Category mapping with agreement (`extract.py`, second stage)

Some facts need interpretation to become rule inputs, e.g. does "monetised video on social platforms" cover "monetised video on a ClipStream channel"? Does "personal, non-commercial projects" exclude monetisation?

For each mapping question, run the LLM **3 times** at temperature 0.7 with the same prompt: "Given this permitted-use clause (quoted), does it cover this actual use (structured)? Answer JSON: {covers: yes|no|unclear, reason}". Decision rule:
- 3/3 agree yes → mapped `covers=true`, label `confirmed_by_document` with the quote.
- 3/3 agree no → `covers=false`.
- Any disagreement or any `unclear` → mapping = `ambiguous` → rules engine outputs `needs_adviser` with reason "Permitted-use wording is ambiguous for your actual use; a person should read clause X."

Mapping questions to implement (only these):
1. `permitted_use_covers_actual_use` — per permitted_uses clause vs the actual use tuple `(monetised: bool, platform: str, medium: "video")`.
2. `grant_covers_actual_use` — for licensor_email grant statements, same tuple.
3. `governing_terms_selects_purchase_version` — does the governing-terms clause say the version at purchase applies? (yes/no/unclear)

Store all 3 raw answers; the chain view shows them.

### 5.5 Fact table

After extraction + quote match + mapping, build a `FactTable`: `dict[fact_key -> Fact]` where each Fact has `status ∈ {confirmed_by_document, stated_by_you, missing, conflicting}`.

- `confirmed_by_document`: at least one quote-verified extraction supports it.
- `stated_by_you`: came from the creator's structured form (name, address, phone, "video monetised?", "channel name"). Never from free text.
- `missing`: required by the step but no document supports it.
- `conflicting`: two documents give incompatible values (e.g. receipt says work "Glasslight", licence certificate says "Glassline") — or extraction runs disagree.

Conflict detection: for keys that can come from multiple documents (`work_title`, `purchase_date`, `licence_version`, `publish_date`), compare values; date mismatch > 0 days or title mismatch (normalised, ratio < 0.9) → `conflicting`.

### 5.6 Rules engine (`rules/engine.py` + `rules.yaml`)

Declarative and versioned. `rules.yaml` header: `version: "0.1.0"`. Each rule has `id`, `name`, `inputs`, `logic` (a named Python function in `engine.py`), `on_pass`, `on_fail`, `on_unknown`, `explanation_template`. Engine runs rules in order, collects a `RuleResult{ rule_id, status: pass|fail|unknown|not_applicable, facts_used[], explanation }`.

Rules to implement:

| ID | Name | Logic |
|---|---|---|
| R0 | Stage detection | From notice_kind facts and their dates, determine `current_stage ∈ {claim, dispute, appeal, removed_with_strike}` and the set of `available_steps`. Dispute available only at `claim`; appeal only after `dispute_rejected`; counter-notice only at `removed_with_strike`. If the chosen step isn't available → result is `needs_adviser` with explanation "this step isn't available at your current stage; the next available step is X". |
| R1 | Work identity | `matched_work_title` (from claim) must equal `licensed_work_title` (from certificate / receipt / email) after normalisation. Mismatch → `needs_adviser` ("the claim is for a different work than your licence covers"). |
| R2 | Licence version in force | Determine the version in force on `purchase_date`. Sources in priority: `licence_version` on certificate → `licence_version_on_receipt` → infer from `terms_version` + `effective_date` ranges. If the current terms have `governing_terms_selects_purchase_version = yes` and the certificate version ≠ current version, the certificate version governs; cite both quotes. If governing clause is `unclear` → `unknown`. |
| R3 | Permitted use covers actual use | Using the version from R2, check `permitted_use_covers_actual_use` for the actual use (monetised flag from `video_metadata` if present, else `stated_by_you`). Any `excluded_uses` matching the actual use → fail. Ambiguous → `unknown`. |
| R4 | Permission date vs publish date | If R3 fails but a `licensor_email` grant exists: `email_date` ≤ `publish_date` (or ≤ `monetisation_start_date` if the video was published unmonetised and monetised later) and `grant_covers_actual_use = yes` and `granted_work_title` matches → R4 pass overrides R3 fail. Email dated **after** publish date → fail with explanation "this permission is dated after you published; it may help going forward but does not show the use was licensed when the claim arose". |
| R5 | Claimant in licence chain | `claimant_name` equals `licensor_name`, OR equals `content_id_administrator_name` from track_page / terms → pass (classify as `licensed_use_conflict`). Otherwise → `unknown` → `needs_adviser` ("we can't connect the claimant to your licensor; this may be an ownership question"). |
| R6 | Matched segment plausibility | Optional. If `matched_segment` exists and video_metadata has duration, check segment within duration. Skip if missing. Never blocks. |
| R7 | Step evidence requirements | For the chosen step, list the statement components (§2.2). Map each to the rule results: S-D1/CN2-a ← R3 or R4; S-D2/CN2-c ← R2 and R4 date logic; S-D3/CN2-b ← R5; CN2-d ← R1; CN1 ← claim notice facts present; CN3 ← stated_by_you fields present. Each component gets `supported | not_supported | unknown`. |
| R8 | Verdict | All components `supported` → `evidence_ready`. Any `unknown`, any `conflicting` fact used, or any `needs_adviser` trigger → `needs_adviser`. Otherwise (≥1 `not_supported`, none unknown) → `evidence_gap`. Gap explanation lists exactly which component failed, which fact is missing, and **what document would close it** (see §5.8). |
| R9 | Route selection | `routes.py`: ordered list. If claimant in chain and stage ≤ appeal → route 1 "Ask the licensor to have its administrator release the claim", route 2 "In-platform dispute/appeal". If stage = removed_with_strike → route 1 "Send your evidence to the claimant and ask them to retract the removal request (this also clears the strike)", route 2 "Counter-notice". For each route, mark `evidence_status` using R7 with that route's requirements. Always list lowest-risk first. |
| R10 | Abstain triggers | Hard-coded: user ticks "I'm relying on fair use / parody / commentary" → `needs_adviser`. User ticks "I created this work myself and the claimant is wrong about ownership" → `needs_adviser`. Any `conflicting` fact → `needs_adviser`. Any mapping `ambiguous` → `needs_adviser`. |

Every RuleResult explanation is plain English, ≤ 2 sentences, and names the clause/date it used.

### 5.7 Draft generator + post-check (`draft.py`)

Only runs when verdict = `evidence_ready` for the chosen route/step.

- **Dispute draft** (platform-level): 4–7 sentences. Template with slots; each slot is filled from the confirmed fact table only. Every sentence ends with a citation marker like `[cert v2 §4.1]`, `[receipt #GA-2025-03112]`, `[terms v3 §9]`, `[email 2025-09-02]`.
- **Counter-notice draft**: the §512(g)(3) structure, with CN1/CN3 filled from facts / stated-by-you, CN2 as the verbatim statutory sentence, CN4 and CN5 as bracketed placeholders `[creator to confirm]` / `[signature]`. Header line: "DRAFT — prepared for your review. NoticeGuard has checked that your documents support the factual statements below. It has not verified their authenticity and is not legal advice."
- **Post-check**: extract every date, ID-like token (regex `[A-Z]{2,}-\d{4}-\d+` etc.), clause reference and proper noun from the draft; each must appear in the confirmed fact table or the stated-by-you fields. Any token that isn't → the draft is rejected and the UI shows "Draft withheld: it contained an unsupported detail: X". Log it. (In practice with a template this should never fire; it exists so we can show the guard in the chain view.)
- Optionally use the LLM to smooth the template prose, **then run the post-check on the smoothed text**. If the smoothed text fails post-check, fall back to the raw template. Default: template only, LLM smoothing behind a flag.

### 5.8 "What would close this gap"

For each `not_supported` component, emit a `GapFix{ component, needed: str, example_document_types: [..], how_to_get: str }`. Table:

- R3 fails, no grant email: "Any document from the licensor, dated on or before your publish date, that grants monetised use of this track on your channel." Doc types: `licensor_email`, `licence_certificate` (higher tier). How: "Check your inbox for support replies from the licensor before the publish date; check your account page for an upgraded licence."
- R4 fails on date: "A grant dated on or before <publish_date>." + "Alternatively: remove or replace the track, or ask the claimant to retract."
- R5 unknown: "The licensor's track page or terms naming <claimant> as its administrator, or an email from the licensor confirming <claimant> administers this track."
- CN3 missing: "Fill in your name, postal address and phone number in the form (these are required by the counter-notice format)."

### 5.9 Chain (`chain.py`)

For every sentence in the result screen and the draft, build:
```
ChainNode {
  sentence_id,
  text,
  rule_id, rule_name, rule_status,
  facts: [ { fact_key, value, status, quote, doc_id, doc_filename, line_start, line_end, clause_ref } ],
  mapping_runs: [ ...raw 3 answers if a mapping was involved ]
}
```
The UI renders this as a side panel when the sentence is clicked.

---

## 6. Synthetic document sets (write these in full — extraction needs real text to quote)

Write these as realistic plain-text documents (`.txt` or `.eml`), 150–600 words each, with numbered clauses where noted. Use the exact strings below where given because the golden tests assert on them.

### 6.1 Shared fictional world
- Platform: **ClipStream** (video platform). Process copy mirrors §2.1.
- Licensor: **Glasswork Audio** (`glasswork.audio`). Sells "Standard" and "Pro" licences. Issues a **Licence Certificate** with every purchase.
- Track: **"Glasslight"** by artist **Lumen Vale**. Catalogue ID `GA-TRK-0412`.
- Rights administrator: **Northline Rights** — listed on Glasswork's track page as "Content matching and claims for this track are administered by Northline Rights on behalf of Glasswork Audio."
- Licence terms versions:
  - **v2** (effective 2024-06-01 to 2025-05-31). Clause **4.1**: "Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee." Clause 4.3: "The licence does not permit redistribution of the Work as a standalone audio file."
  - **v3** (effective 2025-06-01). Clause **4.1**: "Standard licence permits use of the Work as background music in personal, non-commercial video content. Monetised use requires a Pro licence." Clause **9**: "Your licence is governed by the terms in force on the date of purchase. Later changes to these terms do not reduce rights already granted under an earlier version." Clause 10: "Content matching claims on platforms may be administered by a third-party rights administrator acting on our behalf."

### 6.2 Maya's set (`data/synthetic/maya/`)
- `01_claim_notice.txt` — ClipStream claim, case `CS-CLM-88213`, video `vid_7Kq2x` "Studio Vlog #12 — inking the dragon", claimant **Northline Rights**, matched work "Glasslight — Lumen Vale", segment 0:14–2:31, effect: "Ad revenue for this video is being directed to the claimant", date 2025-09-20, states "This is not a copyright strike." Lists options: dispute (claimant has 30 days), or leave the claim.
- `02_receipt.txt` — Glasswork Audio order `GA-2025-03112`, date **12 March 2025**, item "Glasslight — Standard licence", buyer Maya Ortiz, "Your Licence Certificate is attached to this email."
- `03_licence_certificate_v2.txt` — Certificate, "Licence Terms version 2", issued 12 March 2025, licensee Maya Ortiz, work Glasslight (GA-TRK-0412), tier Standard, includes clause 4.1 and 4.3 text verbatim from §6.1, and a line "This certificate is governed by Licence Terms v2 as in force on the date of issue."
- `04_licensor_terms_v3_current.txt` — current terms page, "Version 3, effective 1 June 2025", clauses 4.1, 9, 10 verbatim.
- `05_track_page.txt` — Glasswork track page for Glasslight, including the Northline administrator line verbatim.
- `06_video_metadata.txt` — ClipStream Studio export: video `vid_7Kq2x`, published **2025-08-30**, monetisation ON at publish, channel "Maya Draws", duration 11:48.

Expected: R0 stage=claim; R2 version v2 governs (cite cert + v3 §9); R3 covers (mapping should be 3/3 yes on "monetised video on social platforms" vs monetised ClipStream channel — if it isn't, that's a real finding, report it); R5 claimant in chain via track page; verdict **evidence_ready** for dispute; routes: (1) ask Glasswork to have Northline release, (2) dispute — ready. Status strip warns a dispute may lead to a removal request; shows counter-notice would also be supported by these docs.

### 6.3 Leo's set (`data/synthetic/leo/`)
- `01_claim_notice.txt` — case `CS-CLM-91077`, video `vid_3Pm9d` "Late-night synth session — full set", claimant Northline Rights, work Glasslight, segment 0:00–4:12, date 2025-09-12.
- `02_dispute_rejected.txt` — ClipStream notice, 2025-09-16: "The claimant has reviewed your dispute and reinstated their claim. You may appeal."
- `03_appeal_rejected_removal.txt` — 2025-09-22: "The claimant rejected your appeal and submitted a copyright removal request. Your video has been removed. Your channel has received a copyright strike (1 of 3). Three strikes within 90 days will result in channel termination. If you believe this removal was a mistake, you may submit a counter notification. Counter notifications are a legal process." Includes claimant contact `claims@northlinerights.example`.
- `04_receipt.txt` — order `GA-2025-08231`, date **19 August 2025**, "Glasslight — Standard licence", buyer Leo Marsh.
- `05_licence_certificate_v3.txt` — "Licence Terms version 3", issued 19 Aug 2025, licensee Leo Marsh, Standard, clause 4.1 v3 verbatim ("personal, non-commercial… Monetised use requires a Pro licence.").
- `06_licensor_terms_v3_current.txt` — same as Maya's 04.
- `07_track_page.txt` — same as Maya's 05.
- `08_video_metadata.txt` — video `vid_3Pm9d`, published **2025-09-10**, monetisation ON at publish, channel "Leo Marsh Music".

`data/synthetic/leo_email/09_licensor_support_email.eml` — From `support@glasswork.audio`, To `leo@…`, Date **Tue, 2 Sep 2025 10:14:00 +0100**, Subject "Re: Using Glasslight on my monetised channel", body contains verbatim: **"We've extended your licence: you're cleared to use Glasslight in monetised ClipStream videos on your channel Leo Marsh Music."** and a ticket ref `GW-SUP-55120`.

Expected before email: stage=removed_with_strike; R3 fails (v3 excludes monetised); no R4 grant; verdict **evidence_gap** for counter-notice; gap fix = "document dated on or before 2025-09-10 granting monetised use". Expected after email: R4 pass (2025-09-02 ≤ 2025-09-10, grant covers use — mapping 3/3 yes expected), verdict **evidence_ready**; routes: (1) send email to claimant, ask retraction (clears strike), (2) counter-notice — draft ready.

### 6.4 Statement text shown in the UI

Dispute: "I have a licence or permission from the copyright owner or their authorised representative to use this content in this video."

Counter-notice, quote in full: "I have a good faith belief that the material was removed or disabled as a result of mistake or misidentification of the material to be removed or disabled." Then the component breakdown: (a) I hold a licence or permission for this work — [supported/not]; (b) from the owner or their representative — [..]; (c) that was in force when I published — [..]; (d) for the same work that was matched — [..].

Below it, an "If you file this" box: "This is a sworn statement under penalty of perjury. You consent to the jurisdiction of a US federal court. The claimant then has 10 US business days to show they've filed a lawsuit before the video is restored. Knowingly false statements can create liability under 17 U.S.C. §512(f)."

---

## 7. Frontend spec (`static/`)

One page, three panels, mobile-tolerant but desktop-first (the demo is a screen recording at 1920×1080).

**Top: Process status strip.** Five nodes: Claim → Dispute → Appeal → Removal + strike → Counter-notice. Current stage highlighted with the word "You are here". Under each future node, one line of risk copy: under Dispute/Appeal "Claimant can respond with a removal request → strike"; under Counter-notice "Sworn statement; claimant may sue". Deadline countdown if a `deadline_date` fact exists (days remaining; never invent a deadline).

**Left column: Inputs.**
- Upload area (multi-file), per-file doc_type dropdown, "Analyse" button.
- Structured "About you" form: name, address, phone (for CN3), "Was the video monetised when published? yes/no/don't know", "Which step are you about to take?" radio: Dispute / Appeal / Counter-notice. Two abstain checkboxes: "I'm relying on fair use / commentary / parody", "I made this work myself and the claimant is wrong about ownership".
- A free-text box labelled "Notes (not used in the check)". This exists so the demo can show a leading question typed in and ignored. Show a tiny caption: "NoticeGuard reads your documents, not your question."

**Centre column: Result.**
1. **Verdict card**: one of three headings in words: "Evidence ready for: <route>", "Evidence gap", "Needs an adviser". One-paragraph plain-English explanation. Never colour-only; use an icon + word + colour.
2. **The claim in plain language**: who claimed, what work, what segment, what the platform did, when.
3. **The statement you would be making**: statement text in full, each component with a badge Supported / Not supported / Unknown, each clickable → chain panel.
4. **Evidence table**: rows = fact keys; columns = Value, Status (Confirmed by document / Stated by you / Missing / Conflicting), Source (doc name + clause/line). Confirmed rows show the quote on hover/expand. Key dates row group: purchase, licence version in force, publish, monetisation start, claim, removal.
5. **Routes**: ordered list, lowest-risk first, each with its own evidence status badge.
6. **What would close this gap** (only for `evidence_gap`): the GapFix items.
7. **Draft** (only for `evidence_ready`): the draft text, header line as in §5.7, each sentence clickable → chain. "Copy draft" button. Never a "Submit" button.
8. **Rejected extractions** (collapsed): facts the model produced without a valid quote.

**Right column: Chain panel.** Opens on any click. Shows Document → Quote (highlighted in the document text, scrolled to line) → Fact (key, value, status) → Rule (id, name, one-line logic) → Status. If a mapping was involved, show the three raw answers. A "Rules version 0.1.0" line at the bottom.

**Footer**, always visible: "NoticeGuard reports whether your documents are consistent with the step you're considering. It does not verify document authenticity, does not decide ownership or fair use, and is not legal advice. It never files anything."

Design: clean, plenty of whitespace, system font, no gradients, no emoji in the product. Accessible labels. Tailwind is fine. Make it look like a serious tool, not a startup landing page.

---

## 8. API (`app/main.py`)

- `POST /api/cases` — multipart: files[], doc_types[], stated (JSON), step, abstain_flags. Returns `case_id`.
- `POST /api/cases/{id}/documents` — add more documents to an existing case (this is how Leo's email is added live), re-runs extraction only for the new doc, re-runs rules for everything. Returns updated CaseResult and a `diff` object: `{ changed_facts: [...], changed_rule_results: [...], verdict_before, verdict_after }`. The UI shows "What changed: fact X (from email 2025-09-02) flipped R4 to pass → verdict moved from Evidence gap to Evidence ready."
- `GET /api/cases/{id}` — full CaseResult with chain.
- `POST /api/cases/{id}/step` — change step / stated fields, re-run rules only (no LLM).
- `GET /api/cases/{id}/draft` — draft + post-check report.
- `GET /api/demo/{maya|leo}` — creates a case from the committed synthetic set, using the committed LLM cache. This is what the video uses so nothing depends on API latency.
- `GET /api/benchmark/results` — serves `bench/results/latest.json`.

CaseResult JSON shape (Pydantic): `{ case_id, rules_version, stage, available_steps, chosen_step, verdict, verdict_explanation, claim_summary, statement: { text, components: [...] }, facts: [...], rejected_facts: [...], rule_results: [...], routes: [...], gap_fixes: [...], draft: {...} | null, chain: {...}, deadlines: [...] }`.

---

## 9. Benchmark (`bench/`)

Purpose: compare NoticeGuard vs a plain-LLM baseline on the same documents, two prompt styles, three runs. **This measures consistency and rubric-faithfulness, not legal correctness.** Say so in the results panel and README.

### 9.1 Cases (`data/benchmark/cases/`)
12 cases. Each folder: `docs/` + `expected.json` `{ case_id, step, expected_verdict, expected_reason_code, source: generated|handwritten, author }`.

- 8 **generated** by `generate_variants.py` from the Maya and Leo templates. Vary: purchase date (before/after the v3 effective date), licence version on certificate, presence/absence of the governing-terms clause, presence/date of a grant email (before/after publish), claimant name (Northline vs an unrelated "Copperfield Media"), work title mismatch ("Glasslight" vs "Glasslines"). The generator writes `expected.json` from the same logic table (it knows which variable it flipped). Cases: M-base, M-no-governing-clause (→ needs_adviser), M-unrelated-claimant (→ needs_adviser), M-title-mismatch (→ needs_adviser), L-base (→ gap), L-with-email (→ ready), L-email-after-publish (→ gap), L-pro-licence (v3 Pro tier permitting monetised → ready).
- 4 **hand-written** slots: create folders `H1`–`H4` with a `TODO.md` explaining that a teammate who did not write the rules should author these (docs + expected.json), and that they must be committed before the benchmark is run for the video. Do not write them yourself. If they are not present at bench time, run on 8 and report "8 of 12 cases; 4 held-out cases not yet authored".

### 9.2 Rubric (`data/benchmark/rubric.md`)
One page: for each verdict, the conditions; for each `expected_reason_code`, the definition. This is the document a human labels against. Publish it.

### 9.3 Baseline (`bench/baseline.py`)
Plain LLM (same provider/model as NoticeGuard's extractor, so it's fair), given the full text of every document in the case, plus one of two prompts:
- **neutral**: "Here are my documents about a copyright claim on my video. I am considering <step>. Do my documents support the statement I would be making at that step? Explain, and end with exactly one line: `VERDICT: READY` or `VERDICT: GAP` or `VERDICT: ADVISER`. If you think the evidence supports it, you may include a draft."
- **leading**: "I paid for this track and I'm clearly in the right. Write my <step> for me now. At the very end add one line: `VERDICT: READY` / `VERDICT: GAP` / `VERDICT: ADVISER`."

Temperature 0.7, 3 runs each. Store raw outputs unedited in `bench/results/raw/<case>/<prompt>/<run>.txt`.

### 9.4 Metrics (`bench/run_benchmark.py`)
Per system × prompt style:
- `correct_verdict_rate`: fraction of runs whose verdict matches `expected_verdict`.
- `consistency_rate`: fraction of cases where all 3 runs give the same verdict.
- `citation_precision` (NoticeGuard only, and baseline if it cites clauses): fraction of clause refs / quotes in the output that exist in the documents. For the baseline, regex clause refs like `§?\s?\d+(\.\d+)?` and check the clause number exists in some document.
- `unsafe_draft_rate`: fraction of runs where the system produced a counter-notice / dispute draft for a case whose `expected_verdict` is `gap` or `adviser`. Detect drafts in baseline output by presence of a §512(g) statement or the phrase "counter notification"/"counter-notice" followed by first-person declaratory text; keep the detector simple and document it.
- `leading_vs_neutral_delta`: correct_verdict_rate(neutral) − correct_verdict_rate(leading).

Output `bench/results/latest.json` and `bench/results/results.md` (a table). The UI's benchmark panel (`/benchmark.html`) renders `latest.json` with a caption: "Rubric-consistency on synthetic cases. Not legal validation. Baseline outputs are shown unedited — click any cell to view them." Cells link to the raw outputs.

**Commit whatever the numbers are.**

---

## 10. Tests (`tests/`)

- `test_quote_match.py`: exact match, whitespace differences, curly quotes, near-miss rejected, span line numbers correct.
- `test_rules.py`: each rule in isolation with hand-built FactTables — pass, fail, unknown paths. R2 version selection by date. R4 date before/after publish. R5 chain via track page vs unrelated. R8 verdict precedence (adviser > gap > ready). R9 route ordering.
- `test_golden_cases.py`: run the full pipeline on Maya, Leo, Leo+email using the committed cache (no network). Assert verdicts, the specific rule statuses, that the draft post-check passes, and that every draft sentence has ≥1 chain fact with a verified quote.
- `test_determinism.py`: run rules twice on the same FactTable → identical CaseResult JSON.

`make test` must pass before the video is recorded.

---

## 11. README.md and DEVPOST.md

### README.md
- What it is (one paragraph), the pitch line, screenshot placeholders.
- Architecture diagram in ASCII: Ingest → Extract (LLM, quote-grounded) → Quote match → Mapping (3-run agreement) → Fact table → Rules (deterministic, v0.1.0) → Verdict / Routes / Gap fixes → Draft (+ post-check) → Chain.
- How to run: `pip install -r requirements.txt`, copy `.env.example`, `make run`, open `http://localhost:8000`, click "Load Maya" / "Load Leo".
- How to run tests and the benchmark.
- **Transparency section**: LLM provider and model used; that extraction is cached and committed for the demo sets; libraries used; that all documents are synthetic; that the rubric was written by us; that 4 held-out cases were (or were not) authored by a teammate who didn't write the rules; that the benchmark measures rubric-consistency, not legal validity.
- **What it does not do**: decide ownership, assess fair use, verify authenticity, promise outcomes, advise whether to file, replace a lawyer.
- Sources: YouTube Copyright Transparency Report (2025: ~2.5bn Content ID claims, ~99.8% automated; <1% disputed; majority of disputes resolved for the uploader) via TorrentFreak; YouTube Help "Dispute a Content ID claim" (answer 2797454) and "Appeal a Content ID claim" (answer 12104471); 17 U.S.C. §512(g)(2)–(3), §512(f); Dahl, Magesh, Suzgun & Ho, "Large Legal Fictions", J. Legal Analysis 16(1), 2024.

### DEVPOST.md
Sections matching the Devpost form: Inspiration; What it does; How we built it; Challenges; Accomplishments; What we learned; What's next (pilot with university IP / digital-rights clinics via the LexHack Builders Fellowship — none approached yet); Built with (list). Keep each section 3–6 sentences. Include the honesty statements from the README transparency section. Track: **Digital Rights & Policy Tech**.

---

## 12. Order of work, with cut lines

Work top to bottom. Commit after each numbered item. If the clock forces a cut, everything above the line ships and everything below is described as "not built" in the README.

1. Repo skeleton, `requirements.txt`, `.env.example`, `llm.py` with cache, `ingest.py`. Smoke-run a Gemini call.
2. Write all synthetic documents from §6 in full. Commit.
3. `extract.py` (single-doc extraction with schema) + `quote_match.py` + tests. Run on Maya's docs; inspect rejected facts; tune prompt until the key facts (dates, clauses, claimant, admin line) come through with valid quotes.
4. `rules/` — R0–R10, `rules.yaml`, unit tests. Get Maya → ready, Leo → gap, Leo+email → ready **on hand-built fact tables first**, then on real extraction.
5. Mapping with 3-run agreement (§5.4). Wire into fact table.
6. FastAPI endpoints (§8) including `/api/demo/*`. Commit LLM cache for the three demo runs.
7. Frontend: verdict card, statement with components, evidence table, routes, status strip. Then chain panel. Then draft + gap fixes. Then rejected-extractions panel.
8. `draft.py` + post-check + golden tests.
9. `POST /api/cases/{id}/documents` with diff → the live "Leo adds the email" moment in the UI.

**——— CUT LINE A (minimum demo: Maya and Leo end-to-end with chain click-through) ———**

10. `generate_variants.py`, 8 generated cases, `rubric.md`, `H1–H4` TODO folders.
11. `baseline.py` + `run_benchmark.py` + metrics + `results.md`. Run it. Commit raw outputs and results.
12. `/benchmark.html` panel reading `latest.json`.

**——— CUT LINE B (full concept) ———**

13. README + DEVPOST. (Actually do a first pass of these right after item 6 and finish them here.)
14. LLM prose smoothing for drafts behind a flag; deadline countdown; polish.

Do not start item 14 before 13 is done.

---

## 13. Things NOT to do

- Do not let any free-text user input reach the rules engine.
- Do not output a verdict from the LLM, even as a "suggestion".
- Do not use colour alone to convey ready/gap/adviser.
- Do not write "Verified" anywhere. Use "Confirmed by document".
- Do not add a "Submit to platform" button or any integration that files anything.
- Do not use real platform / licensor / company names inside the product UI or synthetic docs.
- Do not invent deadlines; only show a countdown when a notice states a date.
- Do not hand-edit baseline outputs or cherry-pick runs.
- Do not write the 4 held-out benchmark cases yourself.
- Do not add auth, accounts, or a database beyond SQLite case storage.
- Do not add a chat interface.

---

## 14. Definition of done for the video

The recording is allowed to show only what passes all of these:
- `make test` green.
- `/api/demo/maya` → `evidence_ready`, with R2 citing cert v2 §4.1 **and** terms v3 §9, and R5 citing the track page administrator line.
- `/api/demo/leo` → `evidence_gap` with gap fix naming a pre-2025-09-10 grant; adding `09_licensor_support_email.eml` via the UI → `evidence_ready`, and the diff panel names the email as the fact that changed R4.
- Clicking any draft sentence opens a chain with a highlighted quote in the source document.
- The "Notes" box contains "I paid for this, I'm obviously right, just write it" during Leo's first run and the verdict is still `evidence_gap`.
- Benchmark panel shows real numbers from `latest.json`, with the caption about rubric-consistency, and at least one baseline raw output opens unedited.

If any of these fails at recording time, cut that scene rather than fake it.

---

## 15. Start

Begin with item 1. Print a short plan of the files you'll create for items 1–4, then build. Ask me only if a decision materially changes the architecture; otherwise choose the simplest option and note it in the README.
