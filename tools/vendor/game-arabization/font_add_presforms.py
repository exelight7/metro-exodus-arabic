#!/usr/bin/env python3
"""
font_add_presforms.py - make ANY OpenType Arabic font work with pre-shaped text.

Problem: text produced by ar_shape.py uses Unicode Presentation Forms
(U+FE70-FEFF, U+FB50-FDFF). Many modern fonts (Cairo, Tajawal, many Google /
commercial fonts) only have contextual glyphs reachable through OpenType GSUB,
so in an engine without shaping those code points show as boxes (tofu).

Fix: shape every letter in every context with HarfBuzz (isolated, final,
initial, medial, and the lam-alef ligatures), take the glyph the font itself
would use, and add cmap entries FExx/FBxx -> that glyph. When the font draws a
form with several glyphs (e.g. a lam-alef made of two pieces, or letter + dots),
a new composite glyph is built from the HarfBuzz positions.

Usage
  font_add_presforms.py IN.ttf OUT.ttf [--force] [--rename "MyGame Arabic"]
  font_add_presforms.py IN.ttf --report          (show what is missing, write nothing)

Needs: pip install fonttools uharfbuzz   (brotli for .woff2)
Notes
  * TrueType (glyf) fonts get composite glyphs; CFF (.otf) fonts get merged
    outlines. Variable fonts: instance a static weight first
    (fonttools varLib.instancer IN.ttf wght=400 -o static.ttf).
  * Font licence: OFL allows modification, but if the font declares a Reserved
    Font Name you must rename it before distributing (use --rename).
"""
import argparse
import os
import sys

try:
    import uharfbuzz as hb
except ImportError:
    sys.exit('needs uharfbuzz:  pip install uharfbuzz fonttools')
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import FORMS, LAM_ALEF, LAM  # noqa: E402

ZWJ = '\u200d'
CONTEXTS = {'iso': ('', ''), 'fin': (ZWJ, ''), 'ini': ('', ZWJ), 'med': (ZWJ, ZWJ)}


def hb_shape(hbfont, text):
    buf = hb.Buffer()
    buf.add_codepoints([ord(c) for c in text])
    buf.direction = 'rtl'
    buf.script = 'Arab'
    buf.language = 'ar'
    hb.shape(hbfont, buf, {})
    return list(zip(buf.glyph_infos, buf.glyph_positions))


def glyphs_for(hbfont, text, wanted_clusters):
    """Glyphs (visual order) that HarfBuzz uses for the given source indices.
    Returns ([(gid, x, y), ...], advance) relative to the start of that cluster."""
    res = []
    pen_x = 0
    start = None
    for info, pos in hb_shape(hbfont, text):
        if info.cluster in wanted_clusters:
            if start is None:
                start = pen_x
            res.append((info.codepoint, pen_x + pos.x_offset - start, pos.y_offset, pos.x_advance))
        pen_x += pos.x_advance
    if not res:
        return None
    return [(g, x, y) for g, x, y, _ in res], sum(r[3] for r in res)


def build_composite(font, name, pieces, advance):
    order = font.getGlyphOrder()
    if 'glyf' in font:
        from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent
        glyf = font['glyf']
        g = Glyph()
        g.numberOfContours = -1
        g.components = []
        for gid, x, y in pieces:
            c = GlyphComponent()
            c.glyphName = order[gid]
            c.x, c.y = int(round(x)), int(round(y))
            c.flags = 0x0004 | 0x0002  # ROUND_XY_TO_GRID | ARGS_ARE_XY_VALUES
            g.components.append(c)
        glyf[name] = g
        g.recalcBounds(glyf)
        lsb = getattr(g, 'xMin', 0)
    elif 'CFF ' in font:
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        from fontTools.pens.boundsPen import BoundsPen
        gs = font.getGlyphSet()
        pen = T2CharStringPen(advance, gs)
        bp = BoundsPen(gs)
        for gid, x, y in pieces:
            gs[order[gid]].draw(TransformPen(pen, (1, 0, 0, 1, x, y)))
            gs[order[gid]].draw(TransformPen(bp, (1, 0, 0, 1, x, y)))
        cff = font['CFF '].cff
        top = cff.topDictIndex[0]
        cs = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
        top.CharStrings[name] = cs
        lsb = int(bp.bounds[0]) if bp.bounds else 0
    else:
        return False
    font['hmtx'][name] = (int(round(advance)), int(lsb))
    if 'vmtx' in font:
        font['vmtx'][name] = font['vmtx'][order[pieces[0][0]]]
    return True


