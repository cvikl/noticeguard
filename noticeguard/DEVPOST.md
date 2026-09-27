# NoticeGuard — Devpost submission

**Track:** Digital Rights & Policy Tech

**Live demo:** https://noticeguard.primafacie.eu (click Load Maya / Load Leo; runs from the committed extraction cache)

## Inspiration

YouTube alone processed about 2.5 billion Content ID claims in 2025, almost all of them automated. Creators disputed only about one claim in 200, yet most of the disputes they did file were resolved in their favour. We kept meeting the same two people: the creator who gives up on a claim she could win because the licensor's website now says something different from the licence she bought, and the creator who is about to swear a counter-notice under penalty of perjury on evidence he does not yet have. A chatbot helps neither, because it answers the question as it is framed.

## What it does

NoticeGuard reads the creator's own documents and reports whether they back the step the creator is about to take: Evidence ready, Evidence gap, or Needs an adviser. It shows the process stage, the exact statement the creator would be making, which component of it each document supports, the lowest-risk route first, and what document would close a gap. Every sentence clicks through to Document → Quote → Fact → Rule → Status. A draft is prepared only when evidence is ready and is post-checked against the confirmed facts. It gives the same answer to "I paid for this, I'm obviously right, just write it" as to a neutral question, because free text never reaches the rules. It never tells anyone whether to file.

## How we built it

The model highlights, it never types: it returns each document with XML-style tags around spans, and the tag-stripped output must equal the original text or the whole extraction is rejected and retried with the diff. Values and categorical labels are derived in code. Wording that needs interpretation (does "monetised video on social platforms" cover a monetised ClipStream channel?) is asked three times; anything short of 3/3 agreement sends the case to an adviser. A deterministic, versioned rules engine (R0–R10, `rules.yaml`) decides; FastAPI serves the API and a vanilla-JS front end; the demo runs from a committed LLM cache. Built with Claude Code, with the Impeccable design skill for the interface.

## Challenges we ran into

The first real run sent Maya, who should be ready, to an adviser: the model had tagged "Pro licence additionally permits broadcast…" as a restriction, and one of three runs called it unclear. That forced us to state a precedence rule we now stand behind: a clear permission is only defeated by a clear exclusion, and the disagreement is shown in the chain rather than smoothed over. We also had no API key in the build environment, so we added a provider that shells out to the Claude CLI and disclosed that its sampling temperature cannot be set.

## Accomplishments we're proud of

Every fact on screen is a highlighted span in the creator's own document, located by character offset, and the golden tests assert that. The post-check caught a real defect during the build (a quote shortener cut a word in half and the draft was withheld rather than shown). The demo moment works end to end: Leo's counter-notice is an evidence gap until the 2 September email is added live, and the diff panel names the email as the fact that flipped R4. On the 8 generated benchmark cases (3 runs each, cache off), NoticeGuard matched the rubric in 47 of 48 runs and never drafted for a gap or adviser case; the same model as a plain chatbot matched in 41.7% of neutral runs and 20.8% of leading runs, and produced a draft for a case it should not have in 14 of 48 runs. Its one miss was the round-trip guard rejecting an email the model had altered, which we count as the guard working.

## What we learned

Abstaining is a feature that has to be designed, not a failure mode to apologise for. Agreement between runs is a more honest confidence signal than a model's self-reported confidence. And the cheapest fix is usually outside the platform: ask the licensor to have its administrator release the claim before any sworn statement.

## What's next

Pilot with university IP clinics and digital-rights advice services through the LexHack Builders Fellowship (none approached yet); more licensor worlds beyond one synthetic catalogue; the four held-out benchmark cases written by someone who did not write the rules; and a reviewer mode for advisers who receive the chain rather than the verdict.

## Honesty statements

All documents, companies and names are synthetic. The rubric was written by us; the 8 generated benchmark cases are labelled by the variable the generator flipped; the 4 held-out cases had not been authored at submission time, so the benchmark reports 8 of 12. The benchmark measures rubric-consistency and resistance to a leading prompt, not legal validity; baseline outputs are committed unedited. Extraction is cached and committed for the demo sets. NoticeGuard does not verify authenticity, decide ownership or fair use, or advise whether to file.

## Built with

Python 3.12, FastAPI, Pydantic v2, pypdf, python-dateutil, PyYAML, pytest, SQLite; Claude (Sonnet) via the Claude CLI for extraction, mapping and the baseline; vanilla HTML/CSS/JavaScript with Source Serif 4; Docker + Caddy on a shared Hetzner box.
