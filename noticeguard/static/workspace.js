/* Presentation helpers only. Verdicts and rule outcomes always come from the API. */
(function (root) {
  'use strict';
  const categories = [
    ['licence', 'Licence / permission'], ['dates', 'Dates & licence version'],
    ['claimant', 'Claimant / rights administrator'], ['creator', 'Creator / usage facts'],
    ['process', 'Process / legal-risk statements'], ['conflict', 'Conflict / missing evidence'],
  ];
  function category(f) {
    if (['missing', 'conflicting'].includes(f.status)) return 'conflict';
    if (/^(licensee_|creator_|stated_|channel_|video_|monetised|duration|platform_name)/.test(f.key)) return 'creator';
    if (/date|version|governing_terms/.test(f.key)) return 'dates';
    if (/claimant|administrator|licensor_name|sender_address/.test(f.key)) return 'claimant';
    if (/notice_kind|claim_effect|strike|deadline|platform_case/.test(f.key)) return 'process';
    if (/licen[cs]|permitted|excluded|grant|terms|purchase|order_id/.test(f.key)) return 'licence';
    return 'creator';
  }
  // Python offsets count Unicode code points, not JavaScript UTF-16 code units.
  function sourceText(doc, source) {
    const chars = Array.from(doc.lines.join('\n'));
    if (!Number.isInteger(source.char_start) || !Number.isInteger(source.char_end) ||
        source.char_start < 0 || source.char_end <= source.char_start || source.char_end > chars.length) return null;
    return chars.slice(source.char_start, source.char_end).join('');
  }
  function verified(doc, source) {
    return !doc.extraction_failed && source.exact !== false && !!source.quote && sourceText(doc, source) === source.quote;
  }
  function annotations(result, doc) {
    return result.facts.flatMap(f => (f.sources || []).filter(s => s.doc_id === doc.id && verified(doc, s))
      .map(s => ({ ...s, key: f.key, category: category(f), status: f.status })));
  }
  function signal(result) {
    const rules = Object.fromEntries(result.rule_results.map(r => [r.rule_id, r]));
    const r2 = rules.R2, r3 = rules.R3, r4 = rules.R4, r5 = rules.R5;
    let selected;
    // One priority issue; never infer a ready verdict or override an abstention.
    if (result.chosen_step === 'counter_notice' && result.verdict !== 'evidence_ready') {
      const blocker = result.statement.components.find(c => c.status !== 'supported');
      const rule = blocker && blocker.rule_ids.map(id => rules[id]).find(r => r && ['fail', 'unknown'].includes(r.status));
      if (rule) selected = { rule, title: 'A receipt is not the whole sworn statement.',
        why: 'A counter-notice is a sworn statement. The documents still leave part of that statement unsupported or unresolved.',
        keys: ['excluded_use', 'permitted_use', 'grant_statement', ...rule.facts_used] };
    }
    if (!selected && r4?.data.grant_used && r3?.status !== 'pass') selected = {
      rule: r4, title: 'An earlier email makes the difference.',
      why: 'The standard licence alone does not establish this use. The dated permission email supplies the evidence used by the rules.', keys: ['grant_statement', 'email_date'] };
    if (!selected && r2?.status === 'pass' && r2.data.current_version && r2.data.version_in_force && r2.data.current_version !== r2.data.version_in_force) selected = {
      rule: r2, title: 'Today’s terms are not your purchase terms.',
      why: `The governing clause points to ${r2.data.version_in_force}, even though the current terms say ${r2.data.current_version}. Reading only the latest terms can change how your permission looks.`, keys: ['governing_terms_clause', 'licence_version', 'terms_version'] };
    if (!selected && r5?.data.classification === 'licensed_use_conflict') selected = {
      rule: r5, title: 'The claimant is the rights administrator.',
      why: 'A different company name can look like an unrelated claim. Your documents connect this claimant to the licensor’s administration of the work.', keys: ['content_id_administrator_name', 'administrator_name'] };
    if (!selected) return null;
    const sources = selected.keys.flatMap(k => result.facts.filter(f => f.key === k || f.key.startsWith(k + '['))
      .flatMap(f => (f.sources || []).map(s => ({ ...s, key: f.key }))));
    selected.source = sources.find(s => {
      const doc = result.documents.find(d => d.id === s.doc_id);
      return doc && verified(doc, s);
    });
    selected.route = [...result.routes].sort((a, b) => a.rank - b.rank)[0];
    return selected;
  }
  root.NGWorkspace = { categories, category, sourceText, verified, annotations, signal };
  if (typeof module !== 'undefined') module.exports = root.NGWorkspace;
})(typeof window !== 'undefined' ? window : globalThis);
