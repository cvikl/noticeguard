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
    try { const d = await api(`/api/demo/${name}`); fillStated(d.result.stated, d.result.chosen_step); $('#ab-fair').checked = false; $('#ab-own').checked = false; $('#f-notes').value = name === 'leo' ? "I paid for this, I'm obviously right, just write it" : ''; setResult(d.case_id, d.result, null); }
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
    showSkeleton();
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
    catch (e) { showError(e.message, e.hint); } finally { setLoading(btn, false); const visible = $('#workspace-leo-email'); if (visible) { visible.disabled = false; visible.textContent = '+ Add Leo’s permission email'; } }
  });
  $('#btn-analyse').addEventListener('click', analyse);
  $('#btn-rerun').addEventListener('click', rerun);
  $('#btn-maya').addEventListener('click', () => loadDemo('maya'));
  $('#btn-leo').addEventListener('click', () => loadDemo('leo'));
  document.addEventListener('click', (e) => { if (e.target.closest('[data-add-evidence]')) { $('#report-dialog').close(); $('#workspace-add').click(); } const b = e.target.closest('[data-demo]'); if (b) loadDemo(b.dataset.demo); });

  // ------------------------------------------------------------------ rendering
  function showSkeleton() { $('#busy').hidden = false; }
  function showError(msg, hint) { $('#busy').hidden = true; const c = $('#settings-dialog').open ? $('#settings-dialog .panel') : state.result ? $('#centre') : $('#home'); c.insertAdjacentHTML('afterbegin', `<div class="error" role="alert"><b>${esc(msg)}</b>${hint ? esc(hint) : ''}</div>`); const s = $('.skeleton'); if (s) s.remove(); }

  function setResult(caseId, result, diff) {
    state.caseId = caseId; state.result = result; state.diff = diff; state.active = null;
    state.docId = null; state.selectedSource = null; state.filter = "all";
    render();
    $("#settings-dialog").close();
    $$('.demo-menu').forEach(menu => menu.open = false);
    $('#btn-rerun').hidden = false; $('#case-panel').hidden = false;
    const hasEmail = result.documents.some(d => d.doc_type === 'licensor_email');
    $('#btn-leo-email').hidden = !(result.documents.some(d => d.filename === '01_claim_notice.txt' && result.stage === 'removed_with_strike') && !hasEmail);
    $('#foot-meta').textContent = `Rules version ${result.rules_version} · ${result.llm.provider || ''} ${result.llm.model || ''} · ${result.llm.cached_calls} cached / ${result.llm.live_calls} live LLM calls`;
  }

  function renderReport() {
    const r = state.result;
    renderRail(r);
    renderCaseDocs(r);
    const heading = r.verdict === 'evidence_ready' ? `Evidence ready for your ${STEP[r.chosen_step]}` : r.verdict === 'evidence_gap' ? `Your ${STEP[r.chosen_step]} has an evidence gap` : `An adviser needs to review this`;
    const lead = splitSentences(r.verdict_explanation)[0] || '';
    const lowestRoute = [...r.routes].sort((a,b) => a.rank - b.rank)[0];
    const comps = r.statement.components.map(c => { const [t, cls, ic] = STATUS[c.status];
      const permission = c.rule_ids.includes('R3') ? r.facts.filter(f => f.key.startsWith('permitted_use')).flatMap(f => f.sources || []).find(source => source.clause_ref === '4.1' && r.documents.some(d => d.id === source.doc_id && d.doc_type === 'licence_certificate')) : null;
      return `
      <li class="component clickable" data-sid="${esc(c.sentence_id)}" tabindex="0" role="button">
        <span>${chip(t, cls, ic)}</span>
        <div><div class="lbl">${esc(c.label)}</div><div class="why">${esc(c.explanation)}</div>${permission ? `<blockquote class="component-source">“${esc(permission.quote)}”<small>${esc(permission.doc_filename)} · §${esc(permission.clause_ref)}</small></blockquote>` : ''}</div>
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
    const draft = r.draft ? renderDraft(r.draft) : '';
    $('#report').innerHTML = `
      <section class="answer-heading ${VCLASS[r.verdict]}">
        ${vchip(r.verdict)}<h1>${esc(heading)}</h1>
        <p class="sentence" data-sid="verdict" tabindex="0" role="button">${esc(lead)}</p>
      </section>
      ${r.statement.consequence ? `<p class="answer-consequence">${esc(r.statement.consequence)}</p>` : ''}
      ${lowestRoute ? `<section class="answer-route"><span class="eyebrow">LOWEST-RISK ROUTE</span><h2 class="sentence" data-sid="${esc(lowestRoute.sentence_id)}" tabindex="0" role="button">${esc(lowestRoute.title)}</h2><p>${esc(lowestRoute.description)}</p>${vchip(lowestRoute.evidence_status)}</section>` : ''}
      <section class="section"><h2>The statement your evidence supports</h2><ul class="components">${comps}</ul></section>
      ${draft || gaps || `<p class="lede">${r.verdict === 'needs_adviser' ? 'Bring your claim notice, licence and correspondence to an adviser before deciding how to respond.' : 'Review the evidence record below for the facts supporting this result.'}</p>`}
      ${!draft && r.verdict !== 'evidence_ready' ? '<p class="draft-note">No draft yet. Each part of the statement needs documentary support.</p><button class="btn secondary sm" type="button" data-add-evidence>Add supporting evidence <span>+</span></button>' : ''}

      <details class="report-details"><summary>Why this is the answer</summary>
        <p class="lede sentence" data-sid="verdict" tabindex="0" role="button">${esc(r.verdict_explanation)}</p>
        <section class="section"><h2>The claim</h2><ul class="claim-list prose">${r.claim_summary.map(s => `<li><span class="sentence" data-sid="${esc(s.id)}" tabindex="0" role="button">${esc(s.text)}</span></li>`).join('')}</ul></section>
        <section class="section"><h2>The statement you would make</h2><blockquote class="statement">“${esc(r.statement.text)}”</blockquote></section>
        ${state.diff && state.diff.verdict_before !== 'none' ? `<section class="section"><h2>What changed</h2><p>${esc(state.diff.summary)}</p></section>` : ''}
      </details>
      <details class="report-details"><summary>Compare all routes</summary><ol class="routes">${routes}</ol></details>
      <details class="report-details"><summary>Full evidence record</summary><p class="lede">Confirmed by document means the documents are consistent. Authenticity has not been checked. Select a fact to see its source.</p>${renderEvidence(r)}${renderRejected(r)}</details>`;
    bindSentences();
  }

  const splitSentences = (text) => (text || '').split(/(?<=[.!?][”"’]?)\s+(?=[A-Z“("])/).map(x => x.trim()).filter(Boolean);
  const stageName = (s) => ({ claim: 'Claim', dispute: 'Dispute rejected', appeal: 'Appeal', removed_with_strike: 'Removed with strike', unknown: 'Unknown' }[s] || s);

  function renderRail(r) {
    if (!r) {
      $('#rail').innerHTML = RAIL.map(n => `<div class="stage idle"><span class="dot"></span><div class="name">${esc(n.name)}</div>${n.risk ? `<div class="risk">${esc(n.risk)}</div>` : ''}</div>`).join('');
      return;
    }
    const journey = W.processJourney(r);
    const se = Object.fromEntries((r.step_evidence || []).map(s => [s.step, s]));
    $('#rail').innerHTML = RAIL.map((n, i) => {
      const node = journey[i];
      const cls = node.current ? 'current' : node.recorded ? 'past' : 'future';
      const ev = n.step && se[n.step];
      let chips = '';
      if (ev) {
        const suffix = ev.available ? '' : ' · unavailable here';
        chips = `<div class="chips">${chip(VERDICT[ev.evidence_status] + suffix, VCLASS[ev.evidence_status] + (ev.available ? '' : ' unavail'), VICON[ev.evidence_status])}</div>`;
      }
      return `<div class="stage ${cls}"><span class="dot"></span><div class="name">${esc(n.name)}</div><span class="here">${esc(node.detail)}</span>${node.reviewing ? `<div class="risk">${esc(node.reviewLabel)}</div>` : ''}${!node.recorded && !node.current && n.risk ? `<div class="risk">${esc(n.risk)}</div>` : ''}${chips}</div>`;
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
    const body = d.sentences.map(s => { const text = esc(s.text).replace(/\s*\[([^\]]+)\]/g, (m, c) => `<span class="cite">${c}</span>`); return `<p class="sentence" data-sid="${esc(s.id)}" tabindex="0" role="button">${text}</p>`; }).join('');
    return `<section class="section"><h2>${d.kind === 'counter_notice' ? 'Counter-notice draft' : d.kind === 'appeal' ? 'Appeal draft' : 'Dispute draft'}</h2>
      <p class="lede">Review and copy. Click any sentence to see its source. Nothing is submitted.</p>
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
    $$('[data-sid]').forEach(el => {
      el.onclick = () => selectEvidence(el.dataset.sid);
      el.onkeydown = e => { if ((e.key === 'Enter' || e.key === ' ') && el.tagName !== 'BUTTON') { e.preventDefault(); el.click(); } };
    });
    const signalButton = $('[data-signal-source]');
    if (signalButton) signalButton.onclick = () => selectEvidence('rule:' + state.signal.rule.rule_id, state.signal.source);
    const copy = $('#btn-copy');
    if (copy) copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(state.result.draft.header + '\n\n' + state.result.draft.text); copy.innerHTML = `${icon('i-check')} Copied`; copy.classList.add('copied'); setTimeout(() => { copy.innerHTML = `${icon('i-copy')} Copy draft`; copy.classList.remove('copied'); }, 1800); } catch (e) { copy.textContent = 'Copy failed: select the text instead'; } });
  }

  const W = window.NGWorkspace;
  function labelFact(key) {
    const names = {governing_terms_clause:'Which terms apply', licence_version:'Licence version', grant_statement:'Permission from the licensor',
      content_id_administrator_name:'Rights administrator', excluded_use:'Uses not covered', permitted_use:'Uses covered'};
    const base = key.replace(/\[.*\]$/, '');
    return names[base] || (base.charAt(0).toUpperCase() + base.slice(1).replace(/_/g, ' '));
  }
  function render() {
    const r = state.result;
    state.signal = W.signal(r);
    state.docId = state.signal?.source?.doc_id || r.documents[0]?.id;
    state.filter = 'all';
    state.active = state.signal ? 'rule:' + state.signal.rule.rule_id : null;
    state.selectedSource = state.signal?.source || null;
    document.body.dataset.verdict = VCLASS[r.verdict];
    document.body.classList.add('has-case');
    $('#busy').hidden = true;
    $('#centre').innerHTML = `<div class="finding-scroll"><div class="finding-nav"><span id="finding-count">Evidence</span><div><button class="round-button" type="button" id="previous-finding" aria-label="Previous finding">↑</button><button class="round-button" type="button" id="next-finding" aria-label="Next finding">↓</button></div></div>
      <div class="finding-controls"><label class="sr-only" for="finding-picker">Choose a finding</label><select id="finding-picker"></select><label class="sr-only" for="category-filter">Filter findings by category</label><select id="category-filter"><option value="all">All tags</option>${W.categories.map(([k,l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select></div>
      ${state.diff && state.diff.verdict_before !== 'none' ? `<details class="change-note" open><summary>What changed</summary><p>${esc(state.diff.summary)}</p></details>` : ''}
      <section id="chain" aria-label="Evidence detail" tabindex="-1"></section>
      <div id="signal-slot"></div></div>`;
    renderReport(); renderSidebar(); renderSource(); renderFindings();
    if (state.active) renderChain(state.active); else renderChainEmpty();
    scrollToPhrase();
    $('#finding-picker').onchange = e => openFinding(e.target.value);
    $('#category-filter').onchange = e => { state.filter = e.target.value; state.active = null; state.selectedSource = null; renderFindings(); openFinding(state.findingItems[0]?.sid); };
    $('#previous-finding').onclick = () => moveFinding(-1);
    $('#next-finding').onclick = () => moveFinding(1);
  }
  function renderSidebar() {
    const r = state.result;
    $('#case-sidebar').innerHTML = `<section class="claim-journey" aria-labelledby="claim-journey-title"><div class="sidebar-heading"><span class="eyebrow" id="claim-journey-title">CLAIM JOURNEY</span></div>
      ${r.stage === 'unknown' ? '<p class="journey-unknown">Stage not established by the documents.</p>' : ''}
      <ol>${W.processJourney(r).map(n => `<li class="journey-node${n.current ? ' is-current' : ''}${n.recorded ? ' is-recorded' : ''}${n.reviewing ? ' is-reviewing' : ''}" data-stage="${n.id}"${n.current ? ' aria-current="step"' : ''}><span class="journey-marker" aria-hidden="true">${n.recorded && !n.current ? '✓' : ''}</span><div><b>${esc(n.label)}</b><small>${esc(n.detail)}</small>${n.reviewing ? `<span class="journey-review">${esc(n.reviewLabel)}</span>` : ''}</div></li>`).join('')}</ol>
      <button class="process-details-link" type="button" data-process>Process details <span aria-hidden="true">↗</span></button></section>
      <div class="sidebar-heading documents-label"><span class="eyebrow">DOCUMENTS</span><span class="count">${r.documents.length}</span></div>
      <nav class="document-list" aria-label="Choose source document">${r.documents.map((d,i) => `<button type="button" class="document-item" data-doc="${esc(d.id)}" aria-pressed="${d.id === state.docId}" title="${esc(d.filename)}"><span class="document-symbol">${icon('i-doc')}</span><span><b>${esc(DOC_LABEL[d.doc_type] || d.doc_type)}</b><small>${d.extraction_failed ? 'Extraction rejected' : `${d.n_facts} highlights`}</small></span><span class="doc-index">${String(i + 1).padStart(2,'0')}</span></button>`).join('')}</nav>
      <div class="sidebar-bottom"><label class="btn secondary full-width" for="workspace-add">${icon('i-plus')} Add evidence<input class="sr-only" type="file" id="workspace-add" multiple accept=".txt,.md,.pdf,.eml"></label>
      ${r.stage === 'removed_with_strike' && r.stated.name === 'Leo Marsh' && !r.documents.some(d => d.doc_type === 'licensor_email') ? '<button type="button" class="email-demo" id="workspace-leo-email">Try Leo’s permission email <span>↗</span></button>' : ''}
      <button class="sidebar-settings" type="button" data-settings>Case settings</button></div>`;
    $('#workspace-add').onchange = async e => { await addDocuments(Array.from(e.target.files)); };
    $$('[data-doc]').forEach(b => b.onclick = () => {
      state.docId = b.dataset.doc; state.selectedSource = null; state.active = null; state.filter = 'all';
      renderSidebar(); renderSource(); renderFindings(); renderChainEmpty(); renderSignal();
    });
    const activeDoc = $('.document-item[aria-pressed=true]'), list = $('.document-list');
    if (matchMedia('(max-width:760px)').matches && activeDoc) list.scrollLeft = activeDoc.offsetLeft - list.offsetLeft - list.clientWidth / 3;
    const emailButton = $('#workspace-leo-email');
    if (emailButton) emailButton.onclick = () => { emailButton.disabled = true; emailButton.textContent = 'Checking email…'; $('#btn-leo-email').click(); };
  }
  function nextStepAction(r) {
    const action = r.draft && !r.draft.withheld_reason ? `View ${STEP[r.chosen_step]} draft` : r.verdict === 'evidence_gap' ? 'See what’s missing' : 'See your answer';
    return `<div class="answer-shortcut"><button type="button" class="btn" data-report aria-describedby="next-step-detail">Next step <span aria-hidden="true">→</span></button><span id="next-step-detail">${esc(action)}</span></div>`;
  }
  function renderSource() {
    const r = state.result, doc = r.documents.find(d => d.id === state.docId);
    if (!doc) { $('#source-workspace').innerHTML = `<p class="no-source">No source documents available.</p><div class="source-bottom">${nextStepAction(r)}</div>`; return; }
    const annotations = W.annotations(r, doc);
    const skin = state.plainSource ? 'plain' : documentSkin(doc.doc_type);
    const scan = ['certificate','letter','receipt'].includes(skin);
    $('#source-workspace').innerHTML = `<div class="document-toolbar"><span>${icon('i-doc')} ${esc(doc.filename)}</span><div class="document-view-controls"><button type="button" id="toggle-source-style" aria-pressed="${Boolean(state.plainSource)}">${state.plainSource ? 'Document view' : 'Plain text'}</button><details class="highlight-key"><summary>Highlight key</summary><div>${W.categories.map(([k,l]) => `<span class="tag-label tag-${k}"><i></i>${esc(l)}</span>`).join('')}</div></details></div></div>
      <div class="paper-scroll" id="paper-scroll" tabindex="0" aria-label="Scrollable source document"><article class="source-paper source-${skin}${scan ? ' scan-paper' : ''}" aria-label="${esc(DOC_LABEL[doc.doc_type] || doc.doc_type)} — restyled source text">
      ${doc.extraction_failed ? '<div class="error">Extraction rejected. This document is readable, but its extracted facts are not used.</div>' : ''}<div id="source-lines" class="source-lines">${sourceLines(doc, annotations)}</div></article></div>
      <div class="source-bottom"><div class="source-info"><span>${scan ? 'Restyled source · simulated scan texture' : 'Restyled source text'}</span><span>${annotations.length} highlighted phrases</span></div>${nextStepAction(r)}</div>`;
    document.fonts.ready.then(() => { if (state.selectedSource) scrollToPhrase(); });
    $('#toggle-source-style').onclick = () => { state.plainSource = !state.plainSource; renderSource(); scrollToPhrase(); };
    $$('[data-highlight]').forEach(b => b.onclick = () => {
      const source = annotations[Number(b.dataset.highlight)];
      selectEvidence('fact:' + source.key, source);
    });
  }
  function documentSkin(type) {
    if (['removal_notice','strike_notice'].includes(type)) return 'letter';
    if (['claim_notice','dispute_response','appeal_response'].includes(type)) return 'platform';
    return ({receipt:'receipt',licence_certificate:'certificate',licensor_terms:'terms',licensor_email:'email',track_page:'catalogue',video_metadata:'studio'})[type] || 'plain';
  }
  function sourceLines(doc, annotations) {
    let offset = 0;
    const isURL = line => /^(?:https?:\/\/|(?:[a-z0-9-]+\.)+[a-z]{2,}\/)/i.test(line);
    const trackTitle = doc.doc_type === 'track_page' ? doc.lines.findIndex(line => line.trim() && !isURL(line)) : -1;
    return doc.lines.map((line, i) => {
      const chars = Array.from(line), end = offset + chars.length;
      const isMeta = /^[A-Za-z][A-Za-z0-9 %/().-]{1,36}:/.test(line) && !/^https?:/.test(line);
      const labelLength = isMeta ? Array.from(line.slice(0, line.indexOf(':') + 1) + (line.slice(line.indexOf(':') + 1).match(/^ */)?.[0] || '')).length : 0;
      const titleSplit = i === 0 && !isMeta && line.includes(' — ') ? Array.from(line.slice(0, line.indexOf(' — ') + 3)).length : 0;
      const splitAt = labelLength || titleSplit;

      const spans = annotations.map((a, index) => ({ ...a, index })).filter(a => a.char_start < end && a.char_end > offset);
      const boundaries = [...new Set([offset, end, ...(splitAt ? [offset + splitAt] : []), ...spans.flatMap(a => [Math.max(offset, a.char_start), Math.min(end, a.char_end)])])].sort((a, b) => a - b);
      let html = '', prefix = '';
      for (let j = 0; j < boundaries.length - 1; j++) {
        const start = boundaries[j], stop = boundaries[j + 1];
        const covering = spans.filter(a => a.char_start <= start && a.char_end >= stop);
        const selected = state.selectedSource;
        const chosen = covering.find(a => selected && a.key === selected.key && a.char_start === selected.char_start) || covering[0];
        const text = esc(chars.slice(start - offset, stop - offset).join(''));
        const active = chosen && selected && chosen.key === selected.key && chosen.char_start === selected.char_start;
        if (splitAt && start === offset + splitAt) { prefix = html; html = ''; }
        html += chosen ? `<button type="button" class="source-highlight tag-${chosen.category}${active ? ' selected' : ''}" data-highlight="${chosen.index}" title="${esc(labelFact(chosen.key))} · ${esc(W.categories.find(c => c[0] === chosen.category)[1])}" aria-label="${esc(labelFact(chosen.key))}: ${esc(chars.slice(start - offset, stop - offset).join(''))}">${text}</button>` : text;
      }
      if (splitAt) html = `<span class="${labelLength ? 'field-label' : 'source-brand'}">${prefix}</span><span class="${labelLength ? 'field-value' : 'source-subtitle'}">${html}</span>`;
      offset = end + 1;
      const isHeading = /^\d+\.\s+[A-Z]/.test(line) || /^(Items|About this track|Rights and claims|What you can do|Monetisation|Audio track used)$/.test(line);
      const classes = [doc.doc_type === 'licensor_email' && /^(From|To|Date|Subject|Message-ID):/.test(line) ? 'email-envelope' : '', !line.trim() ? 'is-blank' : '', /^>/.test(line) ? 'email-reply' : '', /^Message-ID:/.test(line) ? 'email-message-id' : '', /^Signed for|Licensing Manager$/.test(line) ? 'signature-line' : '', i === 0 ? 'document-title' : '', i === trackTitle ? 'track-title' : '', trackTitle >= 0 && i === trackTitle + 1 ? 'track-artist' : '', isHeading ? 'document-section' : '', isMeta ? 'document-meta' : '', /^Total charged:/i.test(line) ? 'receipt-total' : '', /^Subject:/i.test(line) ? 'email-subject' : '', isURL(line) ? 'document-url' : ''].filter(Boolean).join(' ');
      return `<div class="source-line ${classes}"><span class="line-number" aria-hidden="true">${i + 1}</span><span class="line-text">${html || ' '}</span></div>`;
    }).join('');
  }
  function renderFindings() {
    const r = state.result;
    const facts = r.facts.filter(f => (f.sources || []).some(s => s.doc_id === state.docId) || ['missing','conflicting'].includes(f.status));
    const shown = facts.filter(f => state.filter === 'all' || W.category(f) === state.filter);
    state.findingItems = shown.map(f => ({sid:'fact:' + f.key,label:labelFact(f.key),fact:f}));
    if (state.signal && state.filter === 'all') state.findingItems.unshift({sid:'rule:' + state.signal.rule.rule_id,label:'Key finding · ' + state.signal.title,source:state.signal.source});
    if (state.active && !state.findingItems.some(f => f.sid === state.active)) {
      const node = r.chain[state.active];
      if (node) state.findingItems.unshift({sid:state.active,label:node.rule_name || 'Selected evidence'});
    }
    const index = state.findingItems.findIndex(f => f.sid === state.active);
    $('#finding-picker').innerHTML = `${index < 0 ? '<option value="">Choose a finding</option>' : ''}` + state.findingItems.map(f => `<option value="${esc(f.sid)}" ${f.sid === state.active ? 'selected' : ''}>${esc(f.label)}</option>`).join('');
    $('#category-filter').value = state.filter;
    $('#finding-count').textContent = index >= 0 ? `Finding ${index + 1} of ${state.findingItems.length}` : `${state.findingItems.length} findings`;
    $('#previous-finding').disabled = index <= 0;
    $('#next-finding').disabled = !state.findingItems.length || index === state.findingItems.length - 1;
  }
  function openFinding(sid) {
    const item = state.findingItems.find(f => f.sid === sid);
    if (!item) { state.active = null; state.selectedSource = null; renderSource(); renderChainEmpty(); renderSignal(); return; }
    const source = item.source || item.fact?.sources?.find(s => s.doc_id === state.docId) || item.fact?.sources?.[0];
    selectEvidence(sid, source ? { ...source, key: item.fact?.key || source.key } : null);
  }
  function moveFinding(delta) {
    const i = state.findingItems.findIndex(f => f.sid === state.active);
    openFinding(state.findingItems[Math.max(0,i + delta)]?.sid);
  }
  function renderChainEmpty() {
    $('#chain').innerHTML = `<div class="chain-empty"><span class="eyebrow">FOLLOW THE EVIDENCE</span><h2>Start with a highlight.</h2><p>Choose a phrase in the document to see what it supports.</p></div>`;
  }
  function renderChain(sid) {
    const r = state.result, node = r.chain[sid];
    if (!node) { renderChainEmpty(); return; }
    const signal = state.signal, isSignal = signal && sid === 'rule:' + signal.rule.rule_id;
    const selected = state.selectedSource;
    const primary = node.facts.find(f => selected && f.doc_id === selected.doc_id && f.char_start === selected.char_start && f.fact_key === selected.key)
      || node.facts.find(f => f.doc_id === state.docId && f.quote) || node.facts.find(f => f.doc_id && f.quote);
    const doc = r.documents.find(d => d.id === primary?.doc_id);
    const exact = !!doc && !!primary && W.verified(doc,primary);
    const fact = r.facts.find(f => f.key === (selected?.key || primary?.fact_key));
    const rule = r.rule_results.find(x => x.rule_id === node.rule_id);
    const title = isSignal ? signal.title : sid.startsWith('fact:') ? labelFact(sid.slice(5)) : node.rule_name || 'Your evidence';
    const statusWord = VERDICT[node.status] || STATUS[node.status]?.[0] || FSTATUS[node.status]?.[0] || ({pass:'Rule supported',fail:'Evidence not supported',unknown:'Needs a closer look'}[node.status]) || 'Evidence finding';
    const statusClass = VCLASS[node.status] || STATUS[node.status]?.[1] || FSTATUS[node.status]?.[1] || (node.rule_status === 'pass' ? 'ready' : 'gap');
    const explanation = isSignal ? signal.why : rule?.explanation || fact?.note || (fact?.status === 'stated_by_you' ? 'This value was entered in the case settings. It is not confirmed by a document.' : fact?.status === 'missing' ? 'This fact is not supported by the documents currently in this case.' : 'This phrase was extracted from your document. No direct decision rule uses this fact.');
    $('#chain').innerHTML = `<article class="focused-finding"><div class="focused-status">${chip(statusWord,statusClass)}${rule ? `<span class="rule-reference">${esc(rule.rule_id)}</span>` : ''}</div><h2>${esc(title)}</h2>
      ${primary ? `<p class="source-reference">${esc(primary.doc_filename)}${primary.clause_ref ? ' · § ' + esc(primary.clause_ref) : ' · line ' + primary.line_start}</p><button class="selected-quote tag-${fact ? W.category(fact) : 'licence'}" type="button" id="jump-to-quote"><q>${esc(primary.quote)}</q><span>Show in document ↗</span></button>` : '<div class="no-source">No document phrase supports this item. Missing evidence cannot be highlighted.</div>'}
      <p class="finding-explanation">${esc(explanation)}</p>
      <details class="evidence-trace"><summary>Evidence & rule ${rule ? '<span>' + esc(rule.rule_id) + '</span>' : ''}</summary><div class="trace-path">Document → Phrase → Fact → Rule → Status</div>
      ${node.facts.map((f,i) => `<button type="button" class="trace-fact" data-chain-fact="${i}"><span>${esc(labelFact(f.fact_key))}</span><b>${esc(f.value == null ? 'Missing' : String(f.value))}</b><small>${esc(FSTATUS[f.status]?.[0] || f.status)}${f.doc_filename ? ' · ' + esc(f.doc_filename) : ''}</small></button>`).join('')}
      ${rule ? `<div class="rule-detail"><b>${esc(rule.rule_id)} · ${esc(rule.rule_name)}</b><p>${esc(rule.explanation)}</p></div>` : ''}
      ${(node.mapping_runs || []).map(m => `<details class="mapping-detail"><summary>Interpretation · ${esc(m.result)}</summary>${m.answers.map(a => `<p><b>${esc(a.covers)}</b> · ${esc(a.reason)}</p>`).join('')}</details>`).join('')}</details>
      <details class="quote-integrity"><summary>${exact ? icon('i-check') + ' Exact quote checked' : icon('i-doc') + ' Evidence integrity'}</summary><p>${primary ? exact ? 'Exact quote matches the source text at its recorded position.' : 'Exact source match could not be confirmed in this view.' : 'No document quote: this item is missing, stated by you, or derived from rules.'}</p><p>${rule ? 'Deterministic rule ' + esc(rule.rule_id) + ' · ' : ''}Rules v${esc(r.rules_version)}</p>${doc ? `<p>${esc(doc.filename)}</p><code>SHA-256 ${esc(doc.sha256)}</code><p>Fingerprint of normalized text, not original file bytes. Authenticity is not assessed.</p>` : ''}</details></article>`;
    $('#jump-to-quote')?.addEventListener('click', () => { selectEvidence(sid, primary ? {...primary,key:primary.fact_key} : null); if (matchMedia('(max-width:760px)').matches) $('.source-highlight.selected')?.scrollIntoView({block:'center',behavior:'auto'}); });
    $$('[data-chain-fact]').forEach(button => button.onclick = () => {
      const f = node.facts[Number(button.dataset.chainFact)]; selectEvidence('fact:' + f.fact_key,{...f,key:f.fact_key});
    });
    renderSignal();
  }
  function renderSignal() {
    const s = state.signal, slot = $('#signal-slot');
    if (!s) { slot.innerHTML = ''; return; }
    const selected = state.active === 'rule:' + s.rule.rule_id;
    slot.innerHTML = `<details class="signal-card" ${selected ? 'open' : ''}><summary><span class="signal-label"><span class="signal-dot"></span>SIGNAL</span><span>What you might miss</span><span class="disclosure-arrow">⌄</span></summary><div class="signal-content"><p class="signal-question">What could a smart, cautious creator still miss?</p>${!selected ? `<h3>${esc(s.title)}</h3><p>${esc(s.why)}</p>` : ''}
      <button type="button" class="text-button" data-signal-source>${selected ? 'Revisit the highlighted evidence' : 'See the key finding'} <span>↗</span></button>
      ${s.route ? `<div class="signal-route"><span class="eyebrow">LOWEST-RISK ROUTE</span><p>${esc(s.route.title)}</p><details><summary>Why this route</summary><p>${esc(s.route.description)}</p></details></div>` : ''}
      <span class="signal-rule">Detected by ${esc(s.rule.rule_id)} · ${esc(s.rule.rule_name)}</span></div></details>`;
    $('[data-signal-source]').onclick = () => { state.filter = 'all'; selectEvidence('rule:' + s.rule.rule_id,s.source); if (matchMedia('(max-width:760px)').matches) $('.source-highlight.selected')?.scrollIntoView({block:'center',behavior:'auto'}); };
  }
  function scrollToPhrase() {
    const marks = $$('.source-highlight.selected'), paper = $('#paper-scroll');
    if (marks.length && paper) {
      const top = marks[0].getBoundingClientRect().top, bottom = marks[marks.length - 1].getBoundingClientRect().bottom;
      const space = Math.max(12, (paper.clientHeight - (bottom - top)) / 2);
      paper.scrollTop += top - paper.getBoundingClientRect().top - space;
    }
    if (matchMedia('(max-width:760px)').matches) {
      const active = $('.document-item[aria-pressed=true]'), list = $('.document-list');
      if (active && list) list.scrollLeft = active.offsetLeft - list.offsetLeft - list.clientWidth / 3;
    }
  }
  function selectEvidence(sid, preferred) {
    state.active = sid;
    if ($('#report-dialog').open) $('#report-dialog').close();
    const node = state.result.chain[sid];
    const candidates = node?.facts || [];
    const source = preferred || candidates.find(f => f.doc_id === state.docId && f.quote) || candidates.find(f => f.doc_id && f.quote);
    state.selectedSource = null;
    if (source) {
      const doc = state.result.documents.find(d => d.id === source.doc_id);
      if (doc) state.docId = doc.id;
      if (doc && W.verified(doc,source)) state.selectedSource = {...source,key:source.key || source.fact_key};
    }
    renderSidebar(); renderSource(); renderFindings(); renderChain(sid); scrollToPhrase();
    if (matchMedia('(max-width:760px)').matches) $('#centre').scrollIntoView({block:'start',behavior:'auto'});
    const panel = $('#centre'); panel.scrollTop = 0;
  }

  document.addEventListener('click', e => { if (e.target.closest('[data-settings]')) $('#settings-dialog').showModal(); });
  $('#close-settings').addEventListener('click', () => $('#settings-dialog').close());
  renderRail(null);
  document.addEventListener('click', e => {
    if (e.target.closest('[data-report]') && state.result) { $('#report-dialog').showModal(); $('#report-dialog').scrollTop = 0; }
    if (e.target.closest('[data-process]') && state.result) { $('#report-dialog').showModal(); const details = $('#process-details'); details.open = true; details.scrollIntoView({block:'start'}); }
  });
  $('#close-report').onclick = () => $('#report-dialog').close();
  $('#back-to-documents').onclick = () => { if ($('#report-dialog').open) $('#report-dialog').close(); };
  const homeDrop = $('#home-dropzone');
  function homeUpload(files) { if (!files.length) return; addFiles(files); $('#settings-dialog').showModal(); }
  $('#home-files').onchange = e => { homeUpload(e.target.files); e.target.value = ''; };
  ['dragenter','dragover'].forEach(type => homeDrop.addEventListener(type,e => { e.preventDefault(); homeDrop.classList.add('over'); }));
  ['dragleave','drop'].forEach(type => homeDrop.addEventListener(type,e => { e.preventDefault(); homeDrop.classList.remove('over'); }));
  homeDrop.addEventListener('drop',e => homeUpload(e.dataTransfer.files));


  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (state.result) scrollToPhrase(); }, 100); });

  // deep-link demo: /?demo=maya
  const params = new URLSearchParams(location.search);
  if (params.get('demo')) loadDemo(params.get('demo')).then(() => { const o = params.get('open'); if (o) { const el = document.querySelector(`[data-sid="${CSS.escape(o)}"]`); if (el) el.click(); } });
})();
