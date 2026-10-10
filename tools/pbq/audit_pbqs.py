#!/usr/bin/env python3
"""Blind audit of every PBQ with Claude Fable 5.1: the model sees only what a student sees (student_view.render),
answers every field, and flags ambiguity; then grade_audit.js scores its answers with the real grader.

  tools/explain/.venv/bin/python tools/pbq/audit_pbqs.py --dry-run             # estimate only, no calls
  tools/explain/.venv/bin/python tools/pbq/audit_pbqs.py --ids pbq-acl-remote  # measure one first
  tools/explain/.venv/bin/python tools/pbq/audit_pbqs.py --max-usd 8           # the rest (done ones are skipped)
  node tools/pbq/grade_audit.js                                                 # scores + report

Results go to tools/pbq/work/audit.json (gitignored); a PBQ already there is skipped unless --redo.
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'explain'))
from student_view import render, leaks

MODEL = 'claude-fable-5-1'
PRICE_IN, PRICE_OUT = 10.00, 50.00            # $/1M tokens
EFFORT = 'high'
EST_OUT = 12000                                # output tokens per PBQ incl. thinking (replaced by the measured mean)
WORK = os.path.join(HERE, 'work')
OUT = os.path.join(WORK, 'audit.json')

S = {'type': 'string'}
def obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
SCHEMA = obj({
    'answers': {'type': 'array', 'items': obj({'field': S, 'values': {'type': 'array', 'items': S}})},
    'placements': {'type': 'array', 'items': obj({'zone': S, 'tokens': {'type': 'array', 'items': S}})},
    'field_notes': {'type': 'array', 'items': obj({'field': S, 'issue': S})},
    'sufficient': {'type': 'boolean'}, 'unique': {'type': 'boolean'}, 'issues': S})

def load():
    return json.load(open(os.path.join(ROOT, 'data', 'pbqs.json')))['pbqs']

def done():
    return json.load(open(OUT)) if os.path.exists(OUT) else {}

def estimate(specs, measured=None):
    system = open(os.path.join(HERE, 'audit.md')).read()
    rows = []
    for s in specs:
        tin = (len(system) + len(render(s))) / 3.5 + 400          # + schema
        tout = measured or EST_OUT
        rows.append((s['id'], tin, tout, (tin * PRICE_IN + tout * PRICE_OUT) / 1e6))
    return rows

def call(api, spec):
    import anthropic
    p = dict(model=MODEL, max_tokens=64000, system=open(os.path.join(HERE, 'audit.md')).read(),
             thinking={'type': 'adaptive'},
             output_config={'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': SCHEMA}},
             messages=[{'role': 'user', 'content': render(spec)}],
             betas=['server-side-fallback-2026-06-01'], fallbacks=[{'model': 'claude-opus-4-8'}])
    try:
        with api.beta.messages.stream(**p) as st:
            msg = st.get_final_message()
    except anthropic.APIStatusError as e:
        print(f'  {spec["id"]}: API error {e.status_code}: {e.message}', file=sys.stderr); return None
    except anthropic.APIConnectionError:
        print(f'  {spec["id"]}: connection error', file=sys.stderr); return None
    if msg.stop_reason == 'refusal':
        print(f'  {spec["id"]}: refused ({msg.stop_details})', file=sys.stderr); return None
    text = next((b.text for b in msg.content if b.type == 'text'), '')
    u = msg.usage
    cost = (u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT) / 1e6
    print(f'  {spec["id"]}: {msg.model}, {u.input_tokens:,} in / {u.output_tokens:,} out, ${cost:.3f}', flush=True)
    return {'model': msg.model, 'usage': {'in': u.input_tokens, 'out': u.output_tokens}, 'cost': cost,
            'at': time.strftime('%Y-%m-%d %H:%M'), 'result': json.loads(text)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', help='comma-separated PBQ ids')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--max-usd', type=float, default=2.0)
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    specs = load()
    for s in specs:
        bad = leaks(s, render(s))
        if bad: sys.exit(f'{s["id"]}: explanation text leaks into the student view: {bad}')
    if a.ids:
        want = set(a.ids.split(','))
        specs = [s for s in specs if s['id'] in want]
        missing = want - {s['id'] for s in specs}
        if missing: sys.exit(f'unknown ids: {sorted(missing)}')
    prev = done()
    if not a.redo: specs = [s for s in specs if s['id'] not in prev]
    outs = [v['usage']['out'] for v in prev.values()]
    measured = int(sum(outs) / len(outs)) if outs else None
    rows = estimate(specs, measured)
    for i, tin, tout, usd in rows: print(f'  {i:<22} ~{tin:,.0f} in / ~{tout:,} out  ${usd:.3f}')
    total = sum(r[3] for r in rows)
    spent = sum(v['cost'] for v in prev.values())
    print(f'{len(rows)} PBQs to audit with {MODEL} (effort {EFFORT}), est. ${total:.2f} '
          f'({"measured" if measured else "assumed"} {measured or EST_OUT:,} output tokens each); already spent ${spent:.2f}')
    if a.dry_run or not rows: return
    if total > a.max_usd: sys.exit(f'estimate ${total:.2f} is above --max-usd {a.max_usd}; not calling')
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'explain'))
    from run import client
    api = client()
    os.makedirs(WORK, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for spec, r in zip(specs, ex.map(lambda s: call(api, s), specs)):
            if r:
                prev[spec['id']] = r
                json.dump(prev, open(OUT, 'w'), indent=1)
    print(f'spent ${sum(v["cost"] for v in prev.values()):.2f} in total; now run: node tools/pbq/grade_audit.js')

if __name__ == '__main__':
    main()
