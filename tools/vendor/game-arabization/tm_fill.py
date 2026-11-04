#!/usr/bin/env python3
"""
tm_fill.py - translation memory: fill a new export from translations you already have.

Huge time saver after a game update (IDs shift, new lines appear), for repeated lines
(UI words, item names used in many places) and when moving between tools (unity_text,
locres_tool, ue3_int_tool, l10n_io formats all have source/target columns).

Match order per row with an empty target:
  1. same id            (only if the source text is still identical)
  2. same source text   (exact; most frequent translation wins, conflicts reported)
  3. --fuzzy            similar source (difflib >= --min-ratio), marked "REVIEW" in a status column
Never overwrites a non-empty target. Writes a report of what was filled from where.

Usage
  tm_fill.py new_export.csv --tm old_translated.csv [--tm glossary_like.csv] -o filled.csv
  tm_fill.py new.csv --tm v1_ar.csv --fuzzy --min-ratio 0.9 -o filled.csv
Columns: --source-col (default source), --target-col (default target), --id-col (default auto:
the first key set present in table and TM - id | namespace,key | file,section,key,occurrence;
comma list for a composite key).
Status (L10N-STD tables): the TM row's "status" (and empty notes/context/speaker) is carried over:
by id = as is, exact source = "final" becomes "reviewed" (other context), fuzzy = "draft".
In-place is fine: -o may be the same file as a --tm (all input is read before writing).
"""
import argparse
import collections
import csv
import difflib
import os
import sys

KEY_SETS = [['id'], ['namespace', 'key'], ['file', 'section', 'key', 'occurrence'], ['key']]
CARRY = ['notes', 'context', 'speaker']


def read(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Fill translations from translation memories.')
    ap.add_argument('table')
    ap.add_argument('--tm', action='append', required=True, help='translated CSV(s), earlier = higher priority')
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--id-col', default='auto', help='auto | column | comma list (composite key)')
    ap.add_argument('--source-col', default='source')
    ap.add_argument('--target-col', default='target')
    ap.add_argument('--fuzzy', action='store_true')
    ap.add_argument('--min-ratio', type=float, default=0.9)
    a = ap.parse_args()
    cols, rows = read(a.table)
    tms = [read(tm) for tm in a.tm]
    if a.id_col == 'auto':
        idc = next((ks for ks in KEY_SETS if all(k in cols for k in ks) and all(all(k in h for k in ks) for h, _ in tms)), ['id'])
    else:
        idc = [c.strip() for c in a.id_col.split(',')]

    def key(r):
        return tuple(r.get(c, '') or '' for c in idc)
    by_id, by_src, src_row = {}, collections.defaultdict(collections.Counter), {}
    for _, trows in tms:
        for r in trows:
            t = (r.get(a.target_col) or '').strip()
            s = r.get(a.source_col) or ''
            if not t:
                continue
            by_id.setdefault(key(r), (s, t, r))
            by_src[s.strip()][t] += 1
            src_row.setdefault((s.strip(), t), r)
    carry_status = any('status' in h for h, _ in tms)
    if carry_status and 'status' not in cols:
        cols = cols + ['status']
    if 'tm_status' not in cols:
        cols = cols + ['tm_status']

    def carry(r, src, how):
        if carry_status:
            st = (src.get('status') or '').strip().lower() if src else ''
            if how == 'fuzzy':
                st = 'draft'
            elif how == 'exact' and st == 'final':
                st = 'reviewed'
            if st and not (r.get('status') or '').strip():
                r['status'] = st
        for c in CARRY:
            if src and c in cols and not (r.get(c) or '').strip() and (src.get(c) or '').strip():
                r[c] = src[c]
    stats = collections.Counter()
    conflicts = []
    srcs = list(by_src)
    for r in rows:
        if (r.get(a.target_col) or '').strip():
            stats['already translated'] += 1
            continue
        s = (r.get(a.source_col) or '').strip()
        hit = by_id.get(key(r))
        if hit and hit[0].strip() == s:
            r[a.target_col], r['tm_status'] = hit[1], 'id'
            carry(r, hit[2], 'id')
            stats['by id'] += 1
            continue
        if s in by_src:
            c = by_src[s]
            r[a.target_col], r['tm_status'] = c.most_common(1)[0][0], 'exact'
            carry(r, src_row.get((s, r[a.target_col])), 'exact')
            if len(c) > 1:
                conflicts.append((s, c))
            stats['exact source'] += 1
            continue
        if a.fuzzy and s:
            best = difflib.get_close_matches(s, srcs, n=1, cutoff=a.min_ratio)
            if best:
                r[a.target_col] = by_src[best[0]].most_common(1)[0][0]
                r['tm_status'] = 'REVIEW fuzzy: %s' % best[0][:60]
                carry(r, None, 'fuzzy')
                stats['fuzzy (review!)'] += 1
                continue
        stats['still empty'] += 1
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('rows %d (key %s): %s -> %s' % (len(rows), '+'.join(idc), ', '.join('%s %d' % kv for kv in stats.items()), a.output))
    seen = set()
    for s, c in conflicts:
        if s in seen:
            continue
        seen.add(s)
        print('  conflict "%s": %s' % (s[:50], ' | '.join('%s x%d' % kv for kv in c.most_common())))
        if len(seen) >= 10:
            break
    return 0


if __name__ == '__main__':
    sys.exit(main())
