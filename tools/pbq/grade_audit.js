// Score the blind audit's answers (tools/pbq/work/audit.json) with the real PBQ grader and write
// tools/pbq/work/audit-report.md: per PBQ the model's score, every field it got "wrong", and its notes.
//   node tools/pbq/grade_audit.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = path.join(__dirname, '..', '..');
const ctx = { console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js/pbq.js'), 'utf8') + '\nthis.PBQ = PBQ;', ctx);
const { PBQ } = ctx;

const specs = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/pbqs.json'), 'utf8')).pbqs;
const auditFile = process.argv[2] || path.join(__dirname, 'work', 'audit.json');   // optional path, for self-tests
if (!fs.existsSync(auditFile)) { console.log('no audit results yet'); process.exit(0); }
const audit = JSON.parse(fs.readFileSync(auditFile, 'utf8'));

const out = ['# PBQ blind audit (Claude Fable 5.1)', ''];
let spent = 0, perfect = 0, n = 0;
for (const spec of specs) {
  const a = audit[spec.id];
  if (!a) continue;
  n++; spent += a.cost;
  const r = a.result;
  const byId = {};
  for (const { f } of PBQ.fields(spec)) byId[f.id] = f;
  const ans = {}, unknown = [];
  for (const { field, values } of r.answers) {
    const f = byId[field];
    if (!f) { unknown.push(field); continue; }
    ans[field] = f.type === 'checks' ? values.filter((v) => v !== '') : (values[0] ?? '');
  }
  const place = {};
  if (spec.dragdrop) {
    const slots = {};
    for (const v of spec.views) for (const s of (v.diagram && v.diagram.slots) || []) (slots[s.zone] = slots[s.zone] || []).push(s.id);
    for (const { zone, tokens } of r.placements) (tokens || []).forEach((t, i) => { if (slots[zone] && slots[zone][i]) place[slots[zone][i]] = t; });
  }
  const g = PBQ.grade(spec, { ans, place });
  if (g.fraction === 1) perfect++;
  out.push(`## ${spec.id} — ${spec.title}: ${g.earned}/${g.total}${g.fraction === 1 ? ' ✓' : ''}`);
  out.push(`model ${a.model}, ${a.usage.in} in / ${a.usage.out} out, $${a.cost.toFixed(3)}; sufficient=${r.sufficient}, unique=${r.unique}`);
  for (const x of g.rows.filter((x) => !x.ok)) out.push(`- MISS ${x.where} · ${x.label}: model ${x.got} | key ${x.want}`);
  if (unknown.length) out.push(`- (model answered unknown field ids: ${unknown.join(', ')})`);
  for (const fn of r.field_notes) out.push(`- NOTE ${fn.field}: ${fn.issue}`);
  out.push(`- ISSUES: ${r.issues}`, '');
}
out.splice(1, 0, `${n} audited, ${perfect} matched the key exactly, $${spent.toFixed(2)} spent`, '');
const reportFile = path.join(path.dirname(auditFile), 'audit-report.md');
fs.writeFileSync(reportFile, out.join('\n'));
console.log(out.slice(0, 3).join('\n'), '\n→', reportFile);
