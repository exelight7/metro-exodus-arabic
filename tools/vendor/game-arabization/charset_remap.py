#!/usr/bin/env python3
"""
charset_remap.py - Arabic for engines that only have a FEW character slots.

Old engines (id Tech 4 fonts = 256 slots, Unreal 3 bitmap fonts, Latin-1/ANSI-only text,
KH2-style fixed tables, bitmap-font generators that accept only a range) cannot address
U+FE70..U+FEFF. Solution used by fan "codepage" patches: put each pre-shaped Arabic glyph
into a free slot (e.g. 0xA0-0xFF), build a font where those slots draw Arabic, and encode
the shaped text with the same table.

  build   choose the glyphs your text actually needs, assign slots, write the remapped
          font (+ map.json). Feed that font to the engine's font tool (Q3Font /
          ExportFontToDoom3 for id Tech 4, BMFont, UE3 font import ...).
  encode  convert shaped text to slot characters with map.json (CSV column / text lines).
          Then write it with the game's 8-bit encoding: text.encode('latin-1') maps
          U+0080..U+00FF to bytes 0x80..0xFF one-to-one.

Usage
  charset_remap.py build --font Arabic-PF.ttf --text tr.csv --column ar --slots 0xA0-0xFF,0x80-0x9F \\
                         --out-font Arabic-Remap.ttf --out-map map.json [--harakat strip]
  charset_remap.py encode --map map.json --csv tr.csv --column ar -o tr_remapped.csv
  charset_remap.py encode --map map.json "نص عربي"
The font must contain presentation forms (run font_add_presforms.py first if needed).
Text is shaped with ar_shape.py (visual mode by default; --mode forms for RTL-capable engines).
"""
import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import Shaper, DEFAULT_TAG_PATTERNS  # noqa: E402
from l10n_io import load_strings  # noqa: E402
import re  # noqa: E402

TAG_RE = re.compile('|'.join('(?:%s)' % p for p in DEFAULT_TAG_PATTERNS))


def parse_slots(spec):
    slots = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        lo, hi = int(a, 0), int(b or a, 0)
        slots.extend(range(lo, hi + 1))
    return slots


def make_shaper(a):
    return Shaper(mode=a.mode, harakat=a.harakat)


def cmd_build(a):
    from fontTools.ttLib import TTFont
    texts = []
    for t in a.text:
        texts += load_strings(t, a.column, a.json_key_re)
    sh = make_shaper(a)
    need = []
    seen = set()
    for t in texts:
        for ch in TAG_RE.sub('', sh.process(t)):
            if ord(ch) >= 0x80 and ch not in seen and ch not in '\r\n':
                seen.add(ch)
                need.append(ch)
    need.sort()
    slots = [s for s in parse_slots(a.slots)]
    font = TTFont(a.font, fontNumber=0)
    cmap = font.getBestCmap()
    clash = [s for s in slots if s in cmap and not a.overwrite]
    if clash and not a.overwrite:
        print('note: %d slots already have glyphs in the font (e.g. U+%04X); they will be REPLACED. '
              'Make sure the game never needs those characters.' % (len(clash), clash[0]))
    missing = [c for c in need if ord(c) not in cmap]
    if missing:
        sys.exit('font lacks %d needed glyphs (e.g. U+%04X) - run font_add_presforms.py first'
                 % (len(missing), ord(missing[0])))
    if len(need) > len(slots):
        sys.exit('need %d slots, have %d. Options: --harakat strip, drop Persian letters, more --slots'
                 % (len(need), len(slots)))
    mapping = {c: slots[i] for i, c in enumerate(need)}
    for t in font['cmap'].tables:
        if t.isUnicode():
            for c, s in mapping.items():
                t.cmap[s] = cmap[ord(c)]
    font.flavor = None
    font.save(a.out_font)
    with open(a.out_map, 'w', encoding='utf-8') as f:
        json.dump({'mode': a.mode, 'harakat': a.harakat,
                   'map': {'U+%04X' % ord(c): '0x%02X' % s for c, s in mapping.items()}}, f, indent=1)
    print('strings %d -> %d distinct non-ASCII glyphs -> slots %s..%s (%d free left)'
          % (len(texts), len(need), hex(slots[0]), hex(slots[len(need) - 1]) if need else '-', len(slots) - len(need)))
    print('font: %s  map: %s' % (a.out_font, a.out_map))
    return 0


def load_map(path):
    with open(path, encoding='utf-8') as f:
        m = json.load(f)
    table = {chr(int(k[2:], 16)): chr(int(v, 16)) for k, v in m['map'].items()}
    return m, table


def cmd_encode(a):
    m, table = load_map(a.map)
    a.mode, a.harakat = m.get('mode', 'visual'), m.get('harakat', 'keep')
    sh = make_shaper(a)
    unmapped = set()

    def conv(s):
        out = []
        for ch in sh.process(s):
            if ch in table:
                out.append(table[ch])
            else:
                if ord(ch) >= 0x80:
                    unmapped.add(ch)
                out.append(ch)
        return ''.join(out)
    if a.csv:
        with open(a.csv, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(io.StringIO(f.read())))
        col = rows[0].index(a.column)
        for r in rows[1:]:
            if col < len(r) and r[col]:
                r[col] = conv(r[col])
        buf = io.StringIO()
        csv.writer(buf, lineterminator='\n').writerows(rows)
        res = buf.getvalue()
    else:
        res = '\n'.join(conv(t) for t in a.strings) + '\n'
    if a.output:
        with open(a.output, 'w', encoding='utf-8', newline='') as f:
            f.write(res)
        print('wrote %s' % a.output)
    else:
        sys.stdout.write(res)
    if unmapped:
        print('WARNING: %d characters not in map (rebuild with all texts): %s'
              % (len(unmapped), ' '.join('U+%04X' % ord(c) for c in sorted(unmapped)[:10])), file=sys.stderr)
        return 1
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Remap pre-shaped Arabic into a limited character range.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--font', required=True)
    b.add_argument('--text', action='append', required=True)
    b.add_argument('--column')
    b.add_argument('--json-key-re')
    b.add_argument('--slots', default='0xA0-0xFF,0x80-0x9F')
    b.add_argument('--mode', choices=['visual', 'forms'], default='visual')
    b.add_argument('--harakat', choices=['keep', 'strip', 'shadda'], default='keep')
    b.add_argument('--overwrite', action='store_true', help='silence the slot-replacement note')
    b.add_argument('--out-font', required=True)
    b.add_argument('--out-map', required=True)
    e = sub.add_parser('encode')
    e.add_argument('--map', required=True)
    e.add_argument('strings', nargs='*')
    e.add_argument('--csv')
    e.add_argument('--column')
    e.add_argument('-o', '--output')
    a = ap.parse_args()
    return cmd_build(a) if a.cmd == 'build' else cmd_encode(a)


if __name__ == '__main__':
    sys.exit(main())
