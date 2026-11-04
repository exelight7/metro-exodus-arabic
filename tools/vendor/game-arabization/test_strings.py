#!/usr/bin/env python3
"""
test_strings.py - the diagnostic test pack to inject BEFORE translating anything.

Each string has an ASCII marker [T01]..[T14] so you can match screenshot to string, and
each one exercises one thing: every letter in every position, lam-alef, numbers + Latin
inside Arabic, tags, placeholders, Arabic punctuation, harakat, a long line for
wrapping, multi-line, Persian letters.

Columns: id, purpose, logical (plain Arabic), visual (ar_shape default), forms (shape only),
reorder (bidi only). Inject ONE column at a time (start with logical) and read the screenshot
with references/arabic-shaping.md section 9.

Usage
  test_strings.py -o test_pack.csv
  test_strings.py -o test_pack.json --format json
  test_strings.py --print                 # show them
  test_strings.py -o t.csv --tag-style rpgmaker    # \\C[2]..\\C[0] instead of <color>
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import Shaper  # noqa: E402

DUAL = 'بتثجحخسشصضطظعغفقكلمنهيئ'
RIGHT = 'اأإآدذرزوؤة'


def build(tag_style):
    if tag_style == 'rpgmaker':
        col_open, col_close, ph1, ph2 = '\\C[2]', '\\C[0]', '\\N[1]', '\\V[1]'
    elif tag_style == 'renpy':
        col_open, col_close, ph1, ph2 = '{color=#ff0}', '{/color}', '[player]', '[count]'
    else:
        col_open, col_close, ph1, ph2 = '<color=#ffff00>', '</color>', '{0}', '{1}'
    rows = [
        ('T01', 'main probe: shaping + direction + numbers + brackets', 'لا سلام عليكم 123 (test)'),
        ('T02', 'dual-joining letters: isolated, initial-medial-final', ' '.join(c + ' ' + c * 3 for c in DUAL[:12])),
        ('T03', 'dual-joining letters (rest)', ' '.join(c + ' ' + c * 3 for c in DUAL[12:])),
        ('T04', 'right-joining letters after ب + hamza', ' '.join(c + ' ب' + c for c in RIGHT) + ' ء'),
        ('T05', 'lam-alef ligatures isolated and joined', 'لا ألا لأ سلأ لإ إلا لآ ملآن الله'),
        ('T06', 'numbers, percent, Latin name inside Arabic', 'النتيجة: 1,250 نقطة (95%) - اللاعب Sora'),
        ('T07', 'colour tag inside a word and around a word',
         'كل%sمة%s ملو%sنة%s هنا' % (col_open, col_close, col_open, col_close)),
        ('T08', 'placeholders', '%s حصل على %s قطعة' % (ph1, ph2)),
        ('T09', 'Arabic punctuation', 'هل أنت مستعد؟ نعم، لنبدأ؛ الآن!'),
        ('T10', 'harakat incl. shadda + fatha', 'علي\u064e\u0651 أن\u0652 أذهب\u064e الآن\u064e، شكرا\u064b'),
        ('T11', 'long line: engine wrapping / overflow',
         'هذه جملة طويلة جدا\u064b لاختبار التفاف النص داخل نافذة الحوار والتأكد من أن ترتيب الأسطر صحيح من الأعلى إلى الأسفل'),
        ('T12', 'two lines: line order', 'السطر الأول هنا\nالسطر الثاني هنا'),
        ('T13', 'tatweel and kashida', 'مـرحـبـا\u064b بـك'),
        ('T14', 'Persian/extra letters (only if needed)', 'پ چ ژ گ ک ی ڤ'),
    ]
    sv, sf, sr = Shaper(), Shaper(mode='forms'), Shaper(mode='reorder')
    if tag_style == 'rpgmaker':
        sv = Shaper(state_code=r'\\C\[(\d+)\]', state_default='0')
    out = []
    for tid, purpose, text in rows:
        marked = '[%s] %s' % (tid, text)
        out.append({'id': tid, 'purpose': purpose, 'logical': marked, 'visual': sv.process(marked),
                    'forms': sf.process(marked), 'reorder': sr.process(marked)})
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Arabic rendering diagnostic test pack.')
    ap.add_argument('-o', '--output')
    ap.add_argument('--format', choices=['csv', 'json', 'txt'], default=None)
    ap.add_argument('--tag-style', choices=['html', 'rpgmaker', 'renpy'], default='html')
    ap.add_argument('--column', default='logical', help='for txt output: which column')
    ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    rows = build(a.tag_style)
    if a.print or not a.output:
        for r in rows:
            print('%s  %-55s %s' % (r['id'], r['purpose'], r['logical'].replace('\n', ' / ')))
        if not a.output:
            return 0
    fmt = a.format or os.path.splitext(a.output)[1].lstrip('.').lower() or 'csv'
    if fmt == 'json':
        with open(a.output, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    elif fmt == 'txt':
        with open(a.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(r[a.column].replace('\n', '\\n') for r in rows) + '\n')
    else:
        with open(a.output, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print('wrote %s (%d strings, tag style %s)' % (a.output, len(rows), a.tag_style))
    return 0


if __name__ == '__main__':
    sys.exit(main())
