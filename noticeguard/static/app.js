/* NoticeGuard front end. Vanilla JS, no build step. Talks to /api. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const VERDICT = { evidence_ready: 'Evidence ready', evidence_gap: 'Evidence gap', needs_adviser: 'Needs an adviser' };
  const VCLASS = { evidence_ready: 'ready', evidence_gap: 'gap', needs_adviser: 'adviser' };
  const VICON = { evidence_ready: 'i-check', evidence_gap: 'i-gap', needs_adviser: 'i-person' };
  const STATUS = { supported: ['Supported', 'ready', 'i-check'], not_supported: ['Not supported', 'gap', 'i-gap'], unknown: ['Unknown', 'adviser', 'i-q'] };
  const FSTATUS = { confirmed_by_document: ['Confirmed by document', 'ready', 'i-check'], stated_by_you: ['Stated by you', 'stated', 'i-dot'], missing: ['Missing', 'missing', 'i-ring'], conflicting: ['Conflicting', 'conflicting', 'i-gap'] };
  const STEP = { dispute: 'dispute', appeal: 'appeal', counter_notice: 'counter-notice' };
  const DOC_TYPES = ['claim_notice', 'dispute_response', 'appeal_response', 'removal_notice', 'strike_notice', 'receipt', 'licence_certificate', 'licensor_terms', 'track_page', 'licensor_email', 'video_metadata', 'other'];
  const DOC_LABEL = { claim_notice: 'Claim notice', dispute_response: 'Dispute response', appeal_response: 'Appeal response', removal_notice: 'Removal notice', strike_notice: 'Strike notice', receipt: 'Receipt', licence_certificate: 'Licence certificate', licensor_terms: 'Licensor terms', track_page: 'Track page', licensor_email: 'Licensor email', video_metadata: 'Video export', other: 'Other' };
  const RAIL = [
    { id: 'claim', name: 'Claim', risk: '' },
    { id: 'dispute', name: 'Dispute', risk: 'Claimant can respond with a removal request → strike', step: 'dispute' },
    { id: 'appeal', name: 'Appeal', risk: 'Claimant can respond with a removal request → strike', step: 'appeal' },
    { id: 'removed_with_strike', name: 'Removal + strike', risk: 'Three strikes in 90 days can end the channel' },
    { id: 'counter_notice', name: 'Counter-notice', risk: 'Sworn statement; claimant may sue', step: 'counter_notice' },
  ];
  const STAGE_INDEX = { claim: 0, dispute: 1, appeal: 2, removed_with_strike: 3, unknown: -1 };

  const state = { caseId: null, result: null, files: [], active: null, diff: null };

  // ------------------------------------------------------------------ helpers
  const icon = (id, cls = '') => `<svg class="${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
  const chip = (text, cls, ic) => `<span class="chip ${cls}">${ic ? icon(ic) : ''}${esc(text)}</span>`;
  const vchip = (v, extra = '') => chip(VERDICT[v] || v, VCLASS[v] || 'neutral', VICON[v]) + extra;
  const fmtDate = (iso) => { if (!iso) return ''; const d = new Date(iso + 'T00:00:00'); return isNaN(d) ? iso : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }); };
  const guessType = (name) => { const n = name.toLowerCase(); const t = [[/removal|removed/, 'removal_notice'], [/strike/, 'strike_notice'], [/appeal/, 'appeal_response'], [/dispute/, 'dispute_response'], [/claim/, 'claim_notice'], [/receipt|order/, 'receipt'], [/certificate/, 'licence_certificate'], [/terms/, 'licensor_terms'], [/track/, 'track_page'], [/email|\.eml$/, 'licensor_email'], [/metadata|studio|video/, 'video_metadata']]; for (const [re, ty] of t) if (re.test(n)) return ty; return 'other'; };
  const setLoading = (btn, on) => { if (!btn) return; btn.disabled = on; btn.classList.toggle('loading', on); };
  const stated = () => ({ name: $('#f-name').value, address: $('#f-address').value, phone: $('#f-phone').value, channel_name: $('#f-channel').value, monetised: ($('input[name=monetised]:checked') || {}).value || 'unknown' });
  const abstain = () => ({ fair_use: $('#ab-fair').checked, ownership: $('#ab-own').checked });
  const step = () => ($('input[name=step]:checked') || {}).value || 'dispute';

  async function api(url, opts = {}) {
    const r = await fetch(url, opts);
    let data = null;
    try { data = await r.json(); } catch (e) { /* non-json */ }
    if (!r.ok || (data && data.error)) {
      const err = new Error((data && (data.detail || data.error)) || `${r.status} ${r.statusText}`);
      err.hint = data && data.hint; err.code = data && data.error; throw err;
    }
    return data;
  }

  // ------------------------------------------------------------------ inputs
  function renderFiles() {
    $('#file-list').innerHTML = state.files.map((f, i) => `
      <li class="file">
        <span class="fname" title="${esc(f.file.name)}">${icon('i-doc')} ${esc(f.file.name)}</span>
        <select aria-label="Document type for ${esc(f.file.name)}" data-i="${i}">${DOC_TYPES.map(t => `<option value="${t}" ${t === f.type ? 'selected' : ''}>${DOC_LABEL[t]}</option>`).join('')}</select>
        <button class="rm" type="button" aria-label="Remove ${esc(f.file.name)}" data-rm="${i}">${icon('i-x')}</button>
      </li>`).join('');
    $('#dropzone-text').textContent = state.files.length ? `${state.files.length} file${state.files.length > 1 ? 's' : ''} selected. Add more?` : 'Drop files here or click to choose (.txt, .md, .pdf, .eml)';
  }
  function addFiles(list) { for (const file of list) state.files.push({ file, type: guessType(file.name) }); renderFiles(); }
  $('#file-input').addEventListener('change', (e) => { addFiles(e.target.files); e.target.value = ''; });
  $('#file-list').addEventListener('change', (e) => { const s = e.target.closest('select'); if (s) state.files[+s.dataset.i].type = s.value; });
  $('#file-list').addEventListener('click', (e) => { const b = e.target.closest('[data-rm]'); if (b) { state.files.splice(+b.dataset.rm, 1); renderFiles(); } });
  const dz = $('#dropzone');
  ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('over'); }));
  dz.addEventListener('drop', (e) => addFiles(e.dataTransfer.files));

  function fillStated(s, st) {
    $('#f-name').value = s.name || ''; $('#f-address').value = s.address || ''; $('#f-phone').value = s.phone || ''; $('#f-channel').value = s.channel_name || '';
    const m = $(`input[name=monetised][value="${s.monetised || 'unknown'}"]`); if (m) m.checked = true;
    const sp = $(`input[name=step][value="${st}"]`); if (sp) sp.checked = true;
  }

  // ------------------------------------------------------------------ actions
  async function analyse() {
    if (!state.files.length) { showError('Add at least one document first.', 'The claim notice is the minimum; the licence and receipt make the check meaningful.'); return; }
    const fd = new FormData();
    state.files.forEach(f => fd.append('files', f.file, f.file.name));
    fd.append('doc_types', JSON.stringify(state.files.map(f => f.type)));
    fd.append('stated', JSON.stringify(stated())); fd.append('step', step());
    fd.append('abstain_flags', JSON.stringify(abstain())); fd.append('notes', $('#f-notes').value);
    setLoading($('#btn-analyse'), true); showSkeleton();
    try { const d = await api('/api/cases', { method: 'POST', body: fd }); state.files = []; renderFiles(); setResult(d.case_id, d.result, null); }
    catch (e) { showError(e.message, e.hint); } finally { setLoading($('#btn-analyse'), false); }
  }
  async function loadDemo(name) {
    const btn = $(`#btn-${name}`); setLoading(btn, true); showSkeleton();
    try { const d = await api(`/api/demo/${name}`); fillStated(d.result.stated, d.result.chosen_step); $('#f-notes').value = name === 'leo' ? "I paid for this, I'm obviously right, just write it" : ''; setResult(d.case_id, d.result, null); }
    catch (e) { showError(e.message, e.hint); } finally { setLoading(btn, false); }
  }
  async function rerun() {
    if (!state.caseId) return;
    setLoading($('#btn-rerun'), true);
    try { const d = await api(`/api/cases/${state.caseId}/step`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ step: step(), stated: stated(), abstain_flags: abstain() }) }); setResult(d.case_id, d.result, d.diff); }
    catch (e) { showError(e.message, e.hint); } finally { setLoading($('#btn-rerun'), false); }
  }
  async function addDocuments(files, types) {
    if (!state.caseId || !files.length) return;
    const fd = new FormData();
    Array.from(files).forEach((f, i) => { fd.append('files', f, f.name); });
    fd.append('doc_types', JSON.stringify(types || Array.from(files).map(f => guessType(f.name))));
    try { const d = await api(`/api/cases/${state.caseId}/documents`, { method: 'POST', body: fd }); setResult(d.case_id, d.result, d.diff); }
    catch (e) { showError(e.message, e.hint); }
  }
  $('#add-input').addEventListener('change', async (e) => { const files = e.target.files; await addDocuments(files); e.target.value = ''; });
  $('#btn-leo-email').addEventListener('click', async () => {
    const btn = $('#btn-leo-email'); setLoading(btn, true);
    try { const files = await api('/api/demo-files/leo_email'); const blobs = files.map(f => new File([f.text], f.filename, { type: 'message/rfc822' })); await addDocuments(blobs, blobs.map(() => 'licensor_email')); btn.hidden = true; }
    catch (e) { showError(e.message, e.hint); } finally { setLoading(btn, false); }
  });
  $('#btn-analyse').addEventListener('click', analyse);
  $('#btn-rerun').addEventListener('click', rerun);
  $('#btn-maya').addEventListener('click', () => loadDemo('maya'));
  $('#btn-leo').addEventListener('click', () => loadDemo('leo'));
  document.addEventListener('click', (e) => { const b = e.target.closest('[data-demo]'); if (b) loadDemo(b.dataset.demo); });

  // ------------------------------------------------------------------ rendering
  function showSkeleton() { $('#centre').innerHTML = `<div class="skeleton" aria-busy="true"><div class="bar h"></div><div class="bar" style="width:70%"></div><div class="bar" style="width:55%"></div><div class="bar" style="width:80%"></div></div>`; }
  function showError(msg, hint) { const c = $('#centre'); c.insertAdjacentHTML('afterbegin', `<div class="error" role="alert"><b>${esc(msg)}</b>${hint ? esc(hint) : ''}</div>`); const s = $('.skeleton', c); if (s) s.remove(); }

  function setResult(caseId, result, diff) {
    state.caseId = caseId; state.result = result; state.diff = diff; state.active = null;
    render(); renderChainEmpty();
    $('#btn-rerun').hidden = false; $('#case-panel').hidden = false;
    const hasEmail = result.documents.some(d => d.doc_type === 'licensor_email');
    $('#btn-leo-email').hidden = !(result.documents.some(d => d.filename === '01_claim_notice.txt' && result.stage === 'removed_with_strike') && !hasEmail);
    $('#foot-meta').textContent = `Rules version ${result.rules_version} · ${result.llm.provider || ''} ${result.llm.model || ''} · ${result.llm.cached_calls} cached / ${result.llm.live_calls} live LLM calls`;
  }

  function render() {
    const r = state.result;
    renderRail(r);
    renderCaseDocs(r);
    const chosenRoute = r.routes.find(x => x.is_chosen_step) || r.routes.find(x => x.step === r.chosen_step);
    const heading = r.verdict === 'evidence_ready' ? `Evidence ready for: <em>${esc(chosenRoute ? chosenRoute.title : STEP[r.chosen_step])}</em>` : r.verdict === 'evidence_gap' ? `Evidence gap <em>for a ${STEP[r.chosen_step]}</em>` : `Needs an adviser <em>before a ${STEP[r.chosen_step]}</em>`;
    const sentences = splitSentences(r.verdict_explanation);
    const nLead = r.verdict === 'evidence_gap' ? 2 : 1;
    const lead = sentences.slice(0, nLead).join(' ');
    const rest = sentences.slice(nLead).join(' ');
    document.body.dataset.verdict = VCLASS[r.verdict];
    const comps = r.statement.components.map(c => { const [t, cls, ic] = STATUS[c.status]; return `
      <li class="component clickable" data-sid="${esc(c.sentence_id)}" tabindex="0" role="button">
        <span>${chip(t, cls, ic)}</span>
        <div><div class="lbl">${esc(c.label)}</div><div class="why">${esc(c.explanation)}</div></div>
      </li>`; }).join('');
    const routes = r.routes.map(x => `
      <li class="route clickable" data-sid="${esc(x.sentence_id)}" tabindex="0" role="button">
        <span class="n">${x.rank}</span>
        <div><h3>${esc(x.title)}</h3><p>${esc(x.description)}</p>${x.is_chosen_step ? '<div class="tag">The step you chose</div>' : x.step ? '' : '<div class="tag">No platform process started</div>'}</div>
        ${vchip(x.evidence_status)}
      </li>`).join('');
    const gaps = r.gap_fixes.length ? `
      <section class="section"><h2>${r.verdict === 'needs_adviser' ? 'What would help an adviser' : 'What would close this gap'}</h2>
      <ul class="gaps">${r.gap_fixes.map(g => { const comp = r.statement.components.find(c => c.id === g.component); return `
        <li class="gapfix clickable" data-sid="${esc(g.sentence_id)}" tabindex="0" role="button">
          <div class="need">${esc(g.needed)}</div>
          <div class="how">${esc(g.how_to_get)}${comp ? ` <span class="muted">· for “${esc(comp.label)}”</span>` : ''}</div>
          ${g.example_document_types.length ? `<div class="types">${g.example_document_types.map(t => chip(DOC_LABEL[t] || t, 'doc', 'i-doc')).join('')}</div>` : ''}
        </li>`; }).join('')}</ul></section>` : '';
    const draft = r.draft ? renderDraft(r.draft) : (r.verdict === 'evidence_ready' ? '' : `
      <section class="section"><h2>Draft</h2><p class="lede">A draft is prepared only when every component of the statement is confirmed by your documents. ${r.verdict === 'evidence_gap' ? 'Close the gap above and re-check.' : 'An adviser should look at this first.'}</p></section>`);
    const rejected = renderRejected(r);
    const diff = state.diff && state.diff.verdict_before !== 'none' ? `
      <div class="diff" role="status"><h3>What changed</h3><p>${esc(state.diff.summary)}</p>
        <div class="move">${vchip(state.diff.verdict_before)}<span class="muted">→</span>${vchip(state.diff.verdict_after)}</div>
        ${state.diff.changed_rule_results.length ? `<ul>${state.diff.changed_rule_results.map(c => `<li><strong>${esc(c.rule_id)} ${esc(c.rule_name)}</strong>: ${esc(c.before.replace(/_/g, ' '))} → ${esc(c.after)}. ${esc(c.explanation)}</li>`).join('')}</ul>` : ''}
      </div>` : '';
    $('#centre').innerHTML = `
      ${diff}
      <section class="section">
        <div class="slab ${VCLASS[r.verdict]} enter">
          <div class="headline"><span class="glyph" role="img" aria-label="${esc(VERDICT[r.verdict])}">${icon(VICON[r.verdict])}</span><h1>${heading}</h1></div>
          <p class="expl sentence clickable" data-sid="verdict" tabindex="0" role="button">${esc(lead)}</p>
          <div class="meta"><span>Stage: ${esc(stageName(r.stage))}</span><span>·</span><span>Step checked: ${esc(STEP[r.chosen_step])}</span><span>·</span><span>Rules v${esc(r.rules_version)}</span>${r.notes_ignored ? '<span>·</span><span>Your notes were not read</span>' : ''}</div>
        </div>
        ${rest ? `<p class="why"><span class="sentence" data-sid="verdict" tabindex="0" role="button">${esc(rest)}</span></p>` : ''}
      </section>
      <section class="section"><h2>The claim in plain language</h2>
        <ul class="claim-list prose">${r.claim_summary.map(s => `<li><span class="sentence" data-sid="${esc(s.id)}" tabindex="0" role="button">${esc(s.text)}</span></li>`).join('')}</ul>
      </section>
      <section class="section"><h2>The statement you would be making</h2>
        <p class="lede">In a ${STEP[r.chosen_step]} you would be saying this. Each part is checked separately.</p>
        <blockquote class="statement">“${esc(r.statement.text)}”</blockquote>
        <ul class="components">${comps}</ul>
        ${r.statement.consequence ? `<div class="consequence"><h3>${r.chosen_step === 'counter_notice' ? 'If you file this' : r.chosen_step === 'appeal' ? 'If you appeal' : 'If you dispute'}</h3>${esc(r.statement.consequence)}</div>` : ''}
      </section>
      <section class="section"><h2>Evidence</h2>
        <p class="lede">Confirmed by document means the documents are consistent with each other. NoticeGuard has not checked that they are authentic. Hover a row for the quote; click for the chain.</p>
        ${renderEvidence(r)}
      </section>
      <section class="section"><h2>Routes, lowest risk first</h2><ol class="routes">${routes}</ol></section>
      ${gaps}
      ${draft}
      ${rejected}`;
    bindSentences();
  }

  const splitSentences = (text) => (text || '').split(/(?<=[.!?][”"’]?)\s+(?=[A-Z“("])/).map(x => x.trim()).filter(Boolean);
  const stageName = (s) => ({ claim: 'Claim', dispute: 'Dispute rejected', appeal: 'Appeal', removed_with_strike: 'Removed with strike', unknown: 'Unknown' }[s] || s);

  function renderRail(r) {
    if (!r) {
      $('#rail').innerHTML = RAIL.map(n => `<div class="stage idle"><span class="dot"></span><div class="name">${esc(n.name)}</div>${n.risk ? `<div class="risk">${esc(n.risk)}</div>` : ''}</div>`).join('');
      return;
    }
    const cur = STAGE_INDEX[r.stage];
    const se = Object.fromEntries((r.step_evidence || []).map(s => [s.step, s]));
    $('#rail').innerHTML = RAIL.map((n, i) => {
      const cls = i < cur ? 'past' : i === cur ? 'current' : 'future';
      const ev = n.step && se[n.step];
      let chips = '';
      if (ev) {
        const suffix = ev.available ? '' : i > cur ? ' when reached' : ' (stage passed)';
        chips = `<div class="chips">${chip(VERDICT[ev.evidence_status] + suffix, VCLASS[ev.evidence_status] + (ev.available ? '' : ' unavail'), VICON[ev.evidence_status])}</div>`;
      }
      return `<div class="stage ${cls}"><span class="dot"></span><div class="name">${esc(n.name)}</div>${i === cur ? '<span class="here">You are here</span>' : ''}${(i > cur && n.risk) ? `<div class="risk">${esc(n.risk)}</div>` : ''}${chips}</div>`;
    }).join('');
    const dl = $('#deadlines');
    if (r.deadlines && r.deadlines.length) {
      dl.hidden = false;
      dl.innerHTML = r.deadlines.map(d => `<span class="dl sentence" data-sid="${esc(d.sentence_id)}" tabindex="0" role="button">${esc(d.label)}: <b>${esc(fmtDate(d.date))}</b> · ${d.days_remaining >= 0 ? `${d.days_remaining} day${d.days_remaining === 1 ? '' : 's'} remaining` : `passed ${-d.days_remaining} day${d.days_remaining === -1 ? '' : 's'} ago`}${d.doc_filename ? ` <span class="muted">· ${esc(d.doc_filename)}</span>` : ''}</span>`).join('');
    } else { dl.hidden = true; dl.innerHTML = ''; }
  }

  function renderCaseDocs(r) {
    $('#case-docs').innerHTML = r.documents.map(d => `<div class="casedoc"><span>${icon('i-doc')} ${esc(d.filename)}${d.extraction_failed ? ' <span class="chip conflicting">extraction rejected</span>' : ''}</span><span class="t">${esc(DOC_LABEL[d.doc_type] || d.doc_type)} · ${d.n_facts} span${d.n_facts === 1 ? '' : 's'}</span></div>`).join('');
  }

  const GROUPS = [
    ['Key dates', (f) => f.group === 'dates' || /_date$/.test(f.key)],
    ['The claim', (f) => /^(platform_case_id|claimant_name|claimant_contact|matched_work_title|matched_segment|notice_kind|claim_effect|strike_count|video_id|video_title|channel_name|platform_name|duration|monetised_on_publish)$/.test(f.key)],
    ['Your licence', (f) => /^(licence_|licensed_|licensee_|licensor_|purchased_|order_id|terms_version|work_title|content_id_administrator_name|administrator_name|sender_address|grant_statement|granted_|ticket_ref|governing_terms_clause|administrator_clause)/.test(f.key)],
    ['Clauses', (f) => f.group === 'clauses' || /^(permitted_use|excluded_use)/.test(f.key)],
    ['Stated by you', (f) => f.status === 'stated_by_you' || /^stated_/.test(f.key)],
    ['Other', () => true],
  ];
  function renderEvidence(r) {
    const rr = Object.fromEntries(r.rule_results.map(x => [x.rule_id, x]));
    const vif = rr.R2 && rr.R2.data && rr.R2.data.version_in_force;
    const facts = r.facts.slice();
    const rows = [];
    const used = new Set();
    for (const [name, pred] of GROUPS) {
      const items = facts.filter(f => !used.has(f) && pred(f));
      items.forEach(f => used.add(f));
      if (name === 'Key dates') {
        // fixed order for the key dates, plus the licence version in force
        const order = ['purchase_date', 'issue_date', 'licence_version', 'publish_date', 'monetisation_start_date', 'claim_date', 'strike_date', 'email_date', 'effective_date', 'deadline_date'];
        items.sort((a, b) => (order.indexOf(a.key) + 1 || 99) - (order.indexOf(b.key) + 1 || 99) || String(a.value).localeCompare(String(b.value)));
        const lv = facts.find(f => f.key === 'licence_version');
        if (lv && !items.includes(lv)) { items.splice(1, 0, lv); used.add(lv); }
      }
      if (!items.length) continue;
      rows.push(`<tr class="group"><td colspan="4">${esc(name)}</td></tr>`);
      for (const f of items) {
        const [t, cls, ic] = FSTATUS[f.status] || [f.status, 'neutral'];
        const src = f.sources && f.sources[0];
        const srcText = src ? `${src.doc_filename}${src.clause_ref ? ` · clause ${src.clause_ref}` : ` · line ${src.line_start}`}${f.sources.length > 1 ? ` +${f.sources.length - 1}` : ''}` : (f.status === 'stated_by_you' ? 'About you form' : '—');
        let val = f.value === true ? 'yes' : f.value === false ? 'no' : f.value == null ? '—' : String(f.value);
        if (/_date$/.test(f.key) && f.status !== 'conflicting') val = fmtDate(val);
        let label = f.key.replace(/\[.*\]$/, '').replace(/_/g, ' ');
        if (f.key === 'licence_version' && vif) label = `licence version (in force: ${vif})`;
        if (/^(permitted_use|excluded_use)/.test(f.key)) { const m = f.key.match(/\[(.*)\]/); label = `${f.key.startsWith('permitted') ? 'permitted use' : 'excluded use'} ${m ? m[1] : ''}`; val = src ? src.quote : val; }
        const q = src && !/^(permitted_use|excluded_use)/.test(f.key) ? `<span class="q">“${esc(src.context || src.quote)}”</span>` : '';
        const note = f.note ? `<span class="q">${esc(f.note)}</span>` : '';
        rows.push(`<tr class="row" data-sid="fact:${esc(f.key)}" tabindex="0"><td class="key">${esc(label)}</td><td class="val">${esc(val)}${q}${note}</td><td>${chip(t, cls, ic)}</td><td class="src">${esc(srcText)}</td></tr>`);
      }
    }
    return `<div class="table-wrap"><table class="evidence"><thead><tr><th>Fact</th><th>Value</th><th>Status</th><th>Source</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }

  function renderDraft(d) {
    if (d.withheld_reason) return `<section class="section"><h2>Draft</h2><div class="draft"><div class="withheld">${esc(d.withheld_reason)}</div><p class="foot">The post-check found a detail in the draft that is not in the confirmed fact table, so the draft was not shown. Checked tokens: ${esc(d.post_check.checked_tokens.join(', '))}.</p></div></section>`;
    const body = d.sentences.map(s => { const text = s.text.replace(/\s*\[([^\]]+)\]/g, (m, c) => `<span class="cite">${esc(c)}</span>`); return `<p class="sentence" data-sid="${esc(s.id)}" tabindex="0" role="button">${text}</p>`; }).join('');
    return `<section class="section"><h2>${d.kind === 'counter_notice' ? 'Counter-notice draft' : d.kind === 'appeal' ? 'Appeal draft' : 'Dispute draft'}</h2>
      <p class="lede">Prepared for your review from the confirmed facts only. Every line clicks through to its source. NoticeGuard never submits anything.</p>
      <div class="draft"><div class="head"><p class="hdr">${esc(d.header)}</p><button class="btn on-dark sm" type="button" id="btn-copy">${icon('i-copy')} Copy draft</button></div>
        <div class="body">${body}</div>
        <p class="foot">Post-check: ${d.post_check.passed ? 'passed' : 'failed'} · ${d.post_check.checked_tokens.length} dates, IDs, clause references and names checked against the fact table${d.smoothed ? ' · prose smoothed by the model and re-checked' : ''}.</p>
      </div></section>`;
  }

  function renderRejected(r) {
    const items = r.rejected_facts || [];
    return `<section class="section"><details class="rejected"><summary>Rejected extractions (${items.length})</summary>
      <p class="muted small" style="margin-top:6px">Spans the model tagged that were dropped: tags outside the tag set, empty spans, or a whole output rejected because the model changed the document text. Nothing here reached the rules.</p>
      ${items.length ? `<ul>${items.map(x => `<li><strong>${esc(x.doc_filename)}</strong> · ${esc(x.type)}${x.quote ? ` · “${esc(x.quote.slice(0, 120))}”` : ''} — ${esc(x.reason)}</li>`).join('')}</ul>` : '<p class="muted small" style="margin-top:6px">None for this case: every tagged span round-tripped and was in the tag set.</p>'}
    </details></section>`;
  }

  // ------------------------------------------------------------------ chain
  function bindSentences() {
    const open = (el) => { const sid = el.dataset.sid; if (!sid) return; $$('.active').forEach(x => x.classList.remove('active')); el.classList.add('active'); state.active = sid; renderChain(sid); };
    $$('[data-sid]').forEach(el => {
      el.addEventListener('click', () => open(el));
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(el); } });
    });
    const copy = $('#btn-copy');
    if (copy) copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(state.result.draft.header + '\n\n' + state.result.draft.text); copy.innerHTML = `${icon('i-check')} Copied`; copy.classList.add('copied'); setTimeout(() => { copy.innerHTML = `${icon('i-copy')} Copy draft`; copy.classList.remove('copied'); }, 1800); } catch (e) { copy.textContent = 'Copy failed: select the text instead'; } });
  }

  function renderChainEmpty() { $('#chain').innerHTML = `<div class="chain-empty"><h2>Reasoning chain</h2><p>Click any sentence, badge, table row or draft line to see the chain behind it: Document → Quote → Fact → Fact → Rule → Status.</p></div>`.replace('Fact → Fact', 'Fact'); }

  function docView(doc, f) {
    const text = doc.lines.join('\n');
    const s = f.char_start, e = f.char_end;
    const before = text.slice(0, s), mid = text.slice(s, e), after = text.slice(e);
    const html = esc(before) + '<mark class="pulse" id="chain-mark">' + esc(mid) + '</mark>' + esc(after);
    const lines = html.split('\n');
    return `<div class="docview" role="region" aria-label="Document text with the quote highlighted">${lines.map((l, i) => `<div class="ln" ${i + 1 === f.line_start ? 'id="chain-line"' : ''}><span class="n">${i + 1}</span><span>${l || ' '}</span></div>`).join('')}</div>`;
  }

  function renderChain(sid) {
    const r = state.result; const node = r.chain[sid];
    const el = $('#chain');
    if (!node) { el.innerHTML = `<div class="chain-empty"><h2>Reasoning chain</h2><p>No chain recorded for this item.</p></div>`; return; }
    const docs = Object.fromEntries(r.documents.map(d => [d.id, d]));
    const withQuote = node.facts.filter(f => f.doc_id && f.quote).map((f, i) => [f, i]).sort((a, b) => ((b[0].clause_ref ? 1 : 0) - (a[0].clause_ref ? 1 : 0)) || (a[1] - b[1])).map(x => x[0]);
    const primary = withQuote[0];
    const byDoc = new Map();
    withQuote.forEach(f => { if (!byDoc.has(f.doc_id)) byDoc.set(f.doc_id, []); byDoc.get(f.doc_id).push(f); });
    const docStep = primary ? `
      <div class="step"><div class="k">Document</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">${Array.from(byDoc.keys()).map(id => chip(docs[id] ? docs[id].filename : id, 'doc', 'i-doc')).join('')}</div>
      </div>
      <div class="step"><div class="k">Quote</div>
        <p class="sentence-text" style="font-style:italic">“${esc(primary.quote)}”</p>
        <p class="muted small" style="margin-top:4px">${esc(docs[primary.doc_id] ? docs[primary.doc_id].filename : '')}, line ${primary.line_start}${primary.clause_ref ? `, clause ${esc(primary.clause_ref)}` : ''}${withQuote.length > 1 ? ` · ${withQuote.length - 1} more quote${withQuote.length > 2 ? 's' : ''} below` : ''}</p>
        ${docs[primary.doc_id] ? docView(docs[primary.doc_id], primary) : ''}
      </div>` : `<div class="step"><div class="k">Document</div><p class="muted small">No document quote is behind this item${node.facts.some(f => f.status === 'stated_by_you') ? ': it rests on fields you typed in the form (Stated by you)' : node.facts.some(f => f.status === 'missing') ? ': the fact is missing' : ''}.</p></div>`;
    const factsStep = node.facts.length ? `
      <div class="step"><div class="k">Fact${node.facts.length > 1 ? 's' : ''}</div>
        ${node.facts.map(f => { const [t, cls, ic] = FSTATUS[f.status] || [f.status, 'neutral']; const v = f.value === true ? 'yes' : f.value === false ? 'no' : f.value == null ? '—' : String(f.value); return `<div class="factrow"><div><div class="fk">${esc(f.fact_key)}${f.doc_filename ? ` · ${esc(f.doc_filename)}${f.clause_ref ? ` §${esc(f.clause_ref)}` : f.line_start ? ` L${f.line_start}` : ''}` : ''}</div><div class="fv">${esc(v.length > 160 ? v.slice(0, 157) + '…' : v)}</div></div>${chip(t, cls, ic)}</div>`; }).join('')}
      </div>` : '';
    const ruleStep = node.rule_id ? `
      <div class="step"><div class="k">Rule</div>
        <div class="rule-card"><div class="rid">${esc(node.rule_id)} · ${esc(node.rule_name)}</div><div class="logic">${esc(node.rule_logic || '')}</div>
        <p style="margin-top:8px">${esc((r.rule_results.find(x => x.rule_id === node.rule_id) || {}).explanation || '')}</p></div>
      </div>` : '';
    const maps = node.mapping_runs && node.mapping_runs.length ? `
      <div class="step"><div class="k">Mapping, 3 runs</div>
        <div class="votes">${node.mapping_runs.map(m => `<div class="vote"><div class="q">“${esc(m.clause_quote.length > 180 ? m.clause_quote.slice(0, 177) + '…' : m.clause_quote)}”</div>
          <div class="muted small" style="margin-top:3px">${esc(m.question.replace(/_/g, ' '))}${m.clause_ref ? ` · clause ${esc(m.clause_ref)}` : ''} · result: <strong>${esc(m.result)}</strong></div>
          <div class="runs">${m.answers.map(a => `<span class="${esc(a.covers)}" title="${esc(a.reason)}">${esc(a.covers)}</span>`).join('')}</div>
          ${m.answers.map(a => `<div class="reason">${esc(a.covers)}: ${esc(a.reason)}</div>`).join('')}</div>`).join('')}
      </div>` : '';
    const statusWord = node.status ? (VERDICT[node.status] || (STATUS[node.status] || [])[0] || (FSTATUS[node.status] || [])[0] || node.status.replace(/_/g, ' ')) : '';
    const statusCls = VCLASS[node.status] || (STATUS[node.status] || [])[1] || (FSTATUS[node.status] || [])[1] || (node.rule_status === 'pass' ? 'ready' : node.rule_status === 'fail' ? 'gap' : node.rule_status === 'unknown' ? 'adviser' : 'neutral');
    el.innerHTML = `<div class="chain">
      <div class="step"><div class="k">Sentence</div><p class="sentence-text">${esc(node.text)}</p></div>
      ${docStep}${factsStep}${ruleStep}${maps}
      <div class="step"><div class="k">Status</div>${statusWord ? chip(statusWord, statusCls, VICON[node.status] || (STATUS[node.status] || [])[2] || (FSTATUS[node.status] || [])[2]) : ''}${node.rule_status ? ` <span class="chip neutral">rule ${esc(node.rule_id)}: ${esc(node.rule_status.replace(/_/g, ' '))}</span>` : ''}</div>
      <div class="version">Rules version ${esc(r.rules_version)} · Confirmed by document, never verified.</div>
    </div>`;
    const line = $('#chain-line'); const box = line && line.closest('.docview'); if (line && box) box.scrollTop = Math.max(0, line.offsetTop - box.clientHeight / 2);
  }

  renderRail(null);
  $('#foot-more').addEventListener('click', () => { const f = $('#foot'); const open = f.classList.toggle('open'); $('#foot-more').textContent = open ? 'Less' : 'More'; $('#foot-more').setAttribute('aria-expanded', String(open)); });

  // deep-link demo: /?demo=maya
  const params = new URLSearchParams(location.search);
  if (params.get('demo')) loadDemo(params.get('demo')).then(() => { const o = params.get('open'); if (o) { const el = document.querySelector(`[data-sid="${CSS.escape(o)}"]`); if (el) el.click(); } });
})();
