#!/usr/bin/env python3
"""
mojibake.py - diagnose garbled Arabic: which encoding mistake produced it?

Typical game symptoms and what they mean:
  Ø³Ù„Ø§Ù…       UTF-8 bytes read as Windows-1252/Latin-1  -> the game reads ANSI, not UTF-8
  ????             text was converted to a code page without Arabic (lossy, data gone)
  ÓáÇã             Windows-1256 (Arabic ANSI) bytes read as Windows-1252
  楳漠 / s.l.a.m   UTF-16 read as UTF-8 / wrong byte order
  □□□ (boxes)      NOT an encoding problem: the font lacks the glyphs (font_check.py)

Usage
  mojibake.py "Ø³Ù„Ø§Ù…"                 # paste the garbled text (from the game file, OCR, log)
  mojibake.py --file strings_ar.txt         # sniff a file's bytes: BOM, UTF-8 validity, UTF-16, cp1256
It tries every (shown-as, really-is) pair and ranks the ones that turn the text into Arabic.
"""
import argparse
import sys
import unicodedata

ENCODINGS = ['utf-8', 'cp1252', 'latin-1', 'cp1256', 'iso8859-6', 'cp437', 'cp850', 'shift_jis',
             'gbk', 'utf-16-le', 'utf-16-be', 'mac_roman', 'cp1251']


def arabic_score(s):
    if not s:
        return 0.0
    letters = sum(1 for c in s if 'ء' <= c <= 'ي' or '\ufe70' <= c <= '\ufefc')
    bad = sum(1 for c in s if c == '�' or (unicodedata.category(c) in ('Cc', 'Co', 'Cn') and c not in '\r\n\t'))
    spaces = s.count(' ')
    return (letters + spaces * 0.5 - bad * 3) / len(s)


def try_text(text):
    res = []
    if '?' in text and text.replace('?', '').replace(' ', '') == '':
        print('only question marks: the text was converted to a code page WITHOUT Arabic. The original is lost;'
              ' re-export from the UTF-8 source with the right encoding (or use charset_remap.py for 8-bit engines).')
        return
    for shown in ENCODINGS:
        try:
            raw = text.encode(shown)
        except (UnicodeEncodeError, LookupError):
            continue
        for real in ENCODINGS:
            if real == shown:
                continue
            try:
                fixed = raw.decode(real)
            except (UnicodeDecodeError, LookupError):
                continue
            sc = arabic_score(fixed)
            if sc > 0.3:
                res.append((sc, shown, real, fixed))
    if not res:
        print('no single mis-decoding explains it. If you see boxes, it is the FONT (font_check.py); '
              'if letters are right but disconnected/reversed, it is SHAPING (ar_shape.py).')
        return
    res.sort(key=lambda r: -r[0])
    seen = set()
    print('most likely explanations (bytes were REALLY in X but SHOWN as Y):')
    for sc, shown, real, fixed in res:
        if fixed in seen:
            continue
        seen.add(fixed)
        print('  real %-10s shown as %-10s score %.2f  ->  %s' % (real, shown, sc, fixed[:60]))
        if len(seen) >= 5:
            break
    best = res[0]
    print('\nmeaning: the game/tool decodes the file as %s, but it was written as %s.' % (best[1], best[2]))
    print('fix: write the file in the encoding the game expects (%s), if it can represent Arabic;' % best[1])
    print('     otherwise the engine is 8-bit -> charset_remap.py, or find the setting/BOM that makes it read %s.'
          % best[2])


def sniff_file(path):
    with open(path, 'rb') as f:
        b = f.read()
    print('%s: %d bytes' % (path, len(b)))
    if b.startswith(b'\xef\xbb\xbf'):
        print('BOM: UTF-8 with BOM (some engines need it, some show it as junk "ï»¿" at the start)')
    elif b.startswith(b'\xff\xfe'):
        print('BOM: UTF-16 LE')
    elif b.startswith(b'\xfe\xff'):
        print('BOM: UTF-16 BE')
    for enc in ('utf-8', 'utf-16-le', 'utf-16-be', 'cp1256'):
        try:
            s = b.decode(enc)
        except UnicodeDecodeError:
            print('  %-9s invalid' % enc)
            continue
        print('  %-9s valid, Arabic score %.2f, sample: %s' % (enc, arabic_score(s[:2000]), s[:50].replace('\n', ' ')))
    odd = b[1:4001:2]
    if odd and (odd.count(0) + odd.count(6)) > len(odd) * 0.6:
        print('  pattern: every second byte is 00/06 -> UTF-16 LE text')


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Diagnose garbled (mojibake) Arabic text.')
    ap.add_argument('text', nargs='*')
    ap.add_argument('--file')
    a = ap.parse_args()
    if a.file:
        sniff_file(a.file)
    if a.text:
        try_text(' '.join(a.text))
    if not a.file and not a.text:
        ap.error('give garbled text or --file')


if __name__ == '__main__':
    main()
