#!/usr/bin/env python3
"""Build data/pbqs.json from the scenario modules in this folder, checking each spec.

  python3 tools/pbq/build_pbqs.py

Each s_*.py module has build() -> [spec, ...]. Structural problems stop the build; grading
self-consistency (the key scores 100%) is checked by test/pbq.test.js.
"""
import importlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MODULES = ['s_wireless', 's_design', 's_switchports', 's_cabling', 's_acl', 's_routing',
           's_addressing', 's_dashboard', 's_discovery']

def walk_fields(spec):
    def from_blocks(blocks, where):
        for b in blocks:
            if b['kind'] == 'fields':
                for f in b['fields']:
                    yield f, where
            elif b['kind'] == 'grid':
                for row in b['rows']:
                    for c in row:
                        if isinstance(c, dict):
                            yield c, where
    for v in spec.get('views', []):
        yield from from_blocks(v.get('blocks', []), v.get('label'))
    for pid, p in spec.get('panels', {}).items():
        for t in p['tabs']:
            yield from from_blocks(t['blocks'], pid)
    yield from from_blocks(spec.get('questions', []), 'questions')

def check(spec):
    errs = []
    sid = spec['id']
    ids = [f['id'] for f, _ in walk_fields(spec)]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup: errs.append(f'duplicate field ids {sorted(dup)}')
    for f, where in walk_fields(spec):
        if 'answer' not in f: errs.append(f'{f["id"]} has no answer')
        if f.get('type') in ('select', 'seg', None) and isinstance(f.get('answer'), str) and f['answer'] not in f.get('options', []):
            errs.append(f'{f["id"]} answer not in options')
    panels = spec.get('panels', {})
    for v in spec.get('views', []):
        d = v.get('diagram') or {}
        nids = [n['id'] for n in d.get('nodes', [])]
        for n in d.get('nodes', []):
            if n.get('panel') and n['panel'] not in panels: errs.append(f'node {n["id"]} -> missing panel {n["panel"]}')
        for l in d.get('links', []):
            if l['a'] not in nids or l['b'] not in nids: errs.append(f'link {l} to unknown node')
        for w in v.get('widgets', []):
            if w.get('panel') and w['panel'] not in panels: errs.append(f'widget -> missing panel {w["panel"]}')
    for g in spec.get('groups', []):
        for i in g['fields']:
            if i not in ids: errs.append(f'group field {i} missing')
        if len(g['values']) < len(g['fields']): errs.append('group has fewer values than fields')
    for rs in spec.get('rowsets', []):
        for r in rs['rows']:
            for i in r:
                if i not in ids: errs.append(f'rowset field {i} missing')
        if len(rs['rows']) != len(rs['expect']): errs.append('rowset rows != expect')
    if spec.get('dragdrop'):
        tokens = {t['id'] for tab in spec['palette']['tabs'] for t in tab['tokens']}
        slots = {}
        for v in spec['views']:
            for s in (v.get('diagram') or {}).get('slots', []):
                slots.setdefault(s['zone'], []).append(s['id'])
        for z in spec['dragdrop']['zones']:
            if len(slots.get(z['id'], [])) < len(z['expect']): errs.append(f'zone {z["id"]} has too few slots')
            for t in z['expect']:
                if t not in tokens: errs.append(f'zone {z["id"]} expects unknown token {t}')
    return [f'{sid}: {e}' for e in errs]

def main():
    specs, errs = [], []
    for m in MODULES:
        if not os.path.exists(os.path.join(HERE, m + '.py')):
            print(f'  (skipping {m}: not written yet)')
            continue
        for s in importlib.import_module(m).build():
            specs.append(s)
            errs += check(s)
    ids = [s['id'] for s in specs]
    if len(set(ids)) != len(ids): errs.append('duplicate PBQ ids')
    if errs:
        sys.exit('\n'.join(errs))
    out = os.path.join(HERE, '..', '..', 'data', 'pbqs.json')
    json.dump({'version': 1, 'count': len(specs), 'pbqs': specs}, open(out, 'w'), indent=1, ensure_ascii=False)
    by_type = {}
    for s in specs: by_type[s['type']] = by_type.get(s['type'], 0) + 1
    print(f'wrote {len(specs)} PBQs -> data/pbqs.json {by_type}')

if __name__ == '__main__':
    main()
