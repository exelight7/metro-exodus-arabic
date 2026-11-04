#!/usr/bin/env python3
"""
l10n_audit.py - automatic QA for an Arabic game translation table.

Catches the problems that break builds or embarrass a patch BEFORE anything is
injected into the game:

 ERROR  tags/placeholders differ from the source ({0} %s <color> \\C[2] ...)
 ERROR  glossary term missing / forbidden variant used
 ERROR  pre-shaped presentation forms inside the translation (keep the table logical!)
 WARN   untranslated (empty or identical to source)
 WARN   too long: chars ratio > --max-ratio (default 1.3) or pixel width > limit
 WARN   numbers differ from the source
 WARN   invisible / bidi control characters (RLM, ZWJ, BOM, NBSP ...)
 WARN   Persian letters (ی ک) instead of Arabic (ي ك)
 WARN   colloquial words in a Fusha translation (ليش إيش عشان ...), --allow-dialect to skip
 WARN   common spelling errors (إستخدم -> استخدم, فى -> في, لاكن -> لكن ...)
 WARN   leading/trailing whitespace differs from the source
 INFO   Latin ? , ; inside Arabic (use ؟ ، ؛ if the font has them)
 INFO   harakat present (decide once if the engine can draw them)
 INFO   double spaces, tatweel, line-count differs
 INFO   same source translated in different ways (consistency)

Usage
  l10n_audit.py strings.csv --source-col en --target-col ar --id-col id
  l10n_audit.py strings.json --glossary glossary.csv --font ar.ttf --size 28 --max-px 600
  l10n_audit.py game.po --report audit.md --issues issues.csv
Glossary CSV columns: source,target[,forbidden]   (forbidden = variants separated by |)
Exit code 1 when any ERROR exists (use --no-fail to always exit 0).
"""
import argparse
import collections
import csv
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import DEFAULT_TAG_PATTERNS, Shaper  # noqa: E402
from l10n_io import load_table  # noqa: E402

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError, ImportError):
    pass

AR = r'\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff'
# letters + harakat only (NOT the Arabic comma/semicolon/question mark or digits): whole-word matching
AR_WORD = r'\u0621-\u065f\u0670-\u06d3\u06fa-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufefc'
NOT_AR_BEFORE = r'(?<![%s])' % AR_WORD
NOT_AR_AFTER = r'(?![%s])' % AR_WORD

DIALECT = ['ليش', 'ليه', 'إيش', 'ايش', 'وش', 'شو', 'شنو', 'عشان', 'علشان', 'هذول', 'هذولا', 'اللي',
           'يبغى', 'أبغى', 'ابغى', 'بدي', 'الحين', 'دحين', 'ذحين', 'يلا', 'بس', 'كمان', 'هيك', 'كده',
           'ازاي', 'إزاي', 'فين', 'امتى', 'إمتى', 'مو', 'مب', 'هالحين', 'وايد', 'تبي', 'يبي']
# wrong -> right (whole word, optional و/ف prefix). Only unambiguous cases.
SPELLING = {
    'إستخدم': 'استخدم', 'إختر': 'اختر', 'إبحث': 'ابحث', 'إذهب': 'اذهب', 'إنتظر': 'انتظر',
    'إنتبه': 'انتبه', 'إضغط': 'اضغط', 'إستمر': 'استمر', 'إنطلق': 'انطلق',
    'إجمع': 'اجمع', 'إفتح': 'افتح', 'إنقر': 'انقر', 'إستعد': 'استعد',
    'إختيار': 'اختيار', 'إستخدام': 'استخدام', 'إنتظار': 'انتظار', 'إنتقال': 'انتقال',
    'إستمرار': 'استمرار', 'إستعادة': 'استعادة', 'إنتهى': 'انتهى', 'إنتهت': 'انتهت', 'إبدأ': 'ابدأ',
    'لاكن': 'لكن', 'هاذا': 'هذا', 'هاذه': 'هذه', 'ذالك': 'ذلك', 'هاكذا': 'هكذا',
    'انشاء الله': 'إن شاء الله', 'إنشاء الله': 'إن شاء الله',
    'فى': 'في', 'الذى': 'الذي', 'التى': 'التي', 'هى': 'هي',
    'مسؤل': 'مسؤول', 'شيئ': 'شيء',
}
INVISIBLE = {'\u200b': 'ZERO WIDTH SPACE', '\u200c': 'ZWNJ', '\u200d': 'ZWJ', '\u200e': 'LRM',
             '\u200f': 'RLM', '\u061c': 'ALM', '\u202a': 'LRE', '\u202b': 'RLE', '\u202c': 'PDF',
             '\u202d': 'LRO', '\u202e': 'RLO', '\u2066': 'LRI', '\u2067': 'RLI', '\u2068': 'FSI',
             '\u2069': 'PDI', '\ufeff': 'BOM', '\u00a0': 'NBSP', '\u00ad': 'SOFT HYPHEN'}


def norm_ar(s):
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn' and c != 'ـ')
    return s.translate(str.maketrans('أإآٱ', 'اااا'))


