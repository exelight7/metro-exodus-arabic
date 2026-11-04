#!/usr/bin/env python3
"""
font_merge.py - add Arabic to the game's own Latin font (or any base font), in one file.

Why: engines pick ONE font per text component (Unity TMP atlas source, Unreal FontFace /
.ufont, RPG Maker gamefont, Godot FontFile...). A fallback font for Arabic causes jumps,
different baselines and broken joins between fonts. Merging keeps the original Latin look
and adds Arabic with its OpenType shaping tables (GSUB/GPOS) intact.

What it does
  1. subsets the Arabic font to Arabic code points (+ presentation forms, marks, ، ؛ ؟, tatweel)
     keeping all layout features
  2. rescales it to the base font's unitsPerEm, times --arabic-scale (visual size match;
     --auto-scale matches Arabic alef height to the base font's "H" height)
  3. merges with fontTools.merge (base glyphs win for shared code points)
  4. optionally grows vertical metrics so tall Arabic marks are not clipped (--fit-metrics)
  5. optional --rename for the new family (needed for OFL fonts with a Reserved Font Name)

Usage
  font_merge.py game_latin.ttf NotoSansArabic.ttf -o merged.ttf --auto-scale --fit-metrics
  font_merge.py base.ttf arabic.ttf -o merged.ttf --arabic-scale 1.1 --rename "Game Arabic"
Then: font_check.py merged.ttf --text translation.csv (and font_add_presforms.py if the engine
cannot shape). Both inputs must be TrueType-outline fonts (glyf); convert CFF .otf first.
Variable fonts: instance them first (fonttools varLib.instancer in.ttf wght=400 -o static.ttf).
"""
import argparse
import os
import sys
import tempfile

from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.merge import Merger, Options as MergeOptions
from fontTools.pens.boundsPen import BoundsPen

ARABIC_RANGES = [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
                 (0x200C, 0x200F), (0x061C, 0x061C)]


def glyph_top(font, ch):
    cmap = font.getBestCmap()
    g = cmap.get(ord(ch))
    if not g:
        return None
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[g].draw(bp)
    return bp.bounds[3] if bp.bounds else None


def check_input(font, name):
    if 'glyf' not in font:
        sys.exit('%s is not a TrueType-outline font (CFF). Convert to TTF first.' % name)
    if 'fvar' in font:
        sys.exit('%s is a variable font. Instance it first: fonttools varLib.instancer IN wght=400 -o static.ttf' % name)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Merge an Arabic font into a base (Latin) font.')
    ap.add_argument('base')
    ap.add_argument('arabic')
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--arabic-scale', type=float, default=1.0, help='extra size factor for Arabic glyphs')
    ap.add_argument('--auto-scale', action='store_true', help='match Arabic alef height to base "H" height')
    ap.add_argument('--fit-metrics', action='store_true', help='grow ascent/descent to fit Arabic glyphs')
    ap.add_argument('--rename', help='new family name')
    a = ap.parse_args()

    base = TTFont(a.base)
    ar = TTFont(a.arabic)
    check_input(base, a.base)
    check_input(ar, a.arabic)
    upem_b, upem_a = base['head'].unitsPerEm, ar['head'].unitsPerEm
    scale = a.arabic_scale
    if a.auto_scale:
        h = glyph_top(base, 'H')
        alef = glyph_top(ar, 'ا')
        if h and alef:
            scale *= (h / upem_b) / (alef / upem_a)
            print('auto scale: H %.3f em, alef %.3f em -> Arabic x%.3f' % (h / upem_b, alef / upem_a, scale))
        else:
            print('auto scale skipped (H or alef missing)')
    tmp = tempfile.mkdtemp(prefix='fmerge_')
    # 1) subset Arabic font to Arabic code points, keep every layout feature
    cmap = ar.getBestCmap()
    keep = [cp for cp in cmap if any(lo <= cp <= hi for lo, hi in ARABIC_RANGES)]
    opts = subset.Options()
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    opts.glyph_names = True
    opts.layout_scripts = ['*']
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=keep)
    sub.subset(ar)
    # 2) scale to base upem (x extra scale)
    target = int(round(upem_b * scale))
    if upem_a != target:
        from fontTools.ttLib.scaleUpem import scale_upem
        scale_upem(ar, target)
    ar['head'].unitsPerEm = upem_b
    # glyph name clashes are handled by the merger, but give Arabic glyphs a prefix for clarity
    p_ar = os.path.join(tmp, 'ar.ttf')
    p_b = os.path.join(tmp, 'base.ttf')
    ar.save(p_ar)
    base.save(p_b)
    # 3) merge (first font wins on duplicate code points)
    mo = MergeOptions()
    mo.drop_tables = ['vmtx', 'vhea', 'MATH', 'STAT']
    merged = Merger(options=mo).merge([p_b, p_ar])
    # 4) metrics
    hhea = merged['hhea']
    os2 = merged['OS/2']
    gs = merged.getGlyphSet()
    m_cmap = merged.getBestCmap()
    ymax, ymin = 0, 0
    for cp in keep:
        g = m_cmap.get(cp)
        if not g:
            continue
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        if bp.bounds:
            ymin, ymax = min(ymin, bp.bounds[1]), max(ymax, bp.bounds[3])
    clipped = ymax > os2.usWinAscent or -ymin > os2.usWinDescent
    if a.fit_metrics:
        os2.usWinAscent = max(os2.usWinAscent, int(ymax))
        os2.usWinDescent = max(os2.usWinDescent, int(-ymin))
        hhea.ascent = max(hhea.ascent, int(ymax))
        hhea.descent = min(hhea.descent, int(ymin))
        os2.sTypoAscender = max(os2.sTypoAscender, int(ymax))
        os2.sTypoDescender = min(os2.sTypoDescender, int(ymin))
    elif clipped:
        print('WARNING: Arabic glyphs (%d..%d) exceed win metrics (%d/-%d) - use --fit-metrics or a smaller '
              '--arabic-scale' % (ymin, ymax, os2.usWinAscent, os2.usWinDescent))
    if a.rename:
        fam = a.rename
        ps = fam.replace(' ', '') + '-Regular'
        for rec in merged['name'].names:
            if rec.nameID in (1, 16):
                rec.string = fam
            elif rec.nameID == 4:
                rec.string = fam
            elif rec.nameID == 6:
                rec.string = ps
    merged.save(a.output)
    out = TTFont(a.output)
    c = out.getBestCmap()
    n_ar = sum(1 for cp in c if 0x0600 <= cp <= 0x06FF)
    n_pf = sum(1 for cp in c if 0xFE70 <= cp <= 0xFEFF)
    n_lat = sum(1 for cp in c if 0x20 <= cp < 0x7F)
    scripts = sorted({sr.ScriptTag for sr in out['GSUB'].table.ScriptList.ScriptRecord}) if 'GSUB' in out else []
    print('merged: %s | ASCII %d/95, Arabic %d, presentation forms %d, glyphs %d, GSUB scripts %s'
          % (a.output, n_lat, n_ar, n_pf, len(out.getGlyphOrder()), scripts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
