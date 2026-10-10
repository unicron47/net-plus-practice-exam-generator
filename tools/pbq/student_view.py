"""Render a PBQ spec as the text a student can see: no answers, solutions, explanations, drop-zone keys, channel
groups or ACL rowsets. Used by the blind audit (audit_pbqs.py)."""

def _cell(f):
    cur = f.get('initial')
    opts = f.get('options')
    s = f'[field {f["id"]}: {f.get("type", "select")}'
    if opts: s += f'; options {opts}'
    if cur not in (None, '', []): s += f'; currently {cur!r}'
    elif f.get('type') == 'checks': s += '; currently none ticked'
    return s + ']'

def _block(b):
    k = b['kind']
    out = []
    if b.get('title'): out.append(f'**{b["title"]}**')
    if k == 'text':
        out.append(b['text'])
    elif k == 'pre':
        out.append('```\n' + b['text'] + '\n```')
    elif k == 'kv':
        out += [f'- {a}: {v}' for a, v in b['items']]
    elif k == 'table':
        out.append('| ' + ' | '.join(b['columns']) + ' |')
        out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in b['rows']]
    elif k == 'bars':
        out += [f'- {s["label"]}: {s.get("text") or str(s["value"]) + s.get("unit", "")}' for s in b['series']]
    elif k == 'wiremap':
        out += [f'- {a}: {v}' for a, v in b.get('info', [])]
        out.append('Wiremap (near-end pin → far-end pin): ' +
                   ', '.join(f'{a}→{"open (no continuity)" if z is None else z}' for a, z in b['pairs']))
        for a, z in b.get('shorts', []):
            out.append(f'Short circuit drawn between pins {a} and {z}')
        if b.get('note'): out.append(b['note'])
    elif k == 'fields':
        out += [f'- {f["label"]}: {_cell(f)}' for f in b['fields']]
    elif k == 'grid':
        out.append('| ' + ' | '.join(b['columns']) + ' |')
        for r in b['rows']:
            out.append('| ' + ' | '.join(_cell(c) if isinstance(c, dict) else str(c) for c in r) + ' |')
    elif k == 'terminal':
        out.append(f'Interactive terminal ({b["prompt"]}). {b.get("banner", "")} The student can run any of these commands '
                   'and sees exactly this output:')
        for c in b['commands']:
            out.append(f'{b["prompt"]} {c["cmd"]}\n```\n{c["out"]}\n```')
    else:
        out.append(f'({k} block)')
    return '\n'.join(out)

def render(spec):
    L = [f'# {spec["title"]}', *spec.get('scenario', [])]
    if spec.get('requirements'):
        L.append('Requirements:'); L += [f'- {r}' for r in spec['requirements']]
    if spec.get('instructions'): L.append(f'Instructions: {spec["instructions"]}')
    zone_label = {z['id']: z['label'] for z in (spec.get('dragdrop') or {}).get('zones', [])}
    for v in spec.get('views', []):
        L.append(f'\n## Tab: {v.get("label", "Main")}')
        d = v.get('diagram')
        if d:
            L.append('Diagram:')
            for z in d.get('zones', []): L.append(f'- area "{z["label"]}"')
            names = {n['id']: n['label'] for n in d.get('nodes', [])}
            for n in d.get('nodes', []):
                L.append(f'- device "{n["label"]}"' + (f' ({n["sub"]})' if n.get('sub') else '') +
                         (f' — select to open window "{spec["panels"][n["panel"]]["title"]}"' if n.get('panel') else ''))
            for l in d.get('links', []):
                L.append(f'- link {names[l["a"]]} — {names[l["b"]]}' + (f' ({l["label"]})' if l.get('label') else ''))
            for t in d.get('notes', []): L.append(f'- label "{t["text"]}"')
            slots = {}
            for s in d.get('slots', []): slots[s['zone']] = slots.get(s['zone'], 0) + 1
            for z, n in slots.items():
                L.append(f'- drop zone {z} ("{zone_label.get(z, z)}"): {n} empty slots')
        for w in v.get('widgets', []): L.append(_block(w))
        for b in v.get('blocks', []): L.append(_block(b))
    for pid, p in spec.get('panels', {}).items():
        L.append(f'\n## Window: {p["title"]}')
        for t in p['tabs']:
            L.append(f'### Window tab: {t["label"]}')
            L += [_block(b) for b in t['blocks']]
    if spec.get('palette'):
        L.append('\n## Palette (drag objects into drop-zone slots' + ('; objects can be reused' if spec['palette'].get('reusable') else '') + ')')
        for t in spec['palette']['tabs']:
            L.append(f'{t["label"]}: ' + ', '.join(f'{k["id"]} = {k["label"]}' for k in t['tokens']))
    if spec.get('questions'):
        L.append('\n## Questions')
        L += [_block(b) for b in spec['questions']]
    return '\n'.join(L)

def leaks(spec, text):
    """Answer strings that only appear in the key would be a leak; explanation sentences must never appear."""
    return [e[:60] for e in spec.get('explanation', []) if e[:60] in text]
