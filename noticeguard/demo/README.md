# Maya — Bernard's final 90-second demo

Use Bernard's original PDF certificates. Both public demos now use these PDFs, with consistent supporting documents. The story is **Maya v2 → Evidence ready → what if she bought under v3? → Evidence gap**. Do not introduce Leo or add the optional email during this recording.

## Public links and screenshots for Bernard

- V2: https://noticeguard.ruleandrecord.com/?demo=maya
- V3: https://noticeguard.ruleandrecord.com/?demo=maya-v3

Open either link and click **Next step** (or **Your answer** in the top navigation).

- V2 screenshot: [Evidence ready and claim-release route](../docs/screenshots/bernard-maya-result.png)
- V3 screenshot: [Evidence gap, Not supported, and v3 §4.1](../docs/screenshots/bernard-maya-v3-result.png)

Both screenshots are unedited captures of the deployed result screens. They show actual rule results and source quotes, not a mockup. The ready result reports documentary support and offers the route to ask the licensor to have Northline Rights release the claim; it does not promise success or file anything.

## Recording setup

Each folder contains **five TXT supporting documents and one PDF certificate**:

1. `01-maya-original`: Bernard's v2 PDF, issued 12 March 2025; receipt order GA-2025-03112.
2. `02-maya-what-if`: Bernard's v3 PDF, issued 14 July 2025; matching receipt order GA-2025-07218.

Bernard's PDF bytes are unchanged; only the copied filenames are shortened. Supporting documents use his licensor address/contact. The v3 receipt has been corrected from our earlier August scenario to his July purchase. Publication remains 30 August 2025, after both purchases; the claim remains 20 September 2025. Current v3 terms took effect on 1 June 2025.

Upload one complete folder at a time. Select **Maya Ortiz**, channel **Maya Draws**, monetised **Yes**, step **Dispute**. Leave address/phone blank and fair-use/ownership flags unchecked. Click **Analyse**.

For the what-if, use a second tab at the homepage and upload the second set as a new case. Do not append v3 to the original case with Add evidence. For a faster recording, the public demo links above load exactly the same case documents/settings. The home page and Try a demo menu expose both versions to judges.

## 90-second script

| Time | On screen | Narration |
|---|---|---|
| 0–15s | Upload the original six files, select Dispute and monetised Yes, then Analyse. | “This is Maya's synthetic case. She bought music for her monetised video, but received a copyright claim. Today's terms appear to exclude her use.” |
| 15–30s | Show the v2 PDF's extracted §4.1 permission and governing-terms finding. | “Her original licence allows monetised video. The governing terms preserve the rights she bought in March, even though today's terms have changed.” |
| 30–45s | Click Next step. Hold on Evidence ready and the first route. | “Her documents support a dispute. The first route is to ask the licensor to have its administrator release the claim.” |
| 45–55s | Scroll to the draft and click a sentence; it opens its source evidence. | “The draft is prepared for review. Every factual statement links back to the documents behind it.” |
| 55–65s | Switch to the separate v3 scenario, using its six files or public link. | “What if Maya had bought the same track in July, after the terms changed?” |
| 65–82s | Click Next step. Show Evidence gap, Not supported, and quoted v3 §4.1 together. | “Her v3 Standard licence covers non-monetised video content. Monetised use requires Pro. That part of her statement is not supported, so no draft is produced.” |
| 82–90s | Hold on the gap and quote. | “Same creator, same track—different evidence, different result. Maya decides what to do.” |

Label the alternate scene **What if: purchased after the terms changed**. These are historical fictional examples, not a claim about a real creator. The benchmark and architecture belong in the slides.

## Exact clauses to show

- V2 certificate §4.1: “Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee.”
- Governing terms: certificate §6.1 and current terms §9.1 preserve purchase terms.
- V3 certificate §4.1: “Standard licence permits use of the Work as background music in non-monetised video content on channels operated by the Licensee.”
- V3 certificate §4.2 explicitly requires Pro for monetised use. The rule explanation cites this exclusion while the component also displays Bernard's requested §4.1 quote.

## Verification — 27 September 2026

Both Bernard scenarios passed the full Gemini gemini-3.8-flash pipeline and the deployed public demo endpoints, with zero live model calls on the final public rehearsal. V2: R2/R3/R5 pass, supported draft. V3: R2/R5 pass, R3 fails, unsupported use component, no draft. Both expose the exact PDF certificate quote. 74 Python tests and 10 JavaScript tests passed.

The full local check (including the optional email) is:

```sh
../.venv/bin/python demo/verify.py --provider gemini --model gemini-3.8-flash
```

Run from `noticeguard/`. Default is cache-only; `--populate-cache` permits actual model calls. Avoid deployments during recording and warm up both tabs before filming.

## Optional email — outside the main story

`03-optional-permission-email/07_licensor_permission_email.eml` now references Bernard's July order GA-2025-07218. Its grant date, 25 August, is before publication. Adding it to the v3 case was verified locally to change the result from gap to ready. Keep it out of the initial uploads and the agreed 90-second story.

## Formats

TXT/Markdown, plain-text EML and selectable-text PDF are supported. No OCR, DOCX or image input. PDF highlights appear in the formatted extracted-text view, not over the original PDF page. The scan texture is a visual treatment.
