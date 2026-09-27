import json

from tests.helpers import leo_facts, leo_mappings, maya_facts, maya_mappings, run, stated_full


def _dump(out):
    return json.dumps({
        "verdict": out.verdict, "explanation": out.verdict_explanation, "stage": out.stage,
        "rules": [r.model_dump() for r in out.rule_results], "statement": out.statement.model_dump(),
        "routes": [r.model_dump() for r in out.routes], "gaps": [g.model_dump() for g in out.gap_fixes],
        "facts": [f.model_dump() for f in out.facts], "step_evidence": [s.model_dump() for s in out.step_evidence],
    }, sort_keys=True)


def test_rules_are_deterministic():
    a = _dump(run(maya_facts(), maya_mappings(), "dispute"))
    b = _dump(run(maya_facts(), maya_mappings(), "dispute"))
    assert a == b
    c = _dump(run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", stated_full()))
    d = _dump(run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", stated_full()))
    assert c == d


def test_input_order_does_not_matter():
    facts = maya_facts()
    a = _dump(run(facts, maya_mappings(), "dispute"))
    b = _dump(run(list(reversed(facts)), list(reversed(maya_mappings())), "dispute"))
    # facts list order is preserved in output, so compare everything except the facts array
    ja, jb = json.loads(a), json.loads(b)
    ja.pop("facts"); jb.pop("facts")
    assert ja == jb
