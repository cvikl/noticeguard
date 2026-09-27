---
version: 1
slug: "static-index-html"
primary_target: "static/index.html"
related_targets: ["static/app.js","static/styles.css","static/benchmark.html"]
---

# Surface brief: static/index.html (NoticeGuard tool)

Scope: the single-page tool (index.html, app.js, styles.css) plus benchmark.html. Visitor mode: Operate.
Audience and job: a creator with a claim and a folder of documents; judges inspecting the chain. Task: load documents, choose the step, read the verdict, click any sentence to see Document → Quote → Fact → Rule → Status, copy a draft when ready, add a document and read "what changed".
Proof/content: real pipeline JSON from /api/demo/maya and /api/demo/leo (committed cache); synthetic names only.
Constraints: no build step, vanilla JS; three verdicts always in words + icon + colour; "Confirmed by document" never "Verified"; no Submit button; no emoji; desktop-first at 1920×1080, phone-tolerant; footer disclaimer always visible; "Rules version 0.1.0" in the chain panel.
Direction pinned by the user (brief wins over the roll): editorial serif display, warm off-white ground, charcoal rounded cards, slick pill buttons; verdict = ink + one accent each. Roll acknowledged: seed key b54c477e assigned index 3 of the grounded list; the pinned brief overrides its materials, the roll's topology discipline (one continuous surface, no modals) is kept.

## Direction contract

THESIS: A case file laid out on a desk: one continuous paper surface with a dark verdict slab and a live chain panel, refusing the SaaS dashboard of same-size stat cards and the chatbot transcript.
OWN-WORLD: Ground #F3F0EA warm paper, ink #1A1917, secondary #6B665E, hairlines #DAD5CC; charcoal slabs #161513 with cream text for the verdict and the draft; one accent per verdict only (ready #1F6B3A, gap #9A6200, adviser #7A1F2B), nothing else coloured. Display and quoted clauses in Source Serif 4 (optical sizes, italic for quotes); UI, labels, tables in the system sans with tabular numerals. Pill buttons: charcoal fill / cream text, outline secondary, 2px ink focus ring offset 2px, hover lifts 1px with an offset soft shadow. Status chips are small serif-less pills with a 6px drawn glyph. Rules and hairlines 1px only.
STORY: The creator sees where they are in the process, reads one sentence that says whether the paperwork backs the step, then clicks any sentence and watches the exact quote light up in their own document. They leave knowing which clause carries each part of the statement and which document would close a gap. They never see a "file now" button.
FIRST VIEWPORT (1920×1080): top bar with the serif wordmark, "Load Maya" / "Load Leo" pills, Benchmark link. Under it a full-width process rail: five serif stage names on one hairline with "You are here" set as a small ink marker under the current stage, risk copy in secondary under future stages, step-evidence chips under each. Below, three columns: inputs (320px) on the left, results centre (fluid, max 76ch prose), chain panel (400px, sticky) on the right. The verdict slab is the first thing in the centre column: a charcoal rounded card, 44px serif heading "Evidence ready for: In-platform dispute", a 28px drawn glyph in the verdict accent, one paragraph in cream. Footer disclaimer pinned to the bottom edge.
FORM: candidate "case file on a desk" (position 1 of the ordered grounded list; the roll assigned index 3, overridden by the user-pinned brief); seed key b54c477e.
SIGNATURE INTERACTION: click a sentence → the chain panel fills top-down (document chip, the document text scrolled to the highlighted quote, fact row, rule row, status) with a 240ms ease-out reveal; the highlighted span pulses once in the verdict accent. Motion grammar: 150–250ms, exponential ease-out, no page-load choreography; the only authored moment is the verdict slab settling in (scale 1.015→1, blur 3px→0, 320ms) when a result arrives.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
