# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Plain static HTML/CSS/vanilla JS served by FastAPI (no build step), as fixed by the build prompt. Delivery target: a Docker container behind the shared Caddy at noticeguard.primafacie.eu, plus a 1920×1080 screen recording for Devpost. (Confirmed by the build prompt; not delegated.)

## Users

Independent video creators (animators, musicians, vloggers) who have just received an automated copyright claim on a video platform and are deciding whether to dispute, appeal, or file a DMCA counter-notice. They arrive anxious, often convinced they are either obviously right or obviously lost, with a folder of documents (claim notice, receipt, licence certificate, licensor terms, track page, video export, emails). Secondary audience: hackathon judges and IP-clinic advisers inspecting the reasoning chain. (Confirmed by the build prompt and concept note.)

## Product Purpose

NoticeGuard is an evidence-readiness checker. The creator uploads documents and picks the step they are about to take; an LLM only highlights spans in the documents, a deterministic rules engine decides, and the result is one of three words: Evidence ready, Evidence gap, Needs an adviser. Success is a creator who knows exactly which clause supports each part of the statement they would sign, which document would close a gap, and the lowest-risk route, before they take any step. It never tells anyone whether to file.

## Positioning

"NoticeGuard checks the statement you'd sign, not the question you ask." Same answer to a leading question as to a neutral one; every sentence clicks through Document → Quote → Fact → Rule → Status; a draft exists only when evidence is ready and is post-checked against the confirmed facts. A chatbot cannot truthfully claim any of these.

## Operating Context

Desktop-first, used at a desk with a folder of PDFs/TXT/EML files, typically once per claim. The demo is a screen recording at 1920×1080 with two cases (Maya: ready for a dispute; Leo: gap for a counter-notice until a licensor email arrives). Judges inspect the chain panel and the benchmark page. All names are synthetic (ClipStream, Glasswork Audio, Northline Rights, "Glasslight").

## Capabilities and Constraints

- Inputs: multi-file upload with a document-type per file; structured "About you" fields (name, address, phone, monetised yes/no/don't know, step, two abstain checkboxes); a free-text Notes box that is deliberately ignored by the decision path.
- Outputs: process status strip (Claim → Dispute → Appeal → Removal + strike → Counter-notice, "You are here"), verdict card, claim in plain language, the statement with per-component Supported / Not supported / Unknown badges, evidence table (Confirmed by document / Stated by you / Missing / Conflicting), routes lowest-risk first, gap fixes, draft (copy only, never submit), rejected extractions, chain panel with highlighted quote in the source document, "what changed" diff when a document is added, deadline countdown only when a notice states a date, benchmark page.
- Hard rules: three outcomes only, always in words (never colour alone); the label is "Confirmed by document", never "Verified"; never a Submit/File button; no emoji in the product; no real platform or company names; no chat interface; rules version shown ("Rules version 0.1.0").
- Terminology: claim, dispute, appeal, removal request, copyright strike, counter-notice (17 U.S.C. §512(g)), licensed-use conflict, rights administrator, licence version in force, governing-terms clause.
- Undecided: none material. Mobile is "tolerated", not designed for.

## Brand Commitments

Name: NoticeGuard. Voice: plain English, calm, on the creator's side, never advisory about filing ("your evidence is ready for X", "a draft prepared for your review"). Binding visual constraints volunteered by the user: editorial serif display type with a sans for UI, warm off-white ground, charcoal rounded cards, pill buttons; the reference the user likes is /home/timotej/Documents/bcco/LexHack/inspo/486d0ba63ca589b46127836faf84f818.jpg (a legal-research tool with serif headings, dark rounded cards, document chips). Verdict colour: ink plus one accent per verdict (green / amber / oxblood), everything else monochrome. No gradients.

## Evidence on Hand

- Two full synthetic document sets and a licensor email: data/synthetic/maya, data/synthetic/leo, data/synthetic/leo_email.
- Committed LLM extraction cache so the demo runs offline: cache/llm.
- Golden expectations: Maya → evidence_ready (dispute); Leo → evidence_gap (counter-notice); Leo + email → evidence_ready.
- Benchmark results will be whatever they are (bench/results/latest.json); none exist yet and must not be invented.
- Real-world statistics (YouTube transparency report) belong in README/Devpost only, never in the product UI.

## Product Principles

1. The document is the authority: every claim on screen traces to a highlighted span.
2. Words before colour: a verdict is a sentence, colour only underlines it.
3. Least-risk route first; the tool reports readiness, never recommends filing.
4. Abstaining is a feature: ambiguity is shown, not smoothed over.
5. Nothing is faked: rejected extractions, disagreeing mapping runs and benchmark numbers are shown as they are.

## Accessibility & Inclusion

Status never conveyed by colour alone (icon + word + colour). Accessible labels on all form controls; keyboard-reachable chain panel; body text contrast ≥ 4.5:1.
