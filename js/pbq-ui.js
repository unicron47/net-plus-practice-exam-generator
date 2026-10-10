/* PBQ user interface: renders a PBQ spec (see js/pbq.js) and writes answers onto the item. */
'use strict';

const PBQUI = (() => {
  const E = PBQ.escH;
  const NS = 'http://www.w3.org/2000/svg';

  /* ── icons (24×24, stroked) ───────────────────────────── */
  const ICON = {
    router: '<circle cx="12" cy="12" r="8"/><path d="M8 10h8M8 14h8M14 7l2 3-2 3M10 11l-2 3 2 3"/>',
    switch: '<rect x="2" y="8" width="20" height="8" rx="2"/><path d="M6 12h.01M9 12h.01M12 12h.01M15 12h.01M18 12h.01"/>',
    firewall: '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 10h18M3 14.5h18M9 5v5M15 5v5M6 10v4.5M12 10v4.5M18 10v4.5M9 14.5V19M15 14.5V19"/>',
    server: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h8M12 16h.01"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M9 20h6M12 16v4"/>',
    laptop: '<rect x="5" y="5" width="14" height="10" rx="1"/><path d="M2 19h20l-2-4H4z"/>',
    ap: '<path d="M8.5 9.5a5 5 0 0 1 7 0M6 7a8.5 8.5 0 0 1 12 0"/><circle cx="12" cy="12.5" r="1.2"/><path d="M12 14v4M8 20h8"/>',
    printer: '<path d="M7 8V3h10v5"/><rect x="3" y="8" width="18" height="8" rx="1"/><path d="M7 14h10v7H7z"/>',
    phone: '<rect x="4" y="9" width="16" height="11" rx="2"/><path d="M7 9V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v3M8 13h.01M12 13h.01M16 13h.01M8 16.5h.01M12 16.5h.01M16 16.5h.01"/>',
    cloud: '<path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 9a4.5 4.5 0 0 1 0 9z"/>',
    db: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    tester: '<rect x="6" y="3" width="12" height="18" rx="2"/><rect x="9" y="6" width="6" height="4"/><path d="M12 21v2M9 14h.01M15 14h.01M9 17h.01M15 17h.01"/>',
    camera: '<rect x="3" y="7" width="13" height="10" rx="2"/><path d="M16 11l5-3v8l-5-3"/>',
    wlc: '<rect x="3" y="10" width="18" height="8" rx="2"/><path d="M9 6.5a4.5 4.5 0 0 1 6 0M7 4a8 8 0 0 1 10 0M7 14h.01M10 14h.01"/>',
    dashboard: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 16v-4M11 16V9M15 16v-6M19 16v-2"/>',
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/>',
    vlan: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 14h18M9 4v16"/>',
  };
  const icon = (name, cls = 'pbq-ico') =>
    `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ICON.server}</svg>`;

  /* ── panel window (one, reused) ───────────────────────── */
  let win = null, ctx = null;   // ctx = {spec, item, onChange}
  function ensureWin() {
    if (win) return win;
    win = document.createElement('div');
    win.className = 'pbq-overlay';
    win.hidden = true;
    win.innerHTML = '<div class="pbq-win" role="dialog" aria-modal="true" aria-labelledby="pbq-win-title">' +
      '<header><h3 id="pbq-win-title"></h3><button type="button" class="pbq-x" aria-label="Close">✕</button></header>' +
      '<nav class="pbq-wtabs"></nav><div class="pbq-wbody"></div>' +
      '<footer><button type="button" class="btn small pbq-done">Done</button></footer></div>';
    document.body.appendChild(win);
    win.querySelector('.pbq-x').addEventListener('click', closePanel);
    win.querySelector('.pbq-done').addEventListener('click', closePanel);
    win.addEventListener('click', (e) => { if (e.target === win) closePanel(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !win.hidden) closePanel(); });
    return win;
  }
  function openPanel(id, tab = 0) {
    const p = ctx.spec.panels[id];
    if (!p) return;
    const w = ensureWin();
    w.querySelector('#pbq-win-title').textContent = p.title;
    const nav = w.querySelector('.pbq-wtabs');
    nav.innerHTML = '';
    nav.hidden = p.tabs.length < 2;
    p.tabs.forEach((t, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = t.label;
      b.className = i === tab ? 'on' : '';
      b.addEventListener('click', () => openPanel(id, i));
      nav.appendChild(b);
    });
    const body = w.querySelector('.pbq-wbody');
    body.innerHTML = '';
    for (const b of p.tabs[tab].blocks) body.appendChild(block(b, id));
    w.hidden = false;
    const first = body.querySelector('input, select, button');
    (first || w.querySelector('.pbq-x')).focus();
  }
  function closePanel() {
    if (win) win.hidden = true;
    if (ctx && ctx.redraw) ctx.redraw();       // diagram badges reflect what was changed
  }

  /* ── diagram ──────────────────────────────────────────── */
  let selectedToken = null;
  function diagram(d) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${d.w} ${d.h}`);
    svg.setAttribute('class', 'pbq-svg');
    svg.setAttribute('role', 'group');
    const nodes = Object.fromEntries((d.nodes || []).map((n) => [n.id, n]));
    let h = '';
    for (const z of d.zones || []) {
      h += `<g class="pbq-zone tone-${z.tone || 'a'}"><rect x="${z.x}" y="${z.y}" width="${z.w}" height="${z.h}" rx="10"/>` +
           `<text x="${z.x + 10}" y="${z.y + 18}">${E(z.label)}</text></g>`;
    }
    for (const l of d.links || []) {
      const a = nodes[l.a], b = nodes[l.b];
      if (!a || !b) continue;
      h += `<line class="pbq-link" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`;
      if (l.label) h += `<text class="pbq-llabel" x="${(a.x + b.x) / 2 + 4}" y="${(a.y + b.y) / 2 - 4}">${E(l.label)}</text>`;
    }
    for (const n of d.nodes || []) {
      const cls = 'pbq-node' + (n.panel ? ' clickable' : '');
      h += `<g class="${cls}" data-node="${E(n.id)}" ${n.panel ? `tabindex="0" role="button" aria-label="${E(n.label)}: open"` : ''}>` +
           `<rect x="${n.x - 34}" y="${n.y - 26}" width="68" height="52" rx="10"/>` +
           `<svg x="${n.x - 13}" y="${n.y - 19}" width="26" height="26" viewBox="0 0 24 24" class="pbq-nico">${ICON[n.icon] || ICON.server}</svg>` +
           `<text class="pbq-nlabel" x="${n.x}" y="${n.y + 20}">${E(n.label)}</text>` +
           (n.sub ? `<text class="pbq-nsub" x="${n.x}" y="${n.y + 42}">${E(n.sub)}</text>` : '') + '</g>';
    }
    for (const t of d.notes || []) {
      h += `<text class="pbq-note${t.mono ? ' mono' : ''}" x="${t.x}" y="${t.y}" text-anchor="${t.anchor || 'start'}">${E(t.text)}</text>`;
    }
    for (const s of d.slots || []) {
      const tok = ctx.item.place && ctx.item.place[s.id];
      const t = tok && tokenById(tok);
      h += `<g class="pbq-slot${t ? ' filled' : ''}" data-slot="${E(s.id)}" tabindex="0" role="button" ` +
           `aria-label="${t ? E(t.label) + ' placed; activate to remove' : 'Empty slot'}">` +
           `<rect x="${s.x - 48}" y="${s.y - 20}" width="96" height="40" rx="8"/>` +
           (t ? `<text x="${s.x}" y="${s.y + 4}">${E(t.label)}</text>` : `<text x="${s.x}" y="${s.y + 5}" class="q">?</text>`) + '</g>';
    }
    svg.innerHTML = h;
    svg.querySelectorAll('.pbq-node.clickable').forEach((g) => {
      const n = nodes[g.dataset.node];
      const go = () => openPanel(n.panel);
      g.addEventListener('click', go);
      g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
    svg.querySelectorAll('.pbq-slot').forEach((g) => {
      const act = () => slotClick(g.dataset.slot);
      g.addEventListener('click', act);
      g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); act(); } });
      g.addEventListener('dragover', (e) => e.preventDefault());
      g.addEventListener('drop', (e) => {
        e.preventDefault();
        const id = e.dataTransfer.getData('text/plain');
        if (id) { selectedToken = id; slotClick(g.dataset.slot); }
      });
    });
    const wrap = document.createElement('div');
    wrap.className = 'pbq-diagram';
    wrap.appendChild(svg);
    return wrap;
  }
  function tokenById(id) {
    for (const t of (ctx.spec.palette && ctx.spec.palette.tabs) || []) for (const k of t.tokens) if (k.id === id) return k;
    return null;
  }
  function slotClick(slot) {
    const place = (ctx.item.place = ctx.item.place || {});
    if (selectedToken) { place[slot] = selectedToken; if (!ctx.spec.palette.reusable) selectedToken = null; }
    else if (place[slot]) delete place[slot];
    ctx.onChange();
    ctx.redraw();
  }

  /* ── controls ─────────────────────────────────────────── */
  function setAns(id, v) {
    const ans = (ctx.item.ans = ctx.item.ans || {});
    ans[id] = PBQ.isEmpty(v) ? '' : v;           // kept even when emptied: clearing a pre-filled value is an answer
    ctx.onChange();
  }
  function control(f) {
    const v = PBQ.valueOf(f, ctx.item.ans || {});
    const lab = `aria-label="${E(f.label || f.id)}"`;
    if (f.type === 'text') {
      const i = document.createElement('input');
      i.type = 'text'; i.className = `pbq-in w-${f.width || 'm'}`; i.value = v || '';
      i.setAttribute('aria-label', f.label || f.id);
      i.spellcheck = false; i.autocomplete = 'off';
      if (f.placeholder) i.placeholder = f.placeholder;
      i.addEventListener('input', () => setAns(f.id, i.value));
      return i;
    }
    if (f.type === 'seg') {
      const d = document.createElement('div');
      d.className = 'pbq-seg'; d.setAttribute('role', 'radiogroup'); d.setAttribute('aria-label', f.label || f.id);
      for (const o of f.options) {
        const b = document.createElement('button');
        b.type = 'button'; b.textContent = o; b.setAttribute('role', 'radio');
        b.setAttribute('aria-checked', String(v === o));
        b.addEventListener('click', () => {
          setAns(f.id, v === o ? '' : o);
          d.replaceWith(control(f));
        });
        d.appendChild(b);
      }
      return d;
    }
    if (f.type === 'checks') {
      const d = document.createElement('div');
      d.className = 'pbq-checks'; d.setAttribute('role', 'group'); d.setAttribute('aria-label', f.label || f.id);
      const cur = Array.isArray(v) ? v : [];
      for (const o of f.options) {
        const l = document.createElement('label');
        l.innerHTML = `<input type="checkbox" ${cur.includes(o) ? 'checked' : ''}><span>${E(o)}</span>`;
        l.querySelector('input').addEventListener('change', (e) => {
          const now = new Set(PBQ.valueOf(f, ctx.item.ans || {}) || []);
          if (e.target.checked) now.add(o); else now.delete(o);
          setAns(f.id, f.options.filter((x) => now.has(x)));
        });
        d.appendChild(l);
      }
      return d;
    }
    const s = document.createElement('select');            // default: select
    s.className = `pbq-sel w-${f.width || 'm'}`;
    s.innerHTML = `<option value="">${E(f.placeholder || 'Select…')}</option>` +
      f.options.map((o) => `<option ${o === v ? 'selected' : ''}>${E(o)}</option>`).join('');
    s.setAttribute('aria-label', f.label || f.id);
    s.addEventListener('change', () => setAns(f.id, s.value));
    void lab;
    return s;
  }

  /* ── blocks ───────────────────────────────────────────── */
  function el(tag, cls, html) { const x = document.createElement(tag); if (cls) x.className = cls; if (html !== undefined) x.innerHTML = html; return x; }
  function block(b) {
    switch (b.kind) {
      case 'text': return el('p', 'pbq-p', E(b.text));
      case 'pre': {
        const f = el('figure', 'pbq-fig');
        if (b.title) f.appendChild(el('figcaption', '', E(b.title)));
        f.appendChild(el('pre', 'pbq-pre', E(b.text)));
        return f;
      }
      case 'kv': return el('dl', 'pbq-kv', b.items.map(([k, v]) => `<dt>${E(k)}</dt><dd>${E(v)}</dd>`).join(''));
      case 'table': {
        const f = el('figure', 'pbq-fig');
        if (b.title) f.appendChild(el('figcaption', '', E(b.title)));
        const w = el('div', 'pbq-tablewrap');
        w.appendChild(el('table', 'pbq-table',
          `<thead><tr>${b.columns.map((c) => `<th>${E(c)}</th>`).join('')}</tr></thead><tbody>` +
          b.rows.map((r) => `<tr>${r.map((c) => `<td>${E(c)}</td>`).join('')}</tr>`).join('') + '</tbody>'));
        f.appendChild(w);
        return f;
      }
      case 'wiremap': return wiremap(b);
      case 'bars': {
        const f = el('figure', 'pbq-fig');
        if (b.title) f.appendChild(el('figcaption', '', E(b.title)));
        f.appendChild(el('div', 'pbq-bars', b.series.map((s) =>
          `<div class="bar"><span class="bl">${E(s.label)}</span><span class="bt"><i class="tone-${s.tone || 'a'}" style="width:${Math.min(100, (s.value / (s.max || 100)) * 100)}%"></i></span>` +
          `<span class="bv">${E(s.text ?? s.value + (s.unit || ''))}</span></div>`).join('')));
        return f;
      }
      case 'fields': {
        const f = el('fieldset', 'pbq-form');
        if (b.title) f.appendChild(el('legend', '', E(b.title)));
        for (const fd of b.fields) {
          const row = el('div', 'pbq-row');
          row.appendChild(el('span', 'pbq-flabel', E(fd.label)));
          row.appendChild(control(fd));
          f.appendChild(row);
        }
        return f;
      }
      case 'grid': {
        const f = el('figure', 'pbq-fig');
        if (b.title) f.appendChild(el('figcaption', '', E(b.title)));
        const w = el('div', 'pbq-tablewrap');
        const t = el('table', 'pbq-table pbq-grid',
          `<thead><tr>${b.columns.map((c) => `<th>${E(c)}</th>`).join('')}</tr></thead>`);
        const tb = document.createElement('tbody');
        b.rows.forEach((r, ri) => {
          const tr = document.createElement('tr');
          r.forEach((c, ci) => {
            const td = document.createElement('td');
            if (c && typeof c === 'object') td.appendChild(control({ label: `${b.columns[ci]} (row ${ri + 1})`, width: 's', ...c }));
            else td.textContent = c ?? '';
            tr.appendChild(td);
          });
          tb.appendChild(tr);
        });
        t.appendChild(tb); w.appendChild(t); f.appendChild(w);
        return f;
      }
      case 'terminal': return terminal(b);
      default: return el('p', 'pbq-p', '');
    }
  }

  function wiremap(b) {
    const f = el('figure', 'pbq-fig pbq-wire');
    if (b.title) f.appendChild(el('figcaption', '', E(b.title)));
    if (b.info) f.appendChild(el('dl', 'pbq-kv', b.info.map(([k, v]) => `<dt>${E(k)}</dt><dd>${E(v)}</dd>`).join('')));
    const pins = [1, 2, 3, 4, 5, 6, 7, 8], X = (p) => 20 + (p - 1) * 34;
    let s = '';
    for (const p of pins) s += `<text x="${X(p)}" y="14">${p}</text><text x="${X(p)}" y="118">${p}</text>`;
    for (const [a, z] of b.pairs) {
      if (z === null) s += `<line x1="${X(a)}" y1="22" x2="${X(a)}" y2="52"/><text class="open" x="${X(a)}" y="66">✕</text>`;
      else s += `<line x1="${X(a)}" y1="22" x2="${X(z)}" y2="102"/>`;
    }
    for (const [a, z] of b.shorts || []) s += `<path class="short" d="M${X(a)} 40 C ${(X(a) + X(z)) / 2} 56, ${(X(a) + X(z)) / 2} 56, ${X(z)} 40"/>`;
    f.appendChild(el('div', 'pbq-wiresvg', `<svg viewBox="0 0 278 126" role="img" aria-label="${E(b.alt || 'Cable wiremap')}">${s}</svg>`));
    if (b.note) f.appendChild(el('p', 'pbq-p small', E(b.note)));
    return f;
  }

  function terminal(b) {
    const box = el('div', 'pbq-term');
    const out = el('pre', 'pbq-tout');
    const hist = ((ctx.item.term = ctx.item.term || {})[b.id] = ctx.item.term[b.id] || []);
    out.textContent = (b.banner ? b.banner + '\n' : '') + hist.join('\n');
    const line = el('div', 'pbq-tline', `<span>${E(b.prompt)}</span>`);
    const inp = document.createElement('input');
    inp.type = 'text'; inp.spellcheck = false; inp.autocomplete = 'off';
    inp.setAttribute('aria-label', `${b.prompt} command`);
    line.appendChild(inp);
    inp.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const cmd = inp.value.trim();
      inp.value = '';
      const res = runCmd(b, cmd);
      hist.push(b.prompt + ' ' + cmd, ...(res ? [res] : []));
      while (hist.length > 200) hist.shift();
      out.textContent = (b.banner ? b.banner + '\n' : '') + hist.join('\n');
      out.scrollTop = out.scrollHeight;
      ctx.onChange();
    });
    box.append(out, line);
    return box;
  }
  /** Cisco-style abbreviations: every typed word must start the command's word ("sh mac add"). */
  function runCmd(b, cmd) {
    const words = cmd.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return '';
    if (words[0] === 'help' || words[0] === '?') {
      return 'Available commands:\n' + b.commands.map((c) => '  ' + c.cmd).join('\n');
    }
    const hit = b.commands.find((c) => {
      const cw = c.cmd.toLowerCase().split(/\s+/);
      return cw.length === words.length && cw.every((w, i) => w.startsWith(words[i]) && (words[i].length >= 2 || /^\d/.test(words[i]) || w === words[i]));
    });
    return hit ? hit.out : '% Invalid input detected. Type help for a list of commands.';
  }

  /* ── drag-and-drop palette ────────────────────────────── */
  function palette(spec) {
    const p = spec.palette;
    const box = el('div', 'pbq-palette');
    box.appendChild(el('div', 'pbq-phint', E(p.hint || 'Select an object, then select a slot to place it. Select a filled slot to empty it.' +
      (p.reusable ? ' Objects can be used more than once.' : ''))));
    const tabsNav = el('nav', 'pbq-ptabs');
    const list = el('div', 'pbq-tokens');
    const showTab = (i) => {
      tabsNav.querySelectorAll('button').forEach((b, j) => b.classList.toggle('on', i === j));
      list.innerHTML = '';
      for (const t of p.tabs[i].tokens) {
        const b = el('button', 'pbq-token' + (selectedToken === t.id ? ' sel' : ''), `${icon(t.icon || 'server')}<span>${E(t.label)}</span>`);
        b.type = 'button'; b.draggable = true;
        b.setAttribute('aria-pressed', String(selectedToken === t.id));
        b.addEventListener('click', () => { selectedToken = selectedToken === t.id ? null : t.id; showTab(i); });
        b.addEventListener('dragstart', (e) => e.dataTransfer.setData('text/plain', t.id));
        list.appendChild(b);
      }
      ctx.ptab = i;
    };
    p.tabs.forEach((t, i) => {
      const b = el('button', '', E(t.label)); b.type = 'button';
      b.addEventListener('click', () => showTab(i));
      tabsNav.appendChild(b);
    });
    if (p.tabs.length < 2) tabsNav.hidden = true;
    box.append(tabsNav, list);
    showTab(ctx.ptab || 0);
    return box;
  }

  /* ── whole PBQ ────────────────────────────────────────── */
  function render(container, spec, item, onChange) {
    if (!ctx || ctx.item !== item) selectedToken = null;
    ctx = { spec, item, onChange, ptab: ctx && ctx.item === item ? ctx.ptab : 0 };
    container.innerHTML = '';
    const root = el('div', 'pbq');
    root.appendChild(el('div', 'pbq-head', `<span class="badge pbq-badge">PBQ</span><h3 class="pbq-title">${E(spec.title)}</h3>`));
    const sc = el('div', 'pbq-scenario');
    for (const p of spec.scenario || []) sc.appendChild(el('p', '', E(p)));
    if (spec.requirements && spec.requirements.length) {
      sc.appendChild(el('ul', 'pbq-req', spec.requirements.map((r) => `<li>${E(r)}</li>`).join('')));
    }
    if (spec.instructions) sc.appendChild(el('p', 'pbq-instr', `<b>Instructions</b> ${E(spec.instructions)}`));
    root.appendChild(sc);

    const views = spec.views || [];
    const vi = Math.min(item.view || 0, Math.max(views.length - 1, 0));
    if (views.length > 1) {
      const nav = el('nav', 'pbq-vtabs');
      views.forEach((v, i) => {
        const b = el('button', i === vi ? 'on' : '', E(v.label)); b.type = 'button';
        b.addEventListener('click', () => { item.view = i; onChange(); render(container, spec, item, onChange); });
        nav.appendChild(b);
      });
      root.appendChild(nav);
    }
    const view = views[vi];
    const vbox = el('div', 'pbq-view');
    const draw = () => {
      vbox.innerHTML = '';
      if (view && view.diagram) vbox.appendChild(diagram(view.diagram));
      if (view && view.widgets) {
        const g = el('div', 'pbq-widgets');
        for (const w of view.widgets) {
          const c = el('div', 'pbq-widget' + (w.wide ? ' wide' : ''));
          c.appendChild(block({ ...w }));
          if (w.panel) {
            const b = el('button', 'btn small', E(w.action || 'Open')); b.type = 'button';
            b.addEventListener('click', () => openPanel(w.panel));
            c.appendChild(b);
          }
          g.appendChild(c);
        }
        vbox.appendChild(g);
      }
      for (const b of (view && view.blocks) || []) vbox.appendChild(block(b));
      if (spec.palette && view && view.diagram && view.diagram.slots) vbox.appendChild(palette(spec));
    };
    ctx.redraw = draw;
    draw();
    root.appendChild(vbox);
    if (spec.questions && spec.questions.length) {
      const q = el('div', 'pbq-questions');
      for (const b of spec.questions) q.appendChild(block(b));
      root.appendChild(q);
    }
    container.appendChild(root);
  }

  /* ── review (results screen) ──────────────────────────── */
  function reviewHTML(spec, item) {
    const r = PBQ.grade(spec, item);
    const rows = r.rows.map((x) => {
      const earned = x.earned !== undefined ? x.earned : (x.ok ? x.points : 0);
      const mark = x.ok ? '✓' : (earned > 0 ? '◐' : '✗');
      return `<tr class="${x.ok ? 'ok' : earned > 0 ? 'part' : 'no'}"><td>${E(x.where)}</td><td>${E(x.label)}</td>` +
             `<td>${E(x.got)}</td><td>${E(x.want)}</td><td class="m">${mark}</td></tr>`;
    }).join('');
    return `<div class="pbq-review"><div class="pbq-tablewrap"><table class="pbq-table">` +
      `<thead><tr><th>Where</th><th>Item</th><th>Your answer</th><th>Correct</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` +
      (spec.explanation || []).map((p) => `<p class="why"><span class="why-label">Why</span>${E(p)}</p>`).join('') + '</div>';
  }

  return { ICON, icon, ensureWin, openPanel, closePanel, diagram, tokenById, control, block, runCmd, render, reviewHTML,
           _state: { get ctx() { return ctx; }, set ctx(v) { ctx = v; },
                     get selected() { return selectedToken; }, set selected(v) { selectedToken = v; } } };
})();

if (typeof window !== 'undefined') window.PBQUI = PBQUI;
