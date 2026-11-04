#!/usr/bin/env python3
"""
font_check.py - will this font show my Arabic translation correctly in this game?

For each font it reports:
  * missing characters for the ACTUAL translation text, both as logical text
    (engine shapes itself) and as pre-shaped text (ar_shape.py output)
  * whether the font can shape on its own (GSUB init/medi/fina/rlig, GPOS mark)
  * presentation-form coverage (needed when the engine cannot shape)
  * vertical metrics vs. the real height of Arabic glyphs (clipped tops/bottoms)
  * size match against the game's original Latin font (--ref)
  * format notes: variable font, CFF vs TrueType, embedding restrictions, licence

Usage
  font_check.py MyArabic.ttf --text translation.csv --column ar
  font_check.py A.ttf B.otf --text strings.json --json-key-re "^text$" --ref original_game_font.ttf
  font_check.py A.ttf --chars "؟،؛٠١٢"
Text sources: .txt (lines) .csv/.tsv (--column, else every cell) .json (string values) .po (msgstr)
Needs: fonttools (Pillow not needed)
"""
import argparse
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import Shaper, FORMS, LAM_ALEF, DEFAULT_TAG_PATTERNS  # noqa: E402
import re  # noqa: E402
TAG_RE = re.compile('|'.join('(?:%s)' % p for p in DEFAULT_TAG_PATTERNS))
from l10n_io import load_strings  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError, ImportError):
    pass


def group_of(cp):
    ch = chr(cp)
    if 0xFE70 <= cp <= 0xFEFF or 0xFB50 <= cp <= 0xFDFF:
        return 'presentation forms'
    if unicodedata.category(ch) == 'Mn':
        return 'harakat / marks'
    if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0x08A0 <= cp <= 0x08FF:
        if unicodedata.category(ch).startswith('L'):
            return 'Arabic letters'
        return 'Arabic punctuation / digits'
    if cp < 0x80:
        return 'ASCII'
    if unicodedata.category(ch).startswith('Z') or unicodedata.category(ch) == 'Cf':
        return 'spaces / format chars'
    return 'other'


def gsub_features(font):
    feats = {}
    for tag in ('GSUB', 'GPOS'):
        if tag not in font or not font[tag].table.ScriptList:
            continue
        t = font[tag].table
        fl = t.FeatureList.FeatureRecord
        for sr in t.ScriptList.ScriptRecord:
            if sr.ScriptTag not in ('arab', 'DFLT'):
                continue
            idx = set()
            langs = [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]
            for ls in langs:
                if ls is not None:
                    idx.update(ls.FeatureIndex)
            feats.setdefault(tag, set()).update(fl[i].FeatureTag for i in idx)
    return feats


def glyph_bounds(font, cps):
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    ymax = ymin = None
    hi = lo = None
    for cp in cps:
        g = cmap.get(cp)
        if not g:
            continue
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        if not bp.bounds:
            continue
        _, y0, _, y1 = bp.bounds
        if ymax is None or y1 > ymax:
            ymax, hi = y1, cp
        if ymin is None or y0 < ymin:
            ymin, lo = y0, cp
    return ymax, hi, ymin, lo


def height_of(font, ch):
    cmap = font.getBestCmap()
    g = cmap.get(ord(ch))
    if not g:
        return None
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[g].draw(bp)
    return bp.bounds[3] if bp.bounds else None


