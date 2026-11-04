#!/usr/bin/env python3
"""
simulate_render.py - SEE what the game will show, without the game.

For an AI agent (or anyone without the game in front of them): renders the strings you
are about to inject the way a given kind of engine draws them, next to how correct Arabic
must look, and reports missing glyphs (boxes) and overflow. Open the PNG and compare.

Engine behaviours (--engine):
  none      draws glyphs left-to-right, no shaping, no RTL        (bitmap fonts, TMP, GameMaker, id Tech 4, UE3...)
  rtl-only  reverses each line but does not shape                (TMP with RTL enabled, some UIs)
  full      shapes + bidi like a browser / HarfBuzz              (Unreal Slate, Godot 4, Unity UI Toolkit ATG, RPG Maker menus)
Engine wrapping (--engine-wrap PX): the engine itself wraps at spaces, left to right, after
you injected - reproduces the "line order reversed" bug of wrapping pre-reversed text.

Usage
  simulate_render.py --font game.ttf --size 28 --engine none --text "لا سلام" --inject "<ar_shape output>"
  simulate_render.py --font f.ttf --size 28 --engine none --csv pack.csv --logical-col logical --inject-col visual -o sim.png
  simulate_render.py --font f.ttf --size 28 --engine none --csv tr.csv --logical-col ar --auto visual --max-px 600
     (--auto MODE: build the injected text with ar_shape.py MODE instead of reading a column)
Exit code 1 if any string has missing glyphs or overflows --max-px.
Needs: Pillow with raqm (for the reference column; falls back to no reference otherwise), fonttools.
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import Shaper, DEFAULT_TAG_PATTERNS  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, features  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
import re  # noqa: E402

TAG_RE = re.compile('|'.join('(?:%s)' % p for p in DEFAULT_TAG_PATTERNS))
NL_RE = re.compile(r'\r?\n|\\n')


def engine_lines(text, engine, wrap_px, font):
    lines = NL_RE.split(TAG_RE.sub('', text))
    if wrap_px:
        out = []
        for ln in lines:
            cur = ''
            for w in ln.split(' '):
                cand = (cur + ' ' + w) if cur else w
                if cur and font.getlength(cand) > wrap_px:
                    out.append(cur)
                    cur = w
                else:
                    cur = cand
            out.append(cur)
        lines = out
    if engine == 'rtl-only':
        lines = [ln[::-1] for ln in lines]
    return lines


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Simulate how an engine will draw injected Arabic.')
    ap.add_argument('--font', required=True)
    ap.add_argument('--size', type=int, default=28)
    ap.add_argument('--engine', choices=['none', 'rtl-only', 'full'], default='none')
    ap.add_argument('--engine-wrap', type=int, help='engine wraps at this width (px)')
    ap.add_argument('--max-px', type=int, help='flag lines wider than this')
    ap.add_argument('--text', action='append', default=[], help='logical text (repeatable)')
    ap.add_argument('--inject', action='append', default=[], help='injected text, same order as --text')
    ap.add_argument('--csv')
    ap.add_argument('--logical-col', default='logical')
    ap.add_argument('--inject-col')
    ap.add_argument('--auto', choices=['visual', 'forms', 'reorder', 'logical'],
                    help='make the injected text with ar_shape.py in this mode')
    ap.add_argument('--limit', type=int, default=40)
    ap.add_argument('-o', '--output', default='simulate.png')
    a = ap.parse_args()

    pairs = []
    if a.csv:
        with open(a.csv, encoding='utf-8-sig') as f:
            data = f.read()
        for r in csv.DictReader(io.StringIO(data), delimiter='\t' if a.csv.endswith('.tsv') else ','):
            pairs.append((r.get('id', ''), r[a.logical_col], r[a.inject_col] if a.inject_col else None))
    else:
        for i, t in enumerate(a.text):
            pairs.append((str(i + 1), t, a.inject[i] if i < len(a.inject) else None))
    if a.auto:
        sh = None if a.auto == 'logical' else Shaper(mode=a.auto)
        pairs = [(i, lg, lg if sh is None else sh.process(lg)) for i, lg, _ in pairs]
    if any(inj is None for _, _, inj in pairs):
        ap.error('give --inject / --inject-col or --auto')
    pairs = pairs[:a.limit]

    cmap = TTFont(a.font, fontNumber=0).getBestCmap()
    fb = ImageFont.truetype(a.font, a.size, layout_engine=ImageFont.Layout.BASIC)
    has_raqm = features.check('raqm')
    fr = ImageFont.truetype(a.font, a.size, layout_engine=ImageFont.Layout.RAQM) if has_raqm else None
    lab = ImageFont.load_default()
    lh = int(a.size * 1.9)
    colw = max(a.max_px or 0, a.engine_wrap or 0, 640) + 20
    if has_raqm:   # widen to the longest reference line (capped) so nothing is clipped
        longest = max((fr.getlength(l, direction='rtl') for _, lg, _ in pairs
                       for l in NL_RE.split(TAG_RE.sub('', lg))), default=0)
        colw = int(min(max(colw, longest + 30), 1600))
    blocks, problems = [], 0
    for sid, logical, inj in pairs:
        ref_lines = NL_RE.split(TAG_RE.sub('', logical))
        eng_lines = engine_lines(inj, a.engine, a.engine_wrap, fb)
        missing = sorted({c for c in TAG_RE.sub('', inj) if ord(c) not in cmap and c not in '\r\n\t'})
        if a.engine == 'full' and has_raqm:
            widths = [fr.getlength(l, direction='rtl') for l in eng_lines]
        else:
            widths = [fb.getlength(l) for l in eng_lines]
        over = [w for w in widths if a.max_px and w > a.max_px]
        flag = []
        if missing:
            flag.append('MISSING %s' % ' '.join('U+%04X' % ord(c) for c in missing[:8]))
        if over:
            flag.append('OVERFLOW %dpx > %dpx' % (max(over), a.max_px))
        problems += bool(flag)
        print('%-6s %s' % (sid, '; '.join(flag) if flag else 'ok'))
        blocks.append((sid, ref_lines, eng_lines, flag))

    rows_h = sum(max(len(r), len(e)) * lh + 22 for _, r, e, _ in blocks) + 30
    im = Image.new('RGB', (colw * 2 + 30, rows_h), 'white')
    d = ImageDraw.Draw(im)
    d.text((10, 6), 'CORRECT (HarfBuzz, RTL)' if has_raqm else 'reference unavailable (no raqm)', fill='black', font=lab)
    d.text((colw + 30, 6), 'ENGINE "%s"%s draws your injected text' % (
        a.engine, ' + wraps at %dpx' % a.engine_wrap if a.engine_wrap else ''), fill='black', font=lab)
    y = 28
    for sid, ref, eng, flag in blocks:
        d.text((10, y), sid, fill='gray', font=lab)
        if flag:
            d.text((colw + 30, y), ' | '.join(flag), fill='red', font=lab)
        y += 14
        n = max(len(ref), len(eng))
        if has_raqm:
            for i, l in enumerate(ref):
                w = fr.getlength(l, direction='rtl')
                d.text((colw - 10 - w, y + i * lh), l, font=fr, fill='black', direction='rtl')
        for i, l in enumerate(eng):
            if a.engine == 'full' and has_raqm:
                w = fr.getlength(l, direction='rtl')
                d.text((colw * 2 + 20 - w, y + i * lh), l, font=fr, fill='navy', direction='rtl')
            else:
                d.text((colw + 30, y + i * lh), l, font=fb, fill='navy')
        if a.max_px:
            d.line([(colw + 30 + a.max_px, y), (colw + 30 + a.max_px, y + n * lh)], fill='red')
        y += n * lh + 8
        d.line([(0, y), (im.width, y)], fill=(225, 225, 225))
    im.save(a.output)
    print('image: %s  (%d strings, %d with problems)' % (a.output, len(blocks), problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
