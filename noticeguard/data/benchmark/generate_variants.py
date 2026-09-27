#!/usr/bin/env python3
"""Generate the 8 variant benchmark cases from the Maya and Leo document sets.

Each variant flips one variable of the base set; expected.json is written from the same logic table,
so the label comes from the variable that was flipped, not from running NoticeGuard.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.ingest import bytes_to_text  # noqa: E402
SYN = ROOT / "data" / "synthetic"
OUT = Path(__file__).resolve().parent / "cases"
AUTHOR = "generate_variants.py (rules author)"

EMAIL_TEMPLATE = (SYN / "leo_email" / "09_licensor_support_email.eml").read_text()


def copy_set(src_folders: list[Path], dst: Path) -> dict[str, Path]:
    docs = dst / "docs"
    if docs.exists():
        shutil.rmtree(docs)
    docs.mkdir(parents=True)
    out = {}
    for folder in src_folders:
        for p in sorted(folder.iterdir()):
            if p.suffix in (".txt", ".eml"):
                shutil.copy(p, docs / p.name)
                out[p.name] = docs / p.name
            elif p.suffix == ".pdf":  # Bernard's PDF certificates: variants edit the extracted text
                dst_txt = docs / (p.stem + ".txt")
                dst_txt.write_text(bytes_to_text(p.name, p.read_bytes()))
                out[dst_txt.name] = dst_txt
    return out


def edit(path: Path, fn) -> None:
    path.write_text(fn(path.read_text()))


def write_expected(dst: Path, case_id: str, step: str, verdict: str, code: str, note: str) -> None:
    (dst / "expected.json").write_text(json.dumps({
        "case_id": case_id, "step": step, "expected_verdict": verdict, "expected_reason_code": code,
        "source": "generated", "author": AUTHOR, "note": note}, indent=2) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    maya, leo, leo_email = SYN / "maya_bernard_v2", SYN / "leo", SYN / "leo_email"

    # M-base: Maya as shipped -> ready (v2 4.1 covers monetised; v3 §9.1 governs by purchase date)
    d = OUT / "M-base"; copy_set([maya], d)
    write_expected(d, "M-base", "dispute", "evidence_ready", "licence_covers_use", "Maya's set unchanged.")

    # M-no-governing-clause: remove clause 9 from the current terms AND the cert's 6.1 -> adviser
    d = OUT / "M-no-governing-clause"; files = copy_set([maya], d)
    edit(files["04_licensor_terms_v3_current.txt"], lambda t: re.sub(r"9\. Governing terms\n9\.1 [^\n]+\n\n", "", t))
    edit(files["03_licence_certificate_v2.txt"], lambda t: re.sub(r"6\.\s+Governing terms\n6\.1\n?(?:[^\n]+\n)+?\n?(?=7\.)", "", t))
    write_expected(d, "M-no-governing-clause", "dispute", "needs_adviser", "no_governing_clause",
                   "Certificate is v2, current terms are v3, and no clause says which version governs.")

    # M-unrelated-claimant: claimant is Copperfield Media, not named anywhere by the licensor -> adviser
    d = OUT / "M-unrelated-claimant"; files = copy_set([maya], d)
    edit(files["01_claim_notice.txt"], lambda t: t.replace("Northline Rights", "Copperfield Media").replace("claims@northlinerights.example", "claims@copperfieldmedia.example"))
    write_expected(d, "M-unrelated-claimant", "dispute", "needs_adviser", "unrelated_claimant",
                   "The claim notice names Copperfield Media; the track page still names Northline Rights as administrator.")

    # M-title-mismatch: the claim is for "Glasslines", the licence is for "Glasslight" -> adviser
    d = OUT / "M-title-mismatch"; files = copy_set([maya], d)
    edit(files["01_claim_notice.txt"], lambda t: t.replace("Matched work: Glasslight — Lumen Vale", "Matched work: Glasslines — Lumen Vale"))
    write_expected(d, "M-title-mismatch", "dispute", "needs_adviser", "work_mismatch", "Matched work title differs from the licensed work.")

    # L-base: Leo as shipped -> gap (v3 Standard excludes monetised use; no grant)
    d = OUT / "L-base"; copy_set([leo], d)
    write_expected(d, "L-base", "counter_notice", "evidence_gap", "tier_excludes_monetised", "Leo's set without the licensor email.")

    # L-with-email: Leo plus the 2 Sept email -> ready
    d = OUT / "L-with-email"; copy_set([leo, leo_email], d)
    write_expected(d, "L-with-email", "counter_notice", "evidence_ready", "grant_before_publish", "Email dated 2025-09-02, video published 2025-09-10.")

    # L-email-after-publish: same email dated 15 Sept (after the 10 Sept publish date) -> gap
    d = OUT / "L-email-after-publish"; files = copy_set([leo, leo_email], d)
    edit(files["09_licensor_support_email.eml"], lambda t: t.replace("Tue, 2 Sep 2025 10:14:00 +0100", "Mon, 15 Sep 2025 10:14:00 +0100")
         .replace("GW-SUP-55120.20250902", "GW-SUP-55120.20250915").replace("On 1 Sep 2025, at 18:42", "On 14 Sep 2025, at 18:42")
         .replace("I'm about to publish a full live set with ads on. Am I covered, or do I need Pro?", "I published a full live set with ads on last week and got a claim. Am I covered, or do I need Pro?")
         .replace("Thanks for checking before you publish, and congratulations on the channel growth.", "Thanks for getting in touch, and congratulations on the channel growth."))
    write_expected(d, "L-email-after-publish", "counter_notice", "evidence_gap", "grant_after_publish",
                   "The grant is dated 2025-09-15, after publication on 2025-09-10.")

    # L-pro-licence: Leo bought Pro (v3 4.2 permits monetised video) -> ready
    d = OUT / "L-pro-licence"; files = copy_set([leo], d)
    edit(files["04_receipt.txt"], lambda t: t.replace("Glasslight — Standard licence", "Glasslight — Pro licence").replace("GBP 29.00", "GBP 89.00").replace("VAT (20%): GBP 5.80", "VAT (20%): GBP 17.80").replace("Total charged: GBP 34.80", "Total charged: GBP 106.80"))
    edit(files["05_licence_certificate_v3.txt"], lambda t: t.replace("Licence tier: Standard", "Licence tier: Pro"))
    write_expected(d, "L-pro-licence", "counter_notice", "evidence_ready", "licence_covers_use", "Pro tier: v3 clause 4.2 permits monetised video.")

    print("wrote 8 generated cases to", OUT)


if __name__ == "__main__":
    main()
