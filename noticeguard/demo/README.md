# Maya demo — Bernard's certificates

Script for filming: **SCRIPT.txt** (plain text, phone-friendly).

Public demo links (load instantly from cache, identical every time):

- V2, evidence ready: https://noticeguard.ruleandrecord.com/?demo=maya
- V3 what-if, evidence gap: https://noticeguard.ruleandrecord.com/?demo=maya-v3

## Folders

- `01-maya-original/` — Bernard's v2 certificate PDF (issued 12 March 2025, order GA-2025-03112) plus the five supporting documents: claim notice, receipt, current licensor terms, track page, video export.
- `02-maya-what-if/` — Bernard's v3 certificate PDF (issued 14 July 2025, order GA-2025-07218) plus matching supporting documents.
- `03-optional-permission-email/` — not part of the 90-second story. Adding it to the v3 case turns gap into ready.

The PDF bytes are byte-identical to the files Bernard supplied in `../../demo/`; only the filenames are shortened. The website's demo buttons load the same sets from `../data/synthetic/maya_bernard_v2/` and `_v3/`.

The supporting documents are required: without the claim notice and track page the rules cannot detect the stage or the claimant, and both cases fall to "needs an adviser".

## Manual upload (if not using the links)

Upload one whole folder. Select Maya Ortiz, channel Maya Draws, monetised Yes, step Dispute. Leave address and phone blank, fair-use and ownership flags unchecked. Analyse. Use a fresh tab for the what-if; do not append v3 to the v2 case.

## What the viewer shows

PDF documents render as the original page with highlights overlaid on the clauses. "Highlighted text" switches to the extracted-text view; "Open PDF" opens the raw file. TXT documents show as restyled text.

## Verify locally

```sh
../.venv/bin/python demo/verify.py --provider gemini --model gemini-3.8-flash
```

Run from `noticeguard/`. Cache-only by default; expects v2 ready, v3 gap, email flips v3 to ready.
