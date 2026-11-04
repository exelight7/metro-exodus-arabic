#!/usr/bin/env python3
"""
l10n_io.py - shared loaders for translation tables (used by l10n_audit.py and font_check.py).

Formats
  .csv / .tsv   header row required; pick columns by name
  .json         list of objects, or {id: {...}}, or {id: "text"}; nested values are walked
  .po / .pot    gettext (msgctxt|msgid used as id, msgid = source, msgstr = target)
  .txt          one string per line (target only)
Every loader returns a list of dicts: {'id', 'source', 'target', 'line'}.
"""
import csv
import io
import json
import os
import re


def _read(path):
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


def _sniff(path, data):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.tsv', '.tab'):
        return '\t'
    try:
        return csv.Sniffer().sniff(data[:8192], delimiters=',;\t|').delimiter
    except csv.Error:
        return ','


def po_unescape(s):
    table = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}
    return re.sub(r'\\(.)', lambda m: table.get(m.group(1), '\\' + m.group(1)), s)


def load_po(data):
    rows, cur, key, line_no = [], {}, None, 0

    def flush():
        if cur.get('msgid'):                      # skips the PO header (empty msgid)
            rows.append({'id': (cur.get('msgctxt', '') + '|' if cur.get('msgctxt') else '') + cur['msgid'][:60],
                         'source': cur['msgid'], 'target': cur.get('msgstr', ''), 'line': cur.get('_line', 0)})
    for line_no, raw in enumerate(data.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            if not line and cur:
                flush()
                cur, key = {}, None
            continue
        m = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+"(.*)"$', line)
        if m:
            k = m.group(1)
            if k == 'msgid' and 'msgid' in cur:
                flush()
                cur = {}
            key = 'msgstr' if k.startswith('msgstr') else ('msgid_plural' if k == 'msgid_plural' else k)
            if key == 'msgstr' and cur.get('msgstr'):
                key = '_extra'                     # plural forms: keep the first only
            cur.setdefault('_line', line_no)
            cur[key] = po_unescape(m.group(2))
        elif line.startswith('"') and key:
            cur[key] = cur.get(key, '') + po_unescape(line[1:-1])
    flush()
    return rows


def load_table(path, id_col=None, src_col=None, tgt_col=None, key_re=None):
    data = _read(path)
    ext = os.path.splitext(path)[1].lower()
    rows = []
    if ext in ('.po', '.pot'):
        return load_po(data)
    if ext in ('.csv', '.tsv', '.tab'):
        reader = csv.DictReader(io.StringIO(data), delimiter=_sniff(path, data))
        cols = reader.fieldnames or []

        def pick(want, guesses):
            if want:
                if want not in cols:
                    raise SystemExit('column %r not in %s' % (want, cols))
                return want
            for g in guesses:
                for c in cols:
                    if c.lower() == g:
                        return c
            return None
        ic = pick(id_col, ('id', 'key', 'label', 'name'))
        sc = pick(src_col, ('source', 'en', 'english', 'original', 'src'))
        tc = pick(tgt_col, ('target', 'ar', 'arabic', 'translation', 'tgt'))
        for n, r in enumerate(reader, 2):
            rows.append({'id': r.get(ic, '') if ic else str(n), 'source': r.get(sc, '') if sc else '',
                         'target': r.get(tc, '') if tc else '', 'line': n})
        return rows
    if ext == '.json':
        obj = json.loads(data)
        kr = re.compile(key_re) if key_re else None
        sc, tc = src_col or 'source', tgt_col or 'target'
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and (sc in obj[0] or tc in obj[0]):
            for n, o in enumerate(obj):
                rows.append({'id': str(o.get(id_col or 'id', n)), 'source': str(o.get(sc, '') or ''),
                             'target': str(o.get(tc, '') or ''), 'line': n})
            return rows
        if isinstance(obj, dict) and obj and all(isinstance(v, dict) for v in obj.values()) \
                and any(sc in v or tc in v for v in obj.values()):
            for k, o in obj.items():
                rows.append({'id': k, 'source': str(o.get(sc, '') or ''), 'target': str(o.get(tc, '') or ''),
                             'line': 0})
            return rows

        def walk(o, path_):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path_ + [str(k)])
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, path_ + [str(i)])
            elif isinstance(o, str):
                last = next((p for p in reversed(path_) if not p.isdigit()), '')
                if kr is None or kr.search(last):
                    rows.append({'id': '/'.join(path_), 'source': '', 'target': o, 'line': 0})
        walk(obj, [])
        return rows
    for n, line in enumerate(data.splitlines(), 1):
        rows.append({'id': str(n), 'source': '', 'target': line, 'line': n})
    return rows


def load_strings(path, column=None, key_re=None):
    """Just the target-language strings (for font coverage)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv', '.tsv', '.tab') and column is None:
        data = _read(path)
        return [c for r in csv.reader(io.StringIO(data), delimiter=_sniff(path, data)) for c in r if c]
    rows = load_table(path, tgt_col=column, key_re=key_re)
    return [r['target'] for r in rows if r['target']]
