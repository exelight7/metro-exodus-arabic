#!/usr/bin/env python3
"""
tmp_sdf_atlas.py - build a TextMeshPro SDF font atlas for Arabic WITHOUT the Unity editor,
preview it the way TMP draws it, and write it into a game's TMP_FontAsset.

  build    font + the characters your translation needs (pre-shaped presentation forms + Latin)
           -> atlas.png (8-bit SDF, Alpha8 data) + tmp_font.json (FaceInfo, glyph table,
              character table, atlas info) in TMP's modern schema (TMP 1.4+/Unity 2018.4+)
  preview  draw a test string from atlas.png + tmp_font.json exactly with those metrics and SDF
           threshold (catches wrong metrics, clipping, overlaps before touching the game)
  apply    write the atlas + tables into an existing TMP_FontAsset inside a Unity file (UnityPy):
           glyph/character tables, FaceInfo, atlas size/padding, static population mode,
           clears kerning pairs; replaces the atlas Texture2D (Alpha8); sets the material's
           _GradientScale / _TextureWidth / _TextureHeight. Dry run unless --write.

Usage
  tmp_sdf_atlas.py build --font merged.ttf --text translation.csv --column ar --mode visual \\
                         --size 64 --padding 7 --out arabic_sdf
  tmp_sdf_atlas.py preview --atlas arabic_sdf --text "مرحبا بك في المدينة" --mode visual
  tmp_sdf_atlas.py apply --unity-file X_Data/resources.assets --font-asset "LiberationSans SDF" \\
                         --atlas arabic_sdf -o patched [--keep-line-height] [--write]
Defaults that matter: --mode visual = text will be injected pre-shaped and pre-reversed (TMP RTL off);
use --mode forms if you enable isRightToLeftText on the components. Always include ASCII (default).
The SDF spread is padding + 1 texels, matching TMP's material _GradientScale = padding + 1.
NOTE: build/preview are tested; apply follows TMP's serialized field names but must be verified
on your game (roundtrip first, then one screen). Legacy TMP (< 1.4, m_glyphInfoList) is reported,
not written.
Needs: fonttools, freetype-py, numpy, opencv-python-headless, Pillow (+ UnityPy for apply)
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ar_shape import Shaper, DEFAULT_TAG_PATTERNS  # noqa: E402
from l10n_io import load_strings  # noqa: E402
import re  # noqa: E402

TAG_RE = re.compile('|'.join('(?:%s)' % p for p in DEFAULT_TAG_PATTERNS))


# ------------------------------------------------------------------------------------------ build
def needed_chars(a):
    chars = set(chr(c) for c in range(32, 127)) if not a.no_ascii else set()
    chars |= set(a.chars or '')
    sh = None if a.mode == 'logical' else Shaper(mode=a.mode, harakat=a.harakat)
    for t in a.text or []:
        looks_like_path = bool(re.search(r'\.(csv|tsv|json|po|pot|txt)$', t, re.I)) or os.sep in t or '/' in t
        if looks_like_path and not os.path.isfile(t):
            sys.exit('--text %r looks like a file but does not exist (wrong folder?)' % t)
        strings = load_strings(t, a.column, a.json_key_re) if os.path.isfile(t) else [t]
        for s in strings:
            s = TAG_RE.sub('', s if sh is None else sh.process(s))
            chars |= set(s)
    chars -= set('\r\n\t')
    return sorted(chars)


def render_sdf(ftfont, gs, gname, size_px, upem, pad, up):
    """Return (sdf uint8 array, metrics) for one glyph at size_px with `pad` texels of spread."""
    from fontTools.pens.freetypePen import FreeTypePen
    from fontTools.pens.boundsPen import BoundsPen
    import cv2
    s = size_px / upem
    bp = BoundsPen(gs)
    gs[gname].draw(bp)
    adv = ftfont['hmtx'][gname][0] * s
    if not bp.bounds:
        return None, {'w': 0, 'h': 0, 'bx': 0.0, 'by': 0.0, 'adv': adv}
    x0, y0, x1, y1 = bp.bounds
    w = max(1, int(math.ceil((x1 - x0) * s)))
    h = max(1, int(math.ceil((y1 - y0) * s)))
    W, H = (w + 2 * pad) * up, (h + 2 * pad) * up
    pen = FreeTypePen(gs)
    gs[gname].draw(pen)
    su = s * up
    # map glyph bbox origin to (pad, pad) texels, y up -> FreeTypePen array is top-down
    arr = pen.array(width=W, height=H, transform=(su, 0, 0, su, -x0 * su + pad * up, -y0 * su + pad * up),
                    contain=False)
    mask = (np.asarray(arr) >= 0.5).astype(np.uint8)
    inside = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    outside = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)
    dist = (inside - outside) / up                       # texels at target size, + inside
    dist = cv2.resize(dist, (w + 2 * pad, h + 2 * pad), interpolation=cv2.INTER_AREA)
    spread = pad + 1
    sdf = np.clip(0.5 + dist / (2.0 * spread), 0, 1)
    return (sdf * 255 + 0.5).astype(np.uint8), {'w': w, 'h': h, 'bx': x0 * s, 'by': y1 * s, 'adv': adv}


def cmd_build(a):
    from fontTools.ttLib import TTFont
    font = TTFont(a.font, fontNumber=0)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    order = font.getGlyphOrder()
    upem = font['head'].unitsPerEm
    chars = needed_chars(a)
    missing = [c for c in chars if ord(c) not in cmap and c != ' ']
    if missing:
        print('WARNING: font lacks %d chars, e.g. %s (run font_add_presforms.py / font_merge.py)'
              % (len(missing), ' '.join('U+%04X' % ord(c) for c in missing[:8])))
    glyphs = {}
    for c in chars:
        g = cmap.get(ord(c))
        if g and g not in glyphs:
            glyphs[g] = render_sdf(font, gs, g, a.size, upem, a.padding, a.upsample)
    # shelf packing, tallest first
    items = sorted(((g, v) for g, v in glyphs.items() if v[0] is not None), key=lambda x: -x[1][0].shape[0])
    size = a.atlas
    while True:
        x = y = row_h = 0
        placed = {}
        ok = True
        for g, (sdf, m) in items:
            ch, cw = sdf.shape
            if x + cw > size:
                x, y, row_h = 0, y + row_h, 0
            if y + ch > size:
                ok = False
                break
            placed[g] = (x, y)
            x += cw
            row_h = max(row_h, ch)
        if ok:
            break
        size *= 2
        if size > 8192:
            sys.exit('glyphs do not fit in 8192x8192 - lower --size or the character set')
    atlas = np.zeros((size, size), np.uint8)
    pad = a.padding
    glyph_table, char_table, used = [], [], []
    for g, (sdf, m) in glyphs.items():
        gid = order.index(g)
        rect = {'m_X': 0, 'm_Y': 0, 'm_Width': 0, 'm_Height': 0}
        if sdf is not None:
            px, py = placed[g]
            atlas[py:py + sdf.shape[0], px:px + sdf.shape[1]] = sdf
            # TMP GlyphRect excludes the padding; Y origin is the BOTTOM of the texture
            rect = {'m_X': px + pad, 'm_Y': size - (py + pad + m['h']), 'm_Width': m['w'], 'm_Height': m['h']}
            used.append({'m_X': px, 'm_Y': size - (py + sdf.shape[0]), 'm_Width': sdf.shape[1], 'm_Height': sdf.shape[0]})
        glyph_table.append({'m_Index': gid,
                            'm_Metrics': {'m_Width': float(m['w']), 'm_Height': float(m['h']),
                                          'm_HorizontalBearingX': round(m['bx'], 3),
                                          'm_HorizontalBearingY': round(m['by'], 3),
                                          'm_HorizontalAdvance': round(m['adv'], 3)},
                            'm_GlyphRect': rect, 'm_Scale': 1.0, 'm_AtlasIndex': 0, 'm_ClassDefinitionType': 0})
    for c in chars:
        g = cmap.get(ord(c))
        if g:
            char_table.append({'m_ElementType': 1, 'm_Unicode': ord(c), 'm_GlyphIndex': order.index(g), 'm_Scale': 1.0})
    s = a.size / upem
    hhea, os2, post = font['hhea'], font['OS/2'], font['post']
    asc, desc = hhea.ascent * s, hhea.descent * s
    space_adv = font['hmtx'][cmap[32]][0] * s if 32 in cmap else a.size / 4
    face = {'m_FamilyName': font['name'].getDebugName(1) or '', 'm_StyleName': font['name'].getDebugName(2) or '',
            'm_PointSize': a.size, 'm_Scale': 1.0, 'm_UnitsPerEM': upem,
            'm_LineHeight': round(asc - desc + hhea.lineGap * s, 3), 'm_AscentLine': round(asc, 3),
            'm_CapLine': round(getattr(os2, 'sCapHeight', 0) * s or asc * 0.7, 3),
            'm_MeanLine': round(getattr(os2, 'sxHeight', 0) * s or asc * 0.5, 3), 'm_Baseline': 0.0,
            'm_DescentLine': round(desc, 3), 'm_SuperscriptOffset': round(asc, 3), 'm_SuperscriptSize': 0.5,
            'm_SubscriptOffset': round(desc, 3), 'm_SubscriptSize': 0.5,
            'm_UnderlineOffset': round(post.underlinePosition * s, 3),
            'm_UnderlineThickness': round(max(1, post.underlineThickness * s), 3),
            'm_StrikethroughOffset': round((getattr(os2, 'sxHeight', 0) * s or asc * 0.5) / 2.5, 3),
            'm_StrikethroughThickness': round(max(1, post.underlineThickness * s), 3), 'm_TabWidth': round(space_adv, 3)}
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray(atlas, 'L').save(os.path.join(a.out, 'atlas.png'))
    meta = {'schema': 'tmp-modern', 'mode': a.mode, 'faceInfo': face, 'glyphTable': glyph_table,
            'characterTable': char_table, 'usedGlyphRects': used,
            'atlas': {'width': size, 'height': size, 'padding': pad, 'gradientScale': pad + 1},
            'source_font': os.path.basename(a.font)}
    with open(os.path.join(a.out, 'tmp_font.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    fill = sum(r['m_Width'] * r['m_Height'] for r in used) / float(size * size)
    print('characters %d, glyphs %d, atlas %dx%d (%.0f%% used), point size %d, padding %d -> %s/'
          % (len(char_table), len(glyph_table), size, size, fill * 100, a.size, pad, a.out))
    return 0


# ---------------------------------------------------------------------------------------- preview
def cmd_preview(a):
    meta = json.load(open(os.path.join(a.atlas, 'tmp_font.json'), encoding='utf-8'))
    atlas = np.asarray(Image.open(os.path.join(a.atlas, 'atlas.png')).convert('L'), dtype=np.float32) / 255.0
    H = meta['atlas']['height']
    glyphs = {g['m_Index']: g for g in meta['glyphTable']}
    cmap = {c['m_Unicode']: c['m_GlyphIndex'] for c in meta['characterTable']}
    face = meta['faceInfo']
    scale = a.font_size / face['m_PointSize']
    mode = a.mode or meta.get('mode', 'visual')
    lines = []
    for t in a.text:
        txt = t if mode == 'logical' else Shaper(mode=mode).process(t)
        lines += re.split(r'\r?\n', TAG_RE.sub('', txt))
    line_h = face['m_LineHeight'] * scale
    width = int(max(sum(glyphs[cmap[ord(c)]]['m_Metrics']['m_HorizontalAdvance'] for c in l if ord(c) in cmap)
                    for l in lines) * scale) + 40
    img = np.zeros((int(line_h * len(lines)) + 40, width), np.float32)
    missing = set()
    for li, l in enumerate(lines):
        pen_x = 20.0
        base_y = 20 + li * line_h + face['m_AscentLine'] * scale
        for c in l:
            gi = cmap.get(ord(c))
            if gi is None:
                missing.add(c)
                continue
            g = glyphs[gi]
            m, r = g['m_Metrics'], g['m_GlyphRect']
            if r['m_Width'] > 0:
                # TMP: quad = metrics box (+ padding), UV = glyph rect (+ padding), Y origin bottom
                p = meta['atlas']['padding']
                top_img = H - (r['m_Y'] + r['m_Height']) - p
                cell = atlas[top_img:top_img + r['m_Height'] + 2 * p, r['m_X'] - p:r['m_X'] + r['m_Width'] + p]
                qw = max(1, int(round(cell.shape[1] * scale)))
                qh = max(1, int(round(cell.shape[0] * scale)))
                import cv2
                q = cv2.resize(cell, (qw, qh), interpolation=cv2.INTER_LINEAR)
                x = int(round(pen_x + (m['m_HorizontalBearingX'] - p) * scale))
                y = int(round(base_y - (m['m_HorizontalBearingY'] + p) * scale))
                ys, xs = max(0, y), max(0, x)
                ye, xe = min(img.shape[0], y + qh), min(img.shape[1], x + qw)
                if ye > ys and xe > xs:
                    sub = q[ys - y:ye - y, xs - x:xe - x]
                    # SDF threshold with a little smoothing, like the TMP shader
                    soft = 0.5 / (meta['atlas']['gradientScale'] * scale) if scale else 0.05
                    alpha = np.clip((sub - 0.5) / (2 * soft) + 0.5, 0, 1)
                    img[ys:ye, xs:xe] = np.maximum(img[ys:ye, xs:xe], alpha)
            pen_x += m['m_HorizontalAdvance'] * scale
    out = Image.fromarray((255 - img * 255).astype(np.uint8), 'L')
    out.save(a.output)
    print('preview: %s%s' % (a.output, ('  MISSING: ' + ' '.join('U+%04X' % ord(c) for c in sorted(missing))) if missing else ''))
    return 1 if missing else 0


# ------------------------------------------------------------------------------------------ apply
def _template(entries, sample):
    """Fill `sample` into the structure of an existing entry (keeps field names TMP expects)."""
    if not entries:
        return sample
    t = entries[0]

    def merge(tpl, val):
        if isinstance(tpl, dict):
            return {k: merge(v, val.get(k, v) if isinstance(val, dict) else v) for k, v in tpl.items()}
        return type(tpl)(val) if isinstance(tpl, (int, float)) and isinstance(val, (int, float)) else val
    return merge(t, sample)


def set_float(mat_tree, name, value):
    floats = mat_tree.get('m_SavedProperties', {}).get('m_Floats')
    if floats is None:
        return False
    for item in floats:
        if isinstance(item, (list, tuple)) and item and item[0] == name:
            idx = floats.index(item)
            floats[idx] = (item[0], float(value)) if isinstance(item, tuple) else [item[0], float(value)]
            return True
        if isinstance(item, dict) and item.get('first') == name:
            item['second'] = float(value)
            return True
    return False


def cmd_apply(a):
    import UnityPy
    from UnityPy.enums import TextureFormat
    meta = json.load(open(os.path.join(a.atlas, 'tmp_font.json'), encoding='utf-8'))
    img = Image.open(os.path.join(a.atlas, 'atlas.png')).convert('L')
    env = UnityPy.load(a.unity_file)
    if a.game_root:
        from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
        ver = next(iter(env.files.values())).unity_version if env.files else '2020.3.0f1'
        gen = TypeTreeGenerator(str(ver))
        gen.load_local_game(a.game_root)
        env.typetree_generator = gen
    by_pid = {o.path_id: o for o in env.objects}
    target = None
    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if tree.get('m_Name') == a.font_asset and ('m_GlyphTable' in tree or 'm_glyphInfoList' in tree):
            target = (obj, tree)
            break
    if not target:
        sys.exit('TMP font asset %r not found in %s' % (a.font_asset, a.unity_file))
    obj, tree = target
    if 'm_GlyphTable' not in tree:
        sys.exit('legacy TMP schema (m_glyphInfoList): not written by this tool - build the asset in the '
                 'matching Unity/TMP version, or extend the tool after checking one glyph by hand')
    plan = []
    face = tree.get('m_FaceInfo', {})
    old_ps = face.get('m_PointSize') or 1
    new_face = dict(meta['faceInfo'])
    if a.keep_line_height and face.get('m_LineHeight'):
        new_face['m_LineHeight'] = face['m_LineHeight'] * meta['faceInfo']['m_PointSize'] / old_ps
    for k, v in new_face.items():
        if k in face:
            face[k] = type(face[k])(v) if isinstance(face[k], (int, float)) else v
    plan.append('FaceInfo: point size %s -> %s, line height %.1f' % (old_ps, face.get('m_PointSize'),
                                                                       face.get('m_LineHeight', 0)))
    tree['m_GlyphTable'] = [_template(tree['m_GlyphTable'], g) for g in meta['glyphTable']]
    tree['m_CharacterTable'] = [_template(tree['m_CharacterTable'], c) for c in meta['characterTable']]
    plan.append('glyphs %d, characters %d' % (len(tree['m_GlyphTable']), len(tree['m_CharacterTable'])))
    for k, v in (('m_AtlasWidth', meta['atlas']['width']), ('m_AtlasHeight', meta['atlas']['height']),
                 ('m_AtlasPadding', meta['atlas']['padding']), ('m_AtlasPopulationMode', 0)):
        if k in tree:
            tree[k] = v
            plan.append('%s = %s' % (k, v))
    if 'm_UsedGlyphRects' in tree:
        tree['m_UsedGlyphRects'] = [_template(tree['m_UsedGlyphRects'], r) for r in meta['usedGlyphRects']]
    if 'm_FreeGlyphRects' in tree:
        tree['m_FreeGlyphRects'] = []
    feat = tree.get('m_FontFeatureTable')
    if isinstance(feat, dict) and 'm_GlyphPairAdjustmentRecords' in feat:
        feat['m_GlyphPairAdjustmentRecords'] = []
        plan.append('kerning pairs cleared (glyph indices changed)')
    atl = (tree.get('m_AtlasTextures') or [None])[0]
    tex_obj = by_pid.get(atl['m_PathID']) if isinstance(atl, dict) and atl.get('m_FileID', 0) == 0 else None
    mat = tree.get('material') or tree.get('m_Material')
    mat_obj = by_pid.get(mat['m_PathID']) if isinstance(mat, dict) and mat.get('m_FileID', 0) == 0 else None
    plan.append('atlas texture: %s' % ('found (will replace, Alpha8 %dx%d)' % img.size if tex_obj else
                                       'NOT in this file (external) - replace it where it lives'))
    plan.append('material: %s' % ('found (_GradientScale=%d)' % meta['atlas']['gradientScale'] if mat_obj else 'not in this file'))
    print('\n'.join('  - ' + p for p in plan))
    if not a.write:
        print('dry run - add --write to save')
        return 0
    obj.save_typetree(tree)
    if tex_obj:
        tex = tex_obj.read()
        tex.set_image(img, target_format=TextureFormat.Alpha8)
        tex.save()
    if mat_obj:
        mt = mat_obj.read_typetree()
        for k, v in (('_GradientScale', meta['atlas']['gradientScale']), ('_TextureWidth', meta['atlas']['width']),
                     ('_TextureHeight', meta['atlas']['height'])):
            set_float(mt, k, v)
        mat_obj.save_typetree(mt)
    os.makedirs(a.output, exist_ok=True)
    dst = os.path.join(a.output, os.path.basename(a.unity_file))
    with open(dst, 'wb') as f:
        f.write(next(iter(env.files.values())).save(packer='original'))
    print('written: %s - verify: reload with unity_text.py scan, then one screen in game' % dst)
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='TextMeshPro SDF atlas builder for Arabic.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--font', required=True)
    b.add_argument('--text', action='append', help='translation file(s) or literal text')
    b.add_argument('--column')
    b.add_argument('--json-key-re')
    b.add_argument('--chars', help='extra characters')
    b.add_argument('--mode', choices=['visual', 'forms', 'logical'], default='visual')
    b.add_argument('--harakat', choices=['keep', 'strip', 'shadda'], default='keep')
    b.add_argument('--no-ascii', action='store_true')
    b.add_argument('--size', type=int, default=64, help='sampling point size (TMP "Sampling Point Size")')
    b.add_argument('--padding', type=int, default=7, help='SDF spread in texels (~10%% of size)')
    b.add_argument('--atlas', type=int, default=1024, help='start atlas size (grows if needed)')
    b.add_argument('--upsample', type=int, default=8, help='supersampling for the distance field')
    b.add_argument('--out', required=True)
    p = sub.add_parser('preview')
    p.add_argument('--atlas', required=True)
    p.add_argument('--text', action='append', required=True)
    p.add_argument('--mode', choices=['visual', 'forms', 'logical'])
    p.add_argument('--font-size', type=float, default=36)
    p.add_argument('-o', '--output', default='tmp_preview.png')
    ap_ = sub.add_parser('apply')
    ap_.add_argument('--unity-file', required=True)
    ap_.add_argument('--font-asset', required=True, help='m_Name of the TMP_FontAsset')
    ap_.add_argument('--atlas', required=True)
    ap_.add_argument('--game-root')
    ap_.add_argument('--keep-line-height', action='store_true', help='keep the original line spacing')
    ap_.add_argument('-o', '--output', required=True)
    ap_.add_argument('--write', action='store_true')
    a = ap.parse_args()
    return {'build': cmd_build, 'preview': cmd_preview, 'apply': cmd_apply}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
