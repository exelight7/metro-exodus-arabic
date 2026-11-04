#!/usr/bin/env python3
"""
ue3_int_tool.py - export / import Unreal Engine 3 localization files (Localization/INT/*.int etc.).

Format: INI-like, UTF-16 LE with BOM (UTF-8/ANSI also read), [Section] then Key=Value.
Values may be quoted "..."; keys can repeat or be arrays (Key[0]=...). Comments start with ';'.
UE3 notes: do not quote values that use the line-break escape; missing keys fall back to INT.

  export  one or more .int files / folders -> CSV (file,section,key,occurrence,source,target,quoted)
  import  CSV -> rewritten files in an output folder; every other byte of the line is preserved
          (indentation, quotes, comments, line endings, BOM, encoding)

Usage
  ue3_int_tool.py export Localization/INT -o int_en.csv
  ue3_int_tool.py import Localization/INT int_ar.csv -o out/INT [--target-col target]
UE3 does NOT shape Arabic: run ar_shape.py (visual) on the target column first (and charset_remap.py
if the game's font has only 8-bit slots), or ship a font/Scaleform fix - see references/engines/unreal.md.
"""
import argparse
import csv
import io
import os
import re
import sys

LINE_RE = re.compile(r'^(?P<pre>\s*)(?P<key>[^=;\[\s][^=]*?)(?P<eq>\s*=\s*)(?P<val>.*?)(?P<post>\s*)$')


def read_text(path):
    raw = open(path, 'rb').read()
    if raw.startswith(b'\xff\xfe'):
        return raw[2:].decode('utf-16-le'), 'utf-16-le', b'\xff\xfe'
    if raw.startswith(b'\xfe\xff'):
        return raw[2:].decode('utf-16-be'), 'utf-16-be', b'\xfe\xff'
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw[3:].decode('utf-8'), 'utf-8', b'\xef\xbb\xbf'
    try:
        return raw.decode('utf-8'), 'utf-8', b''
    except UnicodeDecodeError:
        return raw.decode('cp1252'), 'cp1252', b''


def parse(text):
    """Yield (line_index, section, key, occurrence, match) for each Key=Value line."""
    section = ''
    seen = {}
    lines = text.split('\n')
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('[') and s.rstrip('\r').endswith(']'):
            section = s.rstrip('\r')[1:-1]
            continue
        if not s or s.startswith(';') or s.startswith('//'):
            continue
        m = LINE_RE.match(line.rstrip('\r'))
        if not m:
            continue
        k = (section, m.group('key'))
        seen[k] = seen.get(k, 0) + 1
        yield i, section, m.group('key'), seen[k], m
    return


def unquote(v):
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1], True
    return v, False


def files_of(path):
    if os.path.isfile(path):
        return [(os.path.dirname(path), os.path.basename(path))]
    out = []
    for root, _, fs in os.walk(path):
        for f in sorted(fs):
            if not f.lower().endswith(('.upk', '.u', '.bak', '.tfc', '.bin')):
                out.append((root, f))
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='UE3 .int export/import.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('path')
    e.add_argument('-o', '--output', required=True)
    i = sub.add_parser('import')
    i.add_argument('path')
    i.add_argument('csv')
    i.add_argument('-o', '--output', required=True)
    i.add_argument('--target-col', default='target')
    a = ap.parse_args()
    base = a.path if os.path.isdir(a.path) else os.path.dirname(a.path)

    if a.cmd == 'export':
        n = 0
        os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
        with open(a.output, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['file', 'section', 'key', 'occurrence', 'source', 'target', 'quoted'])
            for root, fn in files_of(a.path):
                rel = os.path.relpath(os.path.join(root, fn), base)
                text, _, _ = read_text(os.path.join(root, fn))
                for _, sec, key, occ, m in parse(text):
                    val, q = unquote(m.group('val'))
                    if not re.search(r'[A-Za-z\u0600-\u06ff]', val):
                        continue
                    w.writerow([rel, sec, key, occ, val, '', 'yes' if q else ''])
                    n += 1
        print('exported %d values -> %s' % (n, a.output))
        return 0

    with open(a.csv, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    tr = {}
    for r in rows:
        t = r.get(a.target_col, '')
        if t:
            tr[(r['file'], r['section'], r['key'], int(r['occurrence']))] = t
    done = 0
    warn = 0
    for root, fn in files_of(a.path):
        rel = os.path.relpath(os.path.join(root, fn), base)
        if not any(k[0] == rel for k in tr):
            continue
        text, enc, bom = read_text(os.path.join(root, fn))
        lines = text.split('\n')
        for li, sec, key, occ, m in list(parse(text)):
            t = tr.get((rel, sec, key, occ))
            if t is None:
                continue
            _, quoted = unquote(m.group('val'))
            if quoted and '\\n' in t:
                warn += 1
            t = t.replace('\r', '').replace('\n', '\\n')
            new_val = '"%s"' % t if quoted else t
            cr = '\r' if lines[li].endswith('\r') else ''
            lines[li] = m.group('pre') + m.group('key') + m.group('eq') + new_val + m.group('post') + cr
            done += 1
        dst = os.path.join(a.output, rel)
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(bom + '\n'.join(lines).encode(enc))
    print('imported %d values -> %s%s' % (done, a.output,
          ('  (WARNING: %d quoted values contain \\n - UE3 ignores the escape inside quotes)' % warn) if warn else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
