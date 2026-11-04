#!/usr/bin/env python3
"""
make_ass.py - build an Arabic .ass subtitle file (for burning into cutscenes with
burn_subs.py / ffmpeg+libass, or for engines/players that read ASS/SRT directly).

libass shapes Arabic with HarfBuzz and reorders with FriBidi, so the text stays LOGICAL
here (do NOT run ar_shape.py on it). Each line starts with an RLM so a line that begins
with a number or a Latin name is still laid out right-to-left (punctuation on the left).

Input: CSV/TSV with start,end and a text column (hardsub_ocr.py output after translation),
       or an .srt file. Times: 00:01:02,345 | 00:01:02.345 | 1:02.3 | 62.345
Usage
  make_ass.py subs.csv -o subs.ass --res 1920x1080 --font "Noto Sans Arabic" --size 54
  make_ass.py subs.csv -o subs.ass --text-col target --box          (opaque box behind text)
  make_ass.py arabic.srt -o arabic.ass --margin-v 80 --outline 3
  make_ass.py subs.csv -o subs.ass --fontfile NotoSansArabic.ttf --em-size 44   (match a 44px game font)
Size note: ASS Fontsize is the LINE height from the font's win metrics. Arabic fonts are tall,
so the same number looks much smaller than in the game. Use --em-size + --fontfile.
"""
import argparse
import csv
import io
import os
import re
import sys

RLM = '‏'


def parse_time(t):
    t = t.strip().replace(',', '.')
    if re.fullmatch(r'\d+(\.\d+)?', t):
        return float(t)
    parts = t.split(':')
    sec = float(parts[-1])
    mins = int(parts[-2]) if len(parts) >= 2 else 0
    hrs = int(parts[-3]) if len(parts) >= 3 else 0
    return hrs * 3600 + mins * 60 + sec


def ass_time(s):
    cs = int(round(s * 100))
    return '%d:%02d:%02d.%02d' % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def load(path, text_col, start_col, end_col):
    with open(path, encoding='utf-8-sig') as f:
        data = f.read()
    rows = []
    if path.lower().endswith('.srt'):
        for block in re.split(r'\n\s*\n', data.strip()):
            lines = block.strip().splitlines()
            m = next((i for i, l in enumerate(lines) if '-->' in l), None)
            if m is None:
                continue
            s, e = [x.strip() for x in lines[m].split('-->')]
            rows.append((parse_time(s), parse_time(e.split()[0]), '\n'.join(lines[m + 1:])))
        return rows
    delim = '\t' if path.lower().endswith(('.tsv', '.tab')) else ','
    reader = csv.DictReader(io.StringIO(data), delimiter=delim)
    cols = reader.fieldnames or []
    tc = text_col or next((c for c in ('target', 'ar', 'arabic', 'text', 'translation') if c in cols), None)
    if tc is None:
        sys.exit('no text column found in %s (columns: %s) - use --text-col' % (path, cols))
    for r in reader:
        txt = (r.get(tc) or '').strip()
        if txt:
            rows.append((parse_time(r[start_col]), parse_time(r[end_col]), txt))
    return rows


