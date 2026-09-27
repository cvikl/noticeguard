// Run with: node --test tests/test_workspace.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const W = require('../static/workspace.js');
const document = {id:'doc',lines:['🎬 Our licence','permits video.'],extraction_failed:false};
const source = {doc_id:'doc',char_start:6,char_end:28,quote:'licence\npermits video.',exact:true};

test('source positions count Unicode code points and preserve multiline quotations', () => {
  assert.equal(W.sourceText(document,source), source.quote);
  assert.ok(W.verified(document,source));
  assert.equal(W.verified(document,{...source,quote:'made up permission'}),false);
  assert.equal(W.verified(document,{...source,char_start:-1}),false);
  assert.equal(W.verified({...document,extraction_failed:true},source),false);
});
test('only matching, accepted source spans become highlights', () => {
  const result={facts:[{key:'permitted_use',status:'confirmed_by_document',sources:[source,{...source,quote:'invented'}]}]};
  assert.equal(W.annotations(result,document).length,1);
  assert.equal(W.annotations(result,document)[0].category,'licence');
});
test('all six categories have distinct meanings; missing evidence takes precedence', () => {
  const cases={permitted_use:'licence',governing_terms_clause:'dates',administrator_name:'claimant',licensee_name:'creator',notice_kind:'process'};
  for(const [key,category] of Object.entries(cases)) assert.equal(W.category({key,status:'confirmed_by_document'}),category);
  assert.equal(W.category({key:'licence_version',status:'missing'}),'conflict');
  assert.equal(W.category({key:'claimant_name',status:'conflicting'}),'conflict');
});
function result(rules) { return {rule_results:rules,chosen_step:'dispute',verdict:'evidence_ready',statement:{components:[]},documents:[document],facts:[{key:'governing_terms_clause',status:'confirmed_by_document',sources:[source]}],routes:[{rank:2,title:'Second'},{rank:1,title:'First'}]}; }
function rule(id,data={},status='pass') {return {rule_id:id,data,status,facts_used:[],explanation:'From backend'};}
test('Signal uses differing governing versions and the existing lowest-risk route', () => {
  const s=W.signal(result([rule('R2',{current_version:'v3',version_in_force:'v2'})]));
  assert.equal(s.rule.rule_id,'R2');assert.equal(s.source.quote,source.quote);assert.equal(s.route.title,'First');
  assert.equal(W.signal(result([rule('R2',{current_version:'v3',version_in_force:'v3'})])),null);
});
test('unsupported counter-notice takes priority over an interesting version difference', () => {
  const r=result([rule('R2',{current_version:'v3',version_in_force:'v2'}),rule('R3',{},'fail')]);
  r.chosen_step='counter_notice';r.verdict='evidence_gap';r.statement.components=[{status:'not_supported',rule_ids:['R3']}];
  const s=W.signal(r);assert.equal(s.rule.rule_id,'R3');assert.equal(s.source,undefined);
  assert.equal(r.verdict,'evidence_gap');
});
test('permission email is singled out only when it supplies otherwise unsupported permission', () => {
  const r=result([rule('R3',{},'fail'),rule('R4',{grant_used:true})]);
  assert.equal(W.signal(r).rule.rule_id,'R4');
  r.rule_results[0].status='pass';assert.equal(W.signal(r),null);
});