def add_glyph_name(font, name):
    order = font.getGlyphOrder()
    if name in order:
        return
    order.append(name)
    font.setGlyphOrder(order)
    if 'CFF ' in font:
        cff = font['CFF '].cff
        top = cff.topDictIndex[0]
        if name not in top.charset:
            top.charset.append(name)
    if 'post' in font and font['post'].formatType == 2.0:
        font['post'].extraNames = getattr(font['post'], 'extraNames', [])


def rename_family(font, family):
    name = font['name']
    sub = name.getDebugName(2) or 'Regular'
    ps = family.replace(' ', '') + '-' + sub.replace(' ', '')
    for rec in name.names:
        if rec.nameID in (1, 16):
            rec.string = family
        elif rec.nameID == 4:
            rec.string = family + ('' if sub == 'Regular' else ' ' + sub)
        elif rec.nameID == 6:
            rec.string = ps
        elif rec.nameID == 3:
            rec.string = ps + ';presforms'
    if 'CFF ' in font:
        font['CFF '].cff.fontNames = [ps]


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Add Arabic presentation-form cmap entries to a font.')
    ap.add_argument('input')
    ap.add_argument('output', nargs='?')
    ap.add_argument('--force', action='store_true', help='replace existing presentation-form mappings')
    ap.add_argument('--report', action='store_true', help='only report, write nothing')
    ap.add_argument('--rename', help='new family name (needed for OFL fonts with a Reserved Font Name)')
    a = ap.parse_args()
    if not a.report and not a.output:
        ap.error('give OUTPUT path or --report')

    font = TTFont(a.input)
    if 'fvar' in font:
        print('WARNING: variable font. Instance a static weight first for predictable results.')
    hbfont = hb.Font(hb.Face(hb.Blob.from_file_path(a.input)))
    cmap = font.getBestCmap()
    order = font.getGlyphOrder()

    jobs = []   # (codepoint, text, clusters)
    for base, forms in FORMS.items():
        if ord(base) not in cmap:
            continue
        for form, pf in forms.items():
            pre, post = CONTEXTS[form]
            text = pre + base + post
            jobs.append((ord(pf), text, {len(pre)}, base, form))
    if ord(LAM) in cmap:
        for alef, forms in LAM_ALEF.items():
            if ord(alef) not in cmap:
                continue
            for form, pf in forms.items():
                pre = ZWJ if form == 'fin' else ''
                text = pre + LAM + alef
                jobs.append((ord(pf), text, {len(pre), len(pre) + 1}, LAM + alef, form))

    added = present = composites = failed = 0
    missing_report = []
    new_map = {}
    for cp, text, clusters, base, form in sorted(jobs):
        if cp in cmap and not a.force:
            present += 1
            continue
        r = glyphs_for(hbfont, text, clusters)
        if not r:
            failed += 1
            continue
        pieces, adv = r
        missing_report.append('U+%04X %s %s' % (cp, base, form))
        if a.report:
            continue
        if len(pieces) == 1 and pieces[0][1] == 0 and pieces[0][2] == 0:
            new_map[cp] = order[pieces[0][0]]
        else:
            gname = 'uni%04X.pf' % cp
            add_glyph_name(font, gname)
            order = font.getGlyphOrder()
            if build_composite(font, gname, pieces, adv):
                new_map[cp] = gname
                composites += 1
            else:
                failed += 1
                continue
        added += 1

    print('font: %s' % os.path.basename(a.input))
    print('presentation forms already mapped: %d' % present)
    print('%s: %d (composites built: %d), failed: %d' %
          ('would add' if a.report else 'added', len(missing_report) if a.report else added,
           composites, failed))
    if a.report:
        for line in missing_report:
            print('  missing ' + line)
        return 0
    for t in font['cmap'].tables:
        if t.isUnicode():
            t.cmap.update(new_map)
    if a.rename:
        rename_family(font, a.rename)
    if a.output.lower().endswith('.woff2'):
        font.flavor = 'woff2'
    elif a.output.lower().endswith('.woff'):
        font.flavor = 'woff'
    else:
        font.flavor = None
    font.save(a.output)
    print('saved: %s' % a.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
