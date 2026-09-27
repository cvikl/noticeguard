# NoticeGuard — LexHack 2026

**NoticeGuard checks the statement you'd sign, not the question you ask.**

An evidence-readiness checker for independent creators hit by an automated copyright claim. The creator uploads their documents (claim notice, licence, receipt, licensor terms, emails) and picks the step they are about to take. A language model only highlights spans in those documents; a deterministic, versioned rules engine decides; the result is one of three words: **Evidence ready**, **Evidence gap**, or **Needs an adviser**. Every sentence clicks through Document → Quote → Fact → Rule → Status. It never tells anyone whether to file.

- **Live demo:** https://noticeguard.ruleandrecord.com (Maya v2: `/?demo=maya`, Maya v3: `/?demo=maya-v3`, Leo: `/?demo=leo`, benchmark: `/benchmark.html`)
- **Track:** Digital Rights & Policy Tech
- **Full technical README, architecture, rules and benchmark:** [noticeguard/README.md](noticeguard/README.md)

## Repository layout

| Path | What it is |
|---|---|
| [`noticeguard/`](noticeguard/) | The application: FastAPI back end, rules engine (`app/rules/`), vanilla-JS front end (`static/`), tests, benchmark, deploy bundle and the committed LLM cache that lets the demo run offline |
| [`noticeguard/demo/`](noticeguard/demo/) | The demo document sets and the 90-second demo script |
| [`submission/`](submission/) | Devpost write-up input, the Tech Stack document, screenshots and the original demo certificates |
| [`docs/`](docs/) | Concept note and the Claude Code build prompts the project was built from |
| [`design/`](design/) | Visual references used for the interface |

## Run locally

```bash
cd noticeguard
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # add GEMINI_API_KEY for live uploads; the demo cases run from cache
make run                  # http://localhost:8000
make test                 # 69 pytest tests, offline
node tests/test_workspace.cjs
```

## Honesty statements

All documents, companies and people are synthetic (ClipStream, Glasswork Audio, Northline Rights, "Glasslight" do not exist). The runtime model is Gemini 3.8 Flash; the benchmark in the technical README was run earlier with Claude Sonnet and is labelled as such. The rubric and the 8 generated benchmark cases were written by us; the 4 held-out cases were not authored, so the benchmark reports 8 of 12. The code was built with Claude Code and the Impeccable design skill; see `docs/` for the build prompts and [`submission/NoticeGuard Tech Stack.docx`](submission/) for every library and AI tool used. NoticeGuard does not verify authenticity, decide ownership or fair use, or advise whether to file.

## Licence

MIT (see [noticeguard/LICENSE](noticeguard/LICENSE)).