def visible_len(s, tag_re):
    s = tag_re.sub('', s)
    return sum(1 for c in s if unicodedata.category(c) not in ('Mn', 'Me', 'Cf', 'Cc'))


class Audit:
    def __init__(self, a):
        self.a = a
        pats = DEFAULT_TAG_PATTERNS + a.tag
        self.tag_re = re.compile('|'.join('(?:%s)' % p for p in pats))
        self.issues = []
        self.glossary = []
        if a.glossary:
            with open(a.glossary, encoding='utf-8-sig', newline='') as f:
                for r in csv.DictReader(f):
                    src = (r.get('source') or '').strip()
                    if src:
                        self.glossary.append((src, (r.get('target') or '').strip(),
                                              [v.strip() for v in (r.get('forbidden') or '').split('|') if v.strip()]))
        self.dialect = [] if a.allow_dialect else list(DIALECT)
        if a.dialect_list:
            with open(a.dialect_list, encoding='utf-8-sig') as f:
                self.dialect += [w.strip() for w in f if w.strip()]
        self.font = None
        if a.font:
            from PIL import ImageFont
            self.font = ImageFont.truetype(a.font, a.size or 32, layout_engine=ImageFont.Layout.BASIC)
            self.forms = Shaper(mode='forms')
        self.word_re = {w: re.compile(NOT_AR_BEFORE + '[وف]?' + re.escape(w) + NOT_AR_AFTER)
                        for w in set(self.dialect) | set(SPELLING)}

    def add(self, row, sev, check, msg):
        self.issues.append({'id': row['id'], 'line': row['line'], 'severity': sev, 'check': check,
                            'message': msg, 'source': row['source'], 'target': row['target']})

    def px(self, text):
        lines = re.split(r'\r?\n|\\n', self.tag_re.sub('', self.forms.process(text)))
        return max(self.font.getlength(l) for l in lines) if lines else 0

    def check(self, row):
        a, src, tgt = self.a, row['source'], row['target']
        if not tgt.strip():
            if src.strip():
                self.add(row, 'WARN', 'untranslated', 'empty translation')
            return
        if src and tgt.strip() == src.strip() and re.search('[A-Za-z]{3,}', src):
            self.add(row, 'WARN', 'untranslated', 'identical to source')
        if src:
            ts, tt = collections.Counter(self.tag_re.findall(src)), collections.Counter(self.tag_re.findall(tgt))
            if ts != tt:
                missing = list((ts - tt).elements())
                extra = list((tt - ts).elements())
                self.add(row, 'ERROR', 'tags', 'missing %s extra %s' % (missing or '-', extra or '-'))
            ns = sorted(re.findall(r'\d+(?:[.,]\d+)?', self.tag_re.sub('', src)))
            nt = sorted(re.findall(r'\d+(?:[.,]\d+)?', self.tag_re.sub('', tgt).translate(
                str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))))
            if ns != nt:
                self.add(row, 'WARN', 'numbers', 'source %s / target %s' % (ns, nt))
            ls, lt = visible_len(src, self.tag_re), visible_len(tgt, self.tag_re)
            if ls >= 4 and lt > ls * a.max_ratio:
                self.add(row, 'WARN', 'length', '%d vs %d chars (%.0f%% of source, limit %.0f%%)' %
                         (lt, ls, 100.0 * lt / ls, a.max_ratio * 100))
            if (src[:1].isspace(), src[-1:].isspace()) != (tgt[:1].isspace(), tgt[-1:].isspace()):
                self.add(row, 'WARN', 'whitespace', 'leading/trailing spaces differ from source')
            cs = len(re.findall(r'\r?\n|\\n', src))
            ct = len(re.findall(r'\r?\n|\\n', tgt))
            if cs != ct:
                self.add(row, 'INFO', 'line-breaks', 'source has %d line breaks, target %d' % (cs, ct))
        if self.font is not None:
            w = self.px(tgt)
            limit = a.max_px
            if row.get('maxpx'):
                limit = float(row['maxpx'])
            if limit and w > limit:
                self.add(row, 'WARN', 'width', '%.0f px > %.0f px' % (w, limit))
        if re.search('[\ufb50-\ufdff\ufe70-\ufeff]', tgt):
            self.add(row, 'ERROR', 'pre-shaped', 'presentation forms found - the table must stay logical '
                                                 'Arabic; shape at build time with ar_shape.py')
        inv = sorted({INVISIBLE[c] for c in tgt if c in INVISIBLE})
        if inv:
            self.add(row, 'WARN', 'invisible', ', '.join(inv))
        if re.search('[یک]', tgt):
            self.add(row, 'WARN', 'persian-letters', 'ی/ک found - use ي/ك (or ar_shape.py --normalize-persian)')
        plain = self.tag_re.sub('', tgt)
        for w in self.dialect:
            if self.word_re[w].search(plain):
                self.add(row, 'WARN', 'dialect', 'colloquial word: %s' % w)
        for w, right in SPELLING.items():
            if self.word_re[w].search(plain):
                self.add(row, 'WARN', 'spelling', '%s -> %s' % (w, right))
        if re.search('[%s][^A-Za-z]{0,3}[?,;]' % AR, plain) or re.search('[?,;][^A-Za-z]{0,3}[%s]' % AR, plain):
            self.add(row, 'INFO', 'punctuation', 'Latin ? , ; next to Arabic (؟ ، ؛ if the font has them)')
        if re.search('[\u064b-\u0652\u0670]', plain):
            self.add(row, 'INFO', 'harakat', 'harakat present')
        if '  ' in tgt.strip():
            self.add(row, 'INFO', 'double-space', 'double space')
        if 'ـ' in plain:
            self.add(row, 'INFO', 'tatweel', 'tatweel present')
        ntgt = norm_ar(tgt)
        for term, want, forbidden in self.glossary:
            if re.search(r'(?<![A-Za-z])' + re.escape(term) + r'(?![A-Za-z])', src, re.I):
                if want and norm_ar(want) not in ntgt:
                    self.add(row, 'ERROR', 'glossary', '"%s" must be "%s"' % (term, want))
                for v in forbidden:
                    if norm_ar(v) in ntgt:
                        self.add(row, 'ERROR', 'glossary', '"%s" uses forbidden variant "%s"' % (term, v))

    def consistency(self, rows):
        by_src = collections.defaultdict(collections.Counter)
        ids = collections.defaultdict(list)
        for r in rows:
            if r['source'].strip() and r['target'].strip():
                k = r['source'].strip().lower()
                by_src[k][r['target'].strip()] += 1
                ids[k].append(r['id'])
        out = []
        for k, c in by_src.items():
            if len(c) > 1:
                out.append((k, c, ids[k]))
        return sorted(out, key=lambda x: -sum(x[1].values()))


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='QA checks for an Arabic game translation table.')
    ap.add_argument('table')
    ap.add_argument('--id-col')
    ap.add_argument('--source-col')
    ap.add_argument('--target-col')
    ap.add_argument('--json-key-re')
    ap.add_argument('--glossary')
    ap.add_argument('--max-ratio', type=float, default=1.3, help='target/source visible length (default 1.3)')
    ap.add_argument('--font', help='font for pixel width check (pre-shaped glyph widths)')
    ap.add_argument('--size', type=int, help='font size in px for --font')
    ap.add_argument('--max-px', type=float, help='max line width in px (or a "maxpx" column per row)')
    ap.add_argument('--tag', action='append', default=[], help='extra tag/placeholder regex')
    ap.add_argument('--allow-dialect', action='store_true')
    ap.add_argument('--dialect-list', help='extra colloquial words, one per line')
    ap.add_argument('--report', help='write Markdown report here')
    ap.add_argument('--issues', help='write all issues as CSV here')
    ap.add_argument('--max-examples', type=int, default=8)
    ap.add_argument('--no-fail', action='store_true')
    a = ap.parse_args()

    rows = load_table(a.table, a.id_col, a.source_col, a.target_col, a.json_key_re)
    au = Audit(a)
    for r in rows:
        au.check(r)
    cons = au.consistency(rows)

    sev_order = {'ERROR': 0, 'WARN': 1, 'INFO': 2}
    by_check = collections.OrderedDict()
    for i in sorted(au.issues, key=lambda x: (sev_order[x['severity']], x['check'])):
        by_check.setdefault((i['severity'], i['check']), []).append(i)
    counts = collections.Counter(i['severity'] for i in au.issues)
    md = ['# Translation audit: %s' % os.path.basename(a.table), '',
          '%d rows | %d ERROR | %d WARN | %d INFO | %d inconsistent sources' % (
              len(rows), counts['ERROR'], counts['WARN'], counts['INFO'], len(cons)), '']
    for (sev, chk), items in by_check.items():
        md.append('## %s %s (%d)' % (sev, chk, len(items)))
        for i in items[:a.max_examples]:
            md.append('- `%s` %s  \n  EN: %s  \n  AR: %s' % (i['id'], i['message'], i['source'][:120], i['target'][:120]))
        if len(items) > a.max_examples:
            md.append('- ... %d more (see --issues CSV)' % (len(items) - a.max_examples))
        md.append('')
    if cons:
        md.append('## INFO consistency: same source, different translations (%d)' % len(cons))
        for k, c, ids in cons[:a.max_examples * 2]:
            md.append('- "%s" -> %s  (ids: %s)' % (k[:60], ' | '.join('%s ×%d' % (t, n) for t, n in c.most_common()),
                                                  ', '.join(ids[:6])))
        md.append('')
    text = '\n'.join(md)
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print('report: %s' % a.report)
    else:
        print(text)
    if a.issues:
        with open(a.issues, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['severity', 'check', 'id', 'line', 'message', 'source', 'target'])
            w.writeheader()
            w.writerows(au.issues)
        print('issues: %s' % a.issues)
    print('summary: %d rows, %d ERROR, %d WARN, %d INFO' % (len(rows), counts['ERROR'], counts['WARN'], counts['INFO']))
    return 1 if counts['ERROR'] and not a.no_fail else 0


if __name__ == '__main__':
    sys.exit(main())
