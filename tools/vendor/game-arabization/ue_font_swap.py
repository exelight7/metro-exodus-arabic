#!/usr/bin/env python3
"""
ue_font_swap.py - inspect and replace the font inside an Unreal .ufont (cooked FontFace data).

Cooked UE games keep each FontFace's TTF/OTF either as a separate .ufont file (Lazy/Stream
loading policies) or inline in the .uexp (Inline policy). Depending on the engine version a
.ufont is the raw font file OR the font wrapped in serialized FFontFaceData (a header with a
length field before the font bytes). This tool finds the embedded font, tells you which case
you have, and swaps in your Arabic-capable font (font_merge.py output) keeping the wrapper
consistent. The new file goes into a *_P.pak at the same path.

  info  FILE              where the font is, its size, the wrapper, the family name
  swap  FILE NEW.ttf -o OUT   replace (updates a 32/64-bit length field that matches the old size)

For fonts embedded INLINE in a .uexp the export size in the .uasset must change too: use
UAssetGUI for that case (this tool refuses to write .uexp unless --force).
Always test: the game should show the new font in one screen before you build the whole patch.
"""
import os
import argparse
import struct
import sys

SIGS = (b'\x00\x01\x00\x00', b'OTTO', b'true', b'ttcf')


def font_end(data, off):
    """End offset of an sfnt starting at off (max table end), or None if not a valid sfnt."""
    try:
        num = struct.unpack_from('>H', data, off + 4)[0]
        if not 3 <= num <= 64:
            return None
        end = off + 12 + 16 * num
        for i in range(num):
            tag, _, toff, tlen = struct.unpack_from('>4sIII', data, off + 12 + 16 * i)
            if not all(32 <= c < 127 for c in tag):
                return None
            end = max(end, off + toff + tlen)
        return (end + 3) & ~3 if end <= len(data) + 3 else None
    except struct.error:
        return None


def family(data, off):
    try:
        from fontTools.ttLib import TTFont
        import io
        return TTFont(io.BytesIO(data[off:])).get('name').getDebugName(1)
    except Exception:
        return '?'


def locate(data):
    for off in range(0, min(len(data), 1 << 20)):
        if data[off:off + 4] in SIGS:
            end = font_end(data, off)
            if end:
                return off, min(end, len(data))
    return None, None


def describe(data, off, end):
    size = end - off
    fields = []
    for w, fmt in ((4, '<i'), (8, '<q')):
        if off >= w and struct.unpack_from(fmt, data, off - w)[0] in (size, len(data) - off):
            fields.append((off - w, fmt))
    return size, fields


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Inspect / replace the font inside an Unreal .ufont.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('info')
    i.add_argument('file')
    s = sub.add_parser('swap')
    s.add_argument('file')
    s.add_argument('font')
    s.add_argument('-o', '--output', required=True)
    s.add_argument('--force', action='store_true')
    a = ap.parse_args()
    data = open(a.file, 'rb').read()
    off, end = locate(data)
    if off is None:
        sys.exit('no TTF/OTF found in %s (compressed? encrypted? extract it with FModel first)' % a.file)
    size, fields = describe(data, off, end)
    kind = 'raw font file' if off == 0 and end >= len(data) - 3 else 'wrapped (header %d bytes, trailer %d bytes)' % (
        off, len(data) - end)
    if a.cmd == 'info':
        print('%s: %s | font at %d, %d bytes, family "%s" | length fields matching: %s'
              % (a.file, kind, off, size, family(data, off),
                 ', '.join('%s@%d' % (f, p) for p, f in fields) or 'none'))
        return 0
    if a.file.lower().endswith('.uexp') and not a.force:
        sys.exit('inline font in .uexp: the .uasset export size must change too -> use UAssetGUI (or --force at your own risk)')
    new = open(a.font, 'rb').read()
    if new[:4] not in SIGS:
        sys.exit('%s is not a TTF/OTF (woff? convert first)' % a.font)
    if off != 0 and not fields:
        sys.exit('wrapped font without a recognisable length field - edit with UAssetGUI instead')
    head = bytearray(data[:off])
    for p, fmt in fields:
        old = struct.unpack_from(fmt, head, p)[0]
        struct.pack_into(fmt, head, p, len(new) + (old - size))
    out = bytes(head) + new + data[end:]
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, 'wb') as f:
        f.write(out)
    o2, e2 = locate(out)
    ok = o2 == off and e2 is not None and out[o2:o2 + len(new)] == new
    print('%s -> %s (%s, %d -> %d font bytes) verify: %s' % (a.file, a.output, kind, size, len(new),
                                                           'OK' if ok else 'FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