def check_font(path, texts, extra_chars, ref, max_examples):
    font = TTFont(path, fontNumber=0)
    cmap = font.getBestCmap()
    upem = font['head'].unitsPerEm
    name = font['name'].getDebugName(4) or os.path.basename(path)
    print('=' * 78)
    print('FONT  %s  (%s)' % (name, os.path.basename(path)))
    print('-' * 78)
    kind = 'CFF/PostScript (.otf)' if 'CFF ' in font or 'CFF2' in font else 'TrueType (glyf)'
    print('format: %s | glyphs: %d | unitsPerEm: %d%s' % (
        kind, len(font.getGlyphOrder()), upem, ' | VARIABLE font (instance a static weight for most engines)' if 'fvar' in font else ''))
    os2 = font['OS/2'] if 'OS/2' in font else None
    if os2 is not None and os2.fsType & 0x000E:
        print('WARNING: OS/2.fsType=%d restricts embedding - check the licence before shipping it in a patch' % os2.fsType)
    lic = font['name'].getDebugName(13)
    if lic:
        print('licence: %s' % (lic[:140] + ('...' if len(lic) > 140 else '')))

    feats = gsub_features(font)
    g = feats.get('GSUB', set())
    p = feats.get('GPOS', set())
    can_shape = {'init', 'medi', 'fina'} <= g
    print('OpenType Arabic shaping (GSUB): %s  %s' % ('YES' if can_shape else 'NO', ' '.join(sorted(g)) or '-'))
    print('mark positioning (GPOS mark/mkmk): %s' % ('YES' if 'mark' in p else 'NO'))
    letters_pf = [(b, f, pf) for b, fs in FORMS.items() if b in 'ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي' for f, pf in fs.items() if 0xFE70 <= ord(pf) <= 0xFEFF]
    la = [pf for fs in LAM_ALEF.values() for pf in fs.values()]
    have = sum(1 for _, _, pf in letters_pf if ord(pf) in cmap) + sum(1 for pf in la if ord(pf) in cmap)
    total = len(letters_pf) + len(la)
    print('presentation forms (core Arabic + lam-alef): %d / %d mapped%s' % (
        have, total, '' if have == total else '  -> run font_add_presforms.py before using pre-shaped text'))

    # vertical metrics vs real glyph extents
    arabic_cps = [c for c in cmap if 0x0600 <= c <= 0x06FF or 0xFB50 <= c <= 0xFDFF or 0xFE70 <= c <= 0xFEFF]
    ymax, hi, ymin, lo = glyph_bounds(font, arabic_cps)
    if ymax is not None:
        hhea = font['hhea']
        print('Arabic glyph extents: top %d (%s U+%04X)  bottom %d (%s U+%04X)' % (
            ymax, chr(hi), hi, ymin, chr(lo), lo))
        print('metrics: hhea %d/%d gap %d' % (hhea.ascent, hhea.descent, hhea.lineGap), end='')
        if os2 is not None:
            print(' | typo %d/%d gap %d | win %d/%d' % (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap,
                                                     os2.usWinAscent, os2.usWinDescent))
            if ymax > os2.usWinAscent or -ymin > os2.usWinDescent:
                print('WARNING: Arabic glyphs exceed usWinAscent/usWinDescent - engines that clip to the line box '
                      'will cut tops (hamza, shadda) or bottoms (ي ع م). Raise line height / padding.')
        else:
            print()

    if ref:
        rf = TTFont(ref, fontNumber=0)
        rcap = height_of(rf, 'H')
        alef = height_of(font, 'ا')
        if rcap and alef:
            ratio = (rcap / rf['head'].unitsPerEm) / (alef / upem)
            print('size vs reference: Latin "H" = %.3f em, Arabic alef = %.3f em -> to match visually use about '
                  '%.0f%% of the original size' % (rcap / rf['head'].unitsPerEm, alef / upem, ratio * 100))

    # coverage against the real text
    if texts or extra_chars:
        logical = {}
        pre = {}
        sh = Shaper(mode='forms')
        for t in texts:
            for ch in TAG_RE.sub('', t):            # tags / placeholders are never drawn
                logical.setdefault(ord(ch), t)
            for ch in TAG_RE.sub('', sh.process(t)):
                pre.setdefault(ord(ch), t)
        for ch in extra_chars:
            logical.setdefault(ord(ch), '(--chars)')
            pre.setdefault(ord(ch), '(--chars)')
        skip = {0x0a, 0x0d, 0x09, 0x200d, 0x200c, 0xfeff}
        for label, need in (('LOGICAL text (engine shapes)', logical), ('PRE-SHAPED text (ar_shape.py)', pre)):
            miss = {cp: ex for cp, ex in need.items() if cp not in cmap and cp not in skip}
            print('-- %s: %d distinct chars, %d missing' % (label, len(need), len(miss)))
            groups = {}
            for cp, ex in sorted(miss.items()):
                groups.setdefault(group_of(cp), []).append((cp, ex))
            for grp, items in groups.items():
                print('   [%s] %d' % (grp, len(items)))
                for cp, ex in items[:max_examples]:
                    try:
                        nm = unicodedata.name(chr(cp))
                    except ValueError:
                        nm = '?'
                    sample = ex if len(ex) <= 40 else ex[:40] + '...'
                    print('     U+%04X %s  %s   e.g. %s' % (cp, chr(cp) if chr(cp).isprintable() else ' ', nm, sample))
                if len(items) > max_examples:
                    print('     ... %d more' % (len(items) - max_examples))
    print()


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Check Arabic font readiness for a game translation.')
    ap.add_argument('fonts', nargs='+')
    ap.add_argument('--text', action='append', default=[], help='translation file(s)')
    ap.add_argument('--column', help='CSV/TSV column (name or index)')
    ap.add_argument('--json-key-re', help='JSON: only values whose key matches')
    ap.add_argument('--chars', default='', help='extra characters that must exist')
    ap.add_argument('--ref', help="the game's original font (size comparison)")
    ap.add_argument('--max-examples', type=int, default=12)
    a = ap.parse_args()
    texts = []
    for t in a.text:
        texts += load_strings(t, a.column, a.json_key_re)
    if a.text:
        print('loaded %d strings' % len(texts))
    for f in a.fonts:
        check_font(f, texts, a.chars, a.ref, a.max_examples)


if __name__ == '__main__':
    main()
