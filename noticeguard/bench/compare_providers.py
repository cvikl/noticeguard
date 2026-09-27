"""Fresh Gemini vs cache-only Claude demo regression; promote cache only on success.
Run with: python -m bench.compare_providers. This does not rerun the full benchmark.
"""
import json
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from app.ingest import load_folder
from app.llm import CACHE_DIR, LLM
from app.main import DATA, DEMO_SETS
from app.models import AbstainFlags
from app.pipeline import new_state, run_case, run_extraction

class HistoricalLLM(LLM):
    def _call(self, *args, **kwargs):
        raise AssertionError('Historical Claude comparison must use cache only')

def outcomes(llm):
    results = {}
    for name, spec in DEMO_SETS.items():
        print(f'{llm.provider}: checking {name}', flush=True)
        docs = [d for folder in spec['folders'] for d in load_folder(DATA / folder)]
        state = new_state(docs, spec['step'], spec['stated'], AbstainFlags())
        run_extraction(state, llm=llm)
        results[name] = run_case(state, llm=llm, today=date(2026, 9, 27))
        print(f'{name}: {results[name].verdict}', flush=True)
        if name == 'leo':
            email = load_folder(DATA / 'leo_email')
            state['documents'].extend(d.model_dump() for d in email)
            run_extraction(state, only_doc_ids=[d.id for d in email], llm=llm)
            results['leo+email'] = run_case(state, llm=llm, today=date(2026, 9, 27))
            print(f"leo+email: {results['leo+email'].verdict}", flush=True)
    return results

def decision(r):
    return dict(verdict=r.verdict, stage=r.stage, chosen_step=r.chosen_step,
                rules={x.rule_id:x.status for x in r.rule_results},
                components={x.id:x.status for x in r.statement.components},
                draft_available=bool(r.draft and not r.draft.withheld_reason and r.draft.post_check.passed),
                routes=[(x.id,x.rank,x.evidence_status) for x in r.routes],
                step_evidence=[(x.step,x.evidence_status,x.available) for x in r.step_evidence],
                gaps=[x.component for x in r.gap_fixes])

def quote_errors(r):
    docs = {d.id:'\n'.join(d.lines) for d in r.documents}
    sources = [s for f in r.facts for s in f.sources]
    sources += [s for node in r.chain.values() for s in node.facts if s.doc_id and s.quote]
    return sum(1 for s in sources if getattr(s, 'exact', True) is False or docs[s.doc_id][s.char_start:s.char_end] != s.quote)

def main():
    historical = HistoricalLLM(provider='claude_cli',model='sonnet',use_cache=True)
    before = outcomes(historical)
    staging = Path(tempfile.mkdtemp(prefix='noticeguard-gemini-cache-'))
    print(f'Fresh Gemini cache: {staging}',flush=True)
    candidate = LLM(provider='gemini',model='gemini-3.8-flash',cache_dir=staging,use_cache=True)
    after = outcomes(candidate)
    cases = []
    for name,r in after.items():
        old,new = decision(before[name]),decision(r)
        differences = {k:dict(claude=old[k],gemini=new[k]) for k in old if old[k]!=new[k]}
        invalid = quote_errors(r)
        rejected = [d.filename for d in r.documents if d.extraction_failed]
        cases.append(dict(case=name,passed=not differences and not invalid and not rejected,
                          claude=old,gemini=new,differences=differences,invalid_quotes=invalid,
                          rejected_documents=rejected,facts=len(r.facts),mapping_runs=len(r.mapping_runs),
                          draft_text_identical=(before[name].draft.text if before[name].draft else None)==(r.draft.text if r.draft else None)))
        (staging/f'{name}-result.json').write_text(r.model_dump_json(indent=2))
    passed = all(c['passed'] for c in cases)
    report = dict(generated_at=datetime.now(timezone.utc).isoformat(),passed=passed,
                  baseline=dict(provider=historical.provider,model=historical.model,live_calls=historical.calls),
                  candidate=dict(provider=candidate.provider,model=candidate.model,live_calls=candidate.calls,cache_hits=candidate.cache_hits),
                  cases=cases,scope='Three demo outcomes with fresh Gemini calls; historical benchmark not rerun.')
    target = Path(__file__).parent/'results'/'provider_migration.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    if passed:
        for path in staging.glob('*.json'):
            if len(path.stem)==64: shutil.copy2(path,CACHE_DIR/path.name)
        print('PASS: decisions and exact quotes match; Gemini demo cache promoted.',flush=True)
    else:
        print(json.dumps(cases,indent=2),flush=True)
        print('FAIL: cache not promoted; inspect staged results.',flush=True)
    print(f'Report: {target}; Gemini live calls: {candidate.calls}',flush=True)
    return 0 if passed else 1

if __name__=='__main__':
    raise SystemExit(main())
