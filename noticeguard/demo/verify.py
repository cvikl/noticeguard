"""Verify actual demo outcomes; --populate-cache permits real model calls."""
from pathlib import Path
import argparse
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ingest import load_folder
from app.llm import LLM, LLMUnavailable
from app.models import AbstainFlags, StatedFields
from app.pipeline import new_state, run_case, run_extraction, diff_results
class CacheOnlyLLM(LLM):
    def _call(self, *args, **kwargs):
        raise LLMUnavailable('Missing model cache. Run with --populate-cache once a provider is available.')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--populate-cache', action='store_true')
parser.add_argument('--provider', default='gemini')
parser.add_argument('--model', default=None)
args = parser.parse_args()
failed = False
for folder, expected in [('01-maya-original', 'evidence_ready'), ('02-maya-what-if', 'evidence_gap')]:
    llm = (LLM if args.populate_cache else CacheOnlyLLM)(provider=args.provider, model=args.model, use_cache=True)
    try:
        state = new_state(load_folder(ROOT / 'demo' / folder), 'dispute',
            StatedFields(name='Maya Ortiz', channel_name='Maya Draws', monetised='yes'), AbstainFlags())
        run_extraction(state, llm=llm)
        result = run_case(state, llm=llm)
        rules = {r.rule_id: r.status for r in result.rule_results}
        assert result.verdict == expected, (result.verdict, expected)
        assert all(rules[r] == 'pass' for r in ['R0', 'R1', 'R2', 'R5'])
        assert not any(d.extraction_failed for d in result.documents)
        assert rules['R3'] == ('pass' if expected == 'evidence_ready' else 'fail')
        if expected == 'evidence_ready':
            assert result.draft and result.draft.post_check.passed and not result.draft.withheld_reason
            for sentence in result.draft.sentences:
                assert any(f.quote and f.doc_id for f in result.chain[sentence.id].facts)
        else:
            assert result.draft is None
        print(f'{folder}: PASS {result.verdict}; {llm.calls} live calls, {llm.cache_hits} cache hits', flush=True)
        if expected == 'evidence_gap':
            before = result.model_dump()
            email_docs = load_folder(ROOT / 'demo' / '03-optional-permission-email')
            state['documents'].extend(d.model_dump() for d in email_docs)
            run_extraction(state, only_doc_ids=[d.id for d in email_docs], llm=llm)
            updated = run_case(state, llm=llm)
            assert updated.verdict == 'evidence_ready', updated.verdict
            assert not any(d.extraction_failed for d in updated.documents)
            assert next(r for r in updated.rule_results if r.rule_id == 'R4').status == 'pass'
            assert updated.draft and updated.draft.post_check.passed and not updated.draft.withheld_reason
            for sentence in updated.draft.sentences:
                assert any(f.quote and f.doc_id for f in updated.chain[sentence.id].facts)
            diff = diff_results(before, updated, email_docs)
            assert any(r['rule_id'] == 'R4' and r['after'] == 'pass' for r in diff.changed_rule_results)
            print('Optional permission email: PASS gap -> ready, R4 changed', flush=True)

    except (LLMUnavailable, AssertionError) as e:
        failed = True
        print(f'{folder}: BLOCKED/FAILED: {e}', flush=True)
sys.exit(1 if failed else 0)
