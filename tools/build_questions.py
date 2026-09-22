#!/usr/bin/env python3
"""Convert the ExamTopics xlsx files into data/questions.json for the adaptive exam app.

Re-run this whenever a spreadsheet changes:
    python3 tools/build_questions.py ["<a.xlsx>" "<b.xlsx>" ...] [out.json]
With no arguments it reads the paths listed in tools/sources.local.txt (gitignored). Question IDs are a hash
of the question text, so stats survive row reordering; when the same text appears
twice (in one file or across files) the first occurrence wins.
"""
import hashlib, json, os, re, sys, zipfile
from xml.etree import ElementTree as ET

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS = {'m': M}

def cells(path):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter(f'{{{M}}}t')))
    sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    for row in sheet.find('m:sheetData', NS):
        out = {}
        for c in row.findall('m:c', NS):
            col = ''.join(ch for ch in c.get('r') if ch.isalpha())
            inline, v = c.find('m:is', NS), c.find('m:v', NS)
            if inline is not None:
                val = ''.join(t.text or '' for t in inline.iter(f'{{{M}}}t'))
            elif v is None:
                continue
            elif c.get('t') == 's':
                val = shared[int(v.text)]
            else:
                val = v.text
            val = (val or '').strip()
            if val:
                out[col] = val
        yield out

def clean(s):
    return re.sub(r'\s+', ' ', s).strip()

TYPES = ('multiple choice', 'checkbox')

def unshift(r):
    """Repair a row whose cells slid one column left (type cell holds option 1).

    Seen in "Adaptive Quiz 1" row 329: B='5G', options in C-F, answer in G, time in H.
    Only applied when column B is not a known type AND the shifted reading is valid.
    """
    if r.get('B', '').lower() in TYPES or not r.get('B'):
        return None
    fixed = {'A': r['A'], 'B': 'Multiple Choice'}
    for a, b in zip('BCDEFGH', 'CDEFGHI'):
        if r.get(a):
            fixed[b] = r[a]
    opts = [c for c in 'CDEFG' if fixed.get(c)]
    ans = re.findall(r'\d+', fixed.get('H', ''))
    if len(ans) == 1 and 1 <= int(ans[0]) <= len(opts):
        return fixed
    return None

def read_rows(src):
    rows = list(cells(src))
    header, body = rows[0], rows[1:]
    assert header.get('A', '').lower().startswith('question'), f'unexpected header in {src}: {header}'
    return body

def main(srcs, dest):
    questions, seen_ids, skipped, repaired = [], {}, [], []
    for src in srcs:
        name = re.sub(r'^Net\s+ExamTopics\s+', '', os.path.splitext(os.path.basename(src))[0])
        for i, r in enumerate(read_rows(src), start=2):
            fixed = unshift(r)
            if fixed:
                repaired.append((name, i, r.get('B')))
                r = fixed

            text = clean(r.get('A', ''))
            options = [clean(r[c]) for c in ('C', 'D', 'E', 'F', 'G') if r.get(c)]
            raw_answer = r.get('H', '')
            answer = [int(n) - 1 for n in re.findall(r'\d+', raw_answer)]

            if not text or len(options) < 2 or not answer or any(a >= len(options) for a in answer):
                skipped.append((name, i, text[:60], 'answer=' + raw_answer))
                continue

            # First occurrence wins, so existing student stats keep pointing at the same wording/options.
            qid = hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]
            if qid in seen_ids:
                skipped.append((name, i, text[:60], 'DUPLICATE of %s row %d' % seen_ids[qid]))
                continue
            seen_ids[qid] = (name, i)

            questions.append({
                'id': qid,
                'source': name,
                'row': i,
                'text': text,
                'type': 'multi' if len(answer) > 1 or r.get('B', '').lower().startswith('checkbox') else 'single',
                'options': options,
                'answer': sorted(answer),
            })

    json.dump({'version': 1, 'count': len(questions), 'questions': questions},
              open(dest, 'w'), indent=1)
    print(f'wrote {len(questions)} questions -> {dest}')
    for src in srcs:
        print('  from', os.path.basename(src))
    print('  single:', sum(1 for q in questions if q['type'] == 'single'),
          ' multi:', sum(1 for q in questions if q['type'] == 'multi'))
    for name, i, b in repaired:
        print(f'  REPAIRED {name} row {i}: cells shifted one column left (type cell was {b!r})')
    if skipped:
        print(f'  SKIPPED {len(skipped)} rows:')
        for s in skipped:
            print('   %s row %s | %s | %s' % s)

# Default spreadsheet paths live in a gitignored file so no local paths end up in the repo.
# One path per line, in merge order, e.g.
#   /path/to/Net ExamTopics Adaptive Test 2.xlsx
#   /path/to/Net ExamTopics Adaptive Quiz 1.xlsx
LOCAL_SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources.local.txt')

if __name__ == '__main__':
    srcs = [a for a in sys.argv[1:] if a.endswith('.xlsx')]
    if not srcs and os.path.exists(LOCAL_SOURCES):
        srcs = [l.strip() for l in open(LOCAL_SOURCES) if l.strip() and not l.startswith('#')]
    if not srcs:
        sys.exit('usage: build_questions.py "/path/to/first.xlsx" ["/path/to/second.xlsx" ...] [out.json]\n'
                 '       (or list the paths in tools/sources.local.txt)')
    dests = [a for a in sys.argv[1:] if a.endswith('.json')]
    main(srcs, dests[0] if dests else 'data/questions.json')
