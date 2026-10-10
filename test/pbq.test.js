// PBQ engine and content checks: every spec grades 100% with its own key, blanks earn only
// "leave empty" points, graders behave, and every view and panel renders without errors.
const fs = require('fs'), path = require('path');
const { JSDOM } = require('jsdom');
const ROOT = path.join(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/pbqs.json'), 'utf8'));

let pass = 0, fail = 0;
const ok = (c, m) => { c ? (pass++, console.log('  ✓ ' + m)) : (fail++, console.log('  ✗ ' + m)); };

const dom = new JSDOM('<!doctype html><body><div id="host"></div></body>', { runScripts: 'outside-only', pretendToBeVisual: true });
const { window } = dom;
window.eval(fs.readFileSync(path.join(ROOT, 'js/pbq.js'), 'utf8'));
window.eval(fs.readFileSync(path.join(ROOT, 'js/pbq-ui.js'), 'utf8'));
const { PBQ, PBQUI } = window;

console.log('\n— graders —');
ok(PBQ.maskBits('255.255.255.240') === 28 && PBQ.maskBits('/28') === 28 && PBQ.maskBits('28') === 28, 'mask accepts dotted, /n and n');
ok(PBQ.maskBits('255.255.0.255') === null, 'non-contiguous mask rejected');
ok(PBQ.hostInSubnet('10.20.30.14', '10.20.30.0/28') && !PBQ.hostInSubnet('10.20.30.15', '10.20.30.0/28') && !PBQ.hostInSubnet('10.20.30.0', '10.20.30.0/28'),
   'host range excludes network and broadcast');
ok(PBQ.checkField({ type: 'text', answer: { exact: 'Ab#1' } }, 'Ab#1') && !PBQ.checkField({ type: 'text', answer: { exact: 'Ab#1' } }, 'ab#1'),
   'passphrases are case-sensitive');
ok(PBQ.checkField({ type: 'text', answer: '10.0.0.1' }, ' 10.0.0.1 '), 'text trims spaces');

console.log('\n— every PBQ —');
const types = {};
for (const spec of data.pbqs) {
  types[spec.type] = (types[spec.type] || 0) + 1;
  const best = PBQ.grade(spec, PBQ.perfect(spec));
  ok(best.fraction === 1 && best.total > 0, `${spec.id}: answer key scores ${best.earned}/${best.total}`);
  if (best.fraction !== 1) for (const r of best.rows.filter((x) => !x.ok)) console.log('      ', r.where, r.label, r.got, '≠', r.want);
  // untouched = every field at its starting value; it may earn points only where that value is already right
  const blank = PBQ.grade(spec, { ans: {}, place: {} });
  const grouped = new Set([...(spec.groups || []).flatMap((g) => g.fields), ...(spec.rowsets || []).flatMap((r) => r.rows.flat())]);
  const blankOk = PBQ.fields(spec).filter(({ f }) => !grouped.has(f.id) && !(f.answer && f.answer.free) && PBQ.checkField(f, f.initial)).length;
  ok(blank.earned === blankOk && blank.fraction < 0.6,
     `${spec.id}: untouched attempt earns ${blank.earned}/${blank.total} (only fields already right at the start)`);

  // render each view and open each panel
  const host = window.document.getElementById('host');
  const item = { id: spec.id, kind: 'pbq', ans: {}, place: {} };
  let errors = 0;
  try {
    (spec.views || []).forEach((v, i) => { item.view = i; PBQUI.render(host, spec, item, () => {}); });
    for (const id of Object.keys(spec.panels || {})) {
      const p = spec.panels[id];
      p.tabs.forEach((t, i) => PBQUI.openPanel(id, i));
    }
    PBQUI.closePanel();
  } catch (e) { errors++; console.log('      ', e.stack.split('\n').slice(0, 3).join(' | ')); }
  ok(!errors, `${spec.id}: all views and panels render`);
}
console.log('\n— coverage —');
console.log('   ', JSON.stringify(types));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
