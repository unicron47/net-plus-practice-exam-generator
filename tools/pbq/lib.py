"""Helpers for writing PBQ specs (see js/pbq.js for the format). Scenarios import these so
addresses, masks and command output are computed, not typed, and always agree."""
import ipaddress

# ── addressing ──────────────────────────────────────────────
def net(cidr):
    return ipaddress.ip_network(cidr, strict=True)

def host(cidr, n):
    """n-th usable host of a subnet (1-based)."""
    return str(list(net(cidr).hosts())[n - 1])

def mask(prefix):
    return str(ipaddress.ip_network(f'0.0.0.0/{prefix}').netmask)

def smallest_prefix(hosts_needed):
    """Smallest subnet (largest prefix) with at least this many usable hosts."""
    for p in range(30, 0, -1):
        if 2 ** (32 - p) - 2 >= hosts_needed:
            return p
    raise ValueError(hosts_needed)

# ── fields ──────────────────────────────────────────────────
def sel(id, label, options, answer, **kw):
    assert isinstance(answer, dict) or answer in options, (id, answer, options)
    return {'id': id, 'label': label, 'type': 'select', 'options': list(options), 'answer': answer, **kw}

def seg(id, label, options, answer, **kw):
    assert isinstance(answer, dict) or answer in options, (id, answer)
    return {'id': id, 'label': label, 'type': 'seg', 'options': list(options), 'answer': answer, **kw}

def txt(id, label, answer, **kw):
    return {'id': id, 'label': label, 'type': 'text', 'answer': answer, **kw}

def checks(id, label, options, answer_set, **kw):
    assert all(a in options for a in answer_set), (id, answer_set)
    return {'id': id, 'label': label, 'type': 'checks', 'options': list(options), 'answer': {'set': list(answer_set)}, **kw}

def fields(title, *fs):
    return {'kind': 'fields', 'title': title, 'fields': list(fs)}

def pre(title, text):
    return {'kind': 'pre', 'title': title, 'text': text.strip('\n')}

def table(title, columns, rows):
    return {'kind': 'table', 'title': title, 'columns': columns, 'rows': rows}

def kv(items):
    return {'kind': 'kv', 'items': items}

def text(t):
    return {'kind': 'text', 'text': t}

# ── diagram ─────────────────────────────────────────────────
def node(id, icon, x, y, label, sub=None, panel=None):
    n = {'id': id, 'icon': icon, 'x': x, 'y': y, 'label': label}
    if sub: n['sub'] = sub
    if panel: n['panel'] = panel
    return n

def zone(x, y, w, h, label, tone='a'):
    return {'x': x, 'y': y, 'w': w, 'h': h, 'label': label, 'tone': tone}

def link(a, b, label=None):
    l = {'a': a, 'b': b}
    if label: l['label'] = label
    return l

def panel(title, *tabs):
    """tabs: (label, [blocks]) pairs, or a single list of blocks."""
    if len(tabs) == 1 and isinstance(tabs[0], list):
        tabs = (('Details', tabs[0]),)
    return {'title': title, 'tabs': [{'label': l, 'blocks': b} for l, b in tabs]}

# ── cable tester wiremaps (pin pairs top→bottom) ────────────
STRAIGHT = [[p, p] for p in (1, 2, 3, 4, 5, 6, 7, 8)]
CROSSOVER = [[1, 3], [2, 6], [3, 1], [4, 4], [5, 5], [6, 2], [7, 7], [8, 8]]       # T568A↔T568B (two pairs, 10/100)
GIG_CROSSOVER = [[1, 3], [2, 6], [3, 1], [4, 7], [5, 8], [6, 2], [7, 4], [8, 5]]   # all four pairs crossed (1000BASE-T)
REVERSED = [[p, 9 - p] for p in (1, 2, 3, 4, 5, 6, 7, 8)]                          # rolled / connector on backward

def wiremap(title, pairs, info, shorts=None, note=None, alt=None):
    b = {'kind': 'wiremap', 'title': title, 'pairs': pairs, 'info': info}
    if shorts: b['shorts'] = shorts
    if note: b['note'] = note
    if alt: b['alt'] = alt
    return b