def ass_color(hexrgb, alpha=0):
    hexrgb = hexrgb.lstrip('#')
    r, g, b = hexrgb[0:2], hexrgb[2:4], hexrgb[4:6]
    return '&H%02X%s%s%s' % (alpha, b.upper(), g.upper(), r.upper())


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Make an Arabic ASS subtitle file.')
    ap.add_argument('input')
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--text-col')
    ap.add_argument('--start-col', default='start')
    ap.add_argument('--end-col', default='end')
    ap.add_argument('--res', default='1920x1080', help='video resolution (PlayResX x PlayResY)')
    ap.add_argument('--font', default='Noto Sans Arabic', help='font FAMILY name (installed or in --fontsdir of burn_subs)')
    ap.add_argument('--size', type=int, default=0, help='ASS Fontsize = LINE height in px (default: 7%% of height)')
    ap.add_argument('--fontfile', help='the .ttf/.otf itself: lets --em-size compensate for tall Arabic metrics')
    ap.add_argument('--em-size', type=float, help='wanted em size in px (like a game/ffmpeg font size); needs --fontfile')
    ap.add_argument('--color', default='FFFFFF', help='text colour RRGGBB')
    ap.add_argument('--outline-color', default='000000')
    ap.add_argument('--outline', type=float, default=3)
    ap.add_argument('--shadow', type=float, default=1)
    ap.add_argument('--bold', action='store_true')
    ap.add_argument('--margin-v', type=int, default=0, help='bottom margin in px (default: 6%% of height)')
    ap.add_argument('--align', type=int, default=2, help='numpad alignment: 2 bottom-centre, 8 top-centre')
    ap.add_argument('--box', action='store_true', help='opaque box behind each line (BorderStyle 3)')
    ap.add_argument('--box-color', default='000000')
    ap.add_argument('--box-alpha', type=int, default=0x40, help='box transparency 0 (solid) - 255 (invisible)')
    ap.add_argument('--no-rlm', action='store_true', help='do not prefix lines with U+200F')
    ap.add_argument('--offset', type=float, default=0.0, help='shift all times by N seconds')
    a = ap.parse_args()

    W, H = [int(v) for v in a.res.lower().split('x')]
    size = a.size or round(H * 0.07)
    if a.em_size:
        if not a.fontfile:
            ap.error('--em-size needs --fontfile')
        from fontTools.ttLib import TTFont
        f = TTFont(a.fontfile, fontNumber=0)
        os2, upem = f['OS/2'], f['head'].unitsPerEm
        # libass (like VSFilter) scales so that usWinAscent+usWinDescent == Fontsize
        ratio = (os2.usWinAscent + os2.usWinDescent) / upem
        size = round(a.em_size * ratio)
        print('em %.0fpx x line-height ratio %.2f (win %d+%d / %d) -> ASS Fontsize %d'
              % (a.em_size, ratio, os2.usWinAscent, os2.usWinDescent, upem, size))
    margin_v = a.margin_v or round(H * 0.06)
    rows = load(a.input, a.text_col, a.start_col, a.end_col)
    if a.box:
        style_border, outline_c, back_c = 3, ass_color(a.box_color, a.box_alpha), ass_color(a.box_color, a.box_alpha)
        outline = max(a.outline, 8)
    else:
        style_border, outline_c, back_c = 1, ass_color(a.outline_color), ass_color('000000', 0x80)
        outline = a.outline
    out = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: %d' % W, 'PlayResY: %d' % H, 'WrapStyle: 0',
           'ScaledBorderAndShadow: yes', 'YCbCr Matrix: TV.709', '',
           '[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, '
           'Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, '
           'MarginL, MarginR, MarginV, Encoding',
           'Style: Default,%s,%d,%s,&H000000FF,%s,%s,%d,0,0,0,100,100,0,0,%d,%g,%g,%d,%d,%d,%d,1' % (
               a.font, size, ass_color(a.color), outline_c, back_c, -1 if a.bold else 0, style_border, outline,
               a.shadow, a.align, round(W * 0.06), round(W * 0.06), margin_v),
           '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    warned = False
    for s, e, txt in rows:
        if '{' in txt or '}' in txt:
            if not warned:
                print('note: { } removed (they start ASS override blocks)')
                warned = True
            txt = txt.replace('{', '(').replace('}', ')')
        lines = re.split(r'\r?\n|\\n|\\N', txt)
        if not a.no_rlm:
            lines = [RLM + l if not l.startswith(RLM) else l for l in lines]
        out.append('Dialogue: 0,%s,%s,Default,,0,0,0,,%s' % (ass_time(max(0.0, s + a.offset)),
                                                             ass_time(max(0.0, e + a.offset)), r'\N'.join(lines)))
    with open(a.output, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(out) + '\n')
    print('wrote %s: %d lines, %dx%d, font "%s" %dpx%s' % (a.output, len(rows), W, H, a.font, size,
                                                         ', boxed' if a.box else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
