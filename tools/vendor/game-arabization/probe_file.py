#!/usr/bin/env python3
"""
probe_file.py - first look at an unknown / "encrypted" game file.

Answers the questions you need before choosing a tool:
  1. Is it a KNOWN container?  (~70 signatures: Unity, Unreal pak/IoStore, CRI CPK/USM,
     Bink, RPG Maker, Ren'Py, Godot, GameMaker, Kirikiri, KH2 BAR, Wwise, FMOD, fonts,
     images, audio, zip/zlib/zstd/lz4/xz ...)
  2. Is it compressed or encrypted?  (Shannon entropy per block: text ~4-5, binary
     5-7, compressed OR encrypted ~7.9-8.0)
  3. Is it a SIMPLE obfuscation?  (single-byte XOR brute force, repeating-key XOR from
     a known plaintext: --known '{"' for JSON, --known PNG, --known UnityFS ...)
  4. Are there compressed streams inside?  (scan for zlib/gzip/zstd/lz4 headers and try
     to inflate them)
  5. Where is the text?  (ASCII / UTF-8 / UTF-16LE strings with offsets)

Usage
  probe_file.py FILE [FILE ...]          summary for each file
  probe_file.py FILE --strings 8         + strings of length >= 8 (first 60)
  probe_file.py FILE --scan              + embedded compressed streams
  probe_file.py FILE --known '{"'        + derive XOR key assuming the plain file starts with that
  probe_file.py --diff A B               where two versions of a file differ (find headers/keys)
  probe_file.py FILE --xor-key 0x5A --out decoded.bin       apply a XOR key
  probe_file.py FILE --xor-key "a1b2c3" --skip 16 --out x   repeating key, skip a header
Standard library only (zstandard / lz4 used if installed).
"""
import argparse
import collections
import math
import os
import re
import struct
import sys
import zlib
import bz2
import lzma

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError, ImportError):
    pass

# (offset, magic bytes, description)
SIGS = [
    (0, b'UnityFS', 'Unity AssetBundle (UnityFS) -> UnityPy / UABEA / AssetStudio'),
    (0, b'UnityWeb', 'Unity web bundle (old)'), (0, b'UnityRaw', 'Unity raw bundle (old)'),
    (0, b'UnityArchive', 'Unity archive'),
    (0, b'\xaf\x1b\xb1\xfa', 'IL2CPP global-metadata.dat -> Il2CppDumper / Cpp2IL'),
    (0, b'-==--==--==--==-', 'Unreal IoStore .utoc (UE5) -> FModel / retoc'),
    (0, b'CPK ', 'CRI CPK archive -> CriPakTools / YACpkTool'),
    (0, b'CRID', 'CRI USM video (Sofdec) -> WannaCRI (may need a key)'),
    (0, b'@UTF', 'CRI @UTF table'), (0, b'AFS\x00', 'AFS archive (CRI/Sega)'),
    (0, b'HCA\x00', 'CRI HCA audio'), (0, b'\xc8\xc3\xc1\x00', 'CRI HCA audio (masked header)'),
    (0, b'BIKb', 'Bink 1 video'), (0, b'BIKf', 'Bink 1 video'), (0, b'BIKg', 'Bink 1 video'),
    (0, b'BIKh', 'Bink 1 video'), (0, b'BIKi', 'Bink 1 video'), (0, b'KB2', 'Bink 2 video (.bk2)'),
    (0, b'RPGMV\x00\x00\x00', 'RPG Maker MV/MZ encrypted asset -> rpgmv_crypt.py'),
    (0, b'RGSSAD\x00', 'RPG Maker XP/VX/VX Ace archive (RGSSAD) -> RPGMakerDecrypter'),
    (0, b'RPA-3.0 ', "Ren'Py archive RPA-3.0 -> unrpa"), (0, b'RPA-2.0 ', "Ren'Py archive RPA-2.0 -> unrpa"),
    (0, b'RENPY RPC2', "Ren'Py compiled script .rpyc -> unrpyc"),
    (0, b'GDPC', 'Godot PCK -> GDRE Tools (gdsdecomp)'),
    (0, b'XP3\r\n \n\x1a\x8b\x67\x01', 'Kirikiri XP3 archive -> GARbro / KrkrExtract'),
    (0, b'BAR\x01', 'Square Enix BAR archive (Kingdom Hearts) -> OpenKH'),
    (0, b'IMGD', 'KH image (IMGD) -> OpenKH'), (0, b'IMGZ', 'KH image pack (IMGZ) -> OpenKH'),
    (0, b'BKHD', 'Wwise SoundBank (.bnk)'), (0, b'AKPK', 'Wwise package (.pck)'),
    (0, b'FSB5', 'FMOD sound bank (FSB5)'), (0, b'BTDX', 'Bethesda BA2 archive'),
    (0, b'BSA\x00', 'Bethesda BSA archive'), (0, b'PSB\x00', 'PSB (E-mote / M2)'),
    (0, b'mdf\x00', 'MDF = zlib-compressed PSB (M2)'),
    (0, b'\x1bLua', 'Lua bytecode -> unluac / luadec'), (0, b'\x1bLJ', 'LuaJIT bytecode'),
    (0, b'SQLite format 3\x00', 'SQLite database'),
    (0, b'\x89PNG\r\n\x1a\n', 'PNG image'), (0, b'\xff\xd8\xff', 'JPEG image'), (0, b'DDS ', 'DDS texture'),
    (0, b'\xabKTX 11', 'KTX texture'), (0, b'\xabKTX 20', 'KTX2 texture'), (0, b'GIF8', 'GIF image'),
    (0, b'OggS', 'Ogg (Vorbis/Opus/Theora)'), (0, b'fLaC', 'FLAC audio'), (0, b'ID3', 'MP3 (ID3)'),
    (0, b'\x1a\x45\xdf\xa3', 'Matroska / WebM video'), (4, b'ftyp', 'MP4 / MOV video'),
    (0, b'\x00\x01\x00\x00\x00', 'TrueType font'), (0, b'OTTO', 'OpenType CFF font'),
    (0, b'ttcf', 'TrueType collection'), (0, b'wOFF', 'WOFF font'), (0, b'wOF2', 'WOFF2 font'),
    (0, b'info face=', 'BMFont descriptor (text)'), (0, b'BMF\x03', 'BMFont descriptor (binary)'),
    (0, b'PK\x03\x04', 'ZIP (also .apk .jar .nw .pak of some engines)'), (0, b'7z\xbc\xaf\x27\x1c', '7-Zip'),
    (0, b'Rar!\x1a\x07', 'RAR'), (0, b'\x1f\x8b', 'gzip'), (0, b'\x28\xb5\x2f\xfd', 'Zstandard'),
    (0, b'\x04\x22\x4d\x18', 'LZ4 frame'), (0, b'\xfd7zXZ\x00', 'xz'), (0, b'BZh', 'bzip2'),
    (0, b'MZ', 'Windows executable / DLL (check for .NET: dnSpy / ILSpy)'),
    (0, b'\x7fELF', 'ELF executable'),
    (0, b'\xef\xbb\xbf', 'UTF-8 text with BOM'), (0, b'\xff\xfe', 'UTF-16LE text (BOM)'),
    (0, b'\xfe\xff', 'UTF-16BE text (BOM)'),
]


def entropy(b):
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def printable_ratio(b):
    if not b:
        return 0.0
    ok = sum(1 for x in b if 32 <= x < 127 or x in (9, 10, 13))
    return ok / len(b)


_EN = set(b' etaoinshrdlu\n')


def text_score(b):
    """How much do these bytes look like real text? ~0.4-0.7 for English/JSON, ~0.4 for
    UTF-8 Arabic, ~1.0 for UTF-16 text, ~0.05 for random or XOR-scrambled data."""
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    en = sum(c[x] for x in _EN) / n
    ar8 = sum(c[x] for x in (0xD8, 0xD9, 0xDA, 0xDB)) / n * 2.2
    odd = b[1::2]
    u16 = (odd.count(0) + odd.count(6)) / max(len(odd), 1) * 0.9 if len(b) > 8 else 0
    return max(en, ar8, u16)


def looks_like_text(b):
    if not b:
        return False
    for enc in ('utf-8', 'utf-16-le'):
        chunk = b[:len(b) - (len(b) % 2)] if enc == 'utf-16-le' else b
        for cut in range(4):
            try:
                s = chunk[:len(chunk) - cut].decode(enc)
                break
            except UnicodeDecodeError:
                s = None
        if not s:
            continue
        good = sum(1 for ch in s if ch.isprintable() or ch in '\r\n\t') / len(s)
        letters = sum(1 for ch in s if ch.isalpha() or ch == ' ') / len(s)
        if good > 0.97 and letters > 0.45 and text_score(b) > 0.2:
            return True
    return False


def verdict(e, is_text):
    if is_text:
        return 'plain text'
    if e > 7.9:
        return 'compressed OR encrypted (high entropy) - check for a container header / try --scan'
    if e > 7.2:
        return 'packed / compressed-ish binary or weak encryption on structured data'
    if e < 1.0:
        return 'mostly constant bytes (padding / zeros)'
    return 'structured binary or SIMPLE obfuscation (XOR keeps text-like entropy) - see XOR lines below'


def xor_single(data):
    sample = data[:65536]
    best = []
    for k in range(1, 256):
        best.append((text_score(bytes(b ^ k for b in sample)), k))
    best.sort(reverse=True)
    return best[:3]


def guess_keysizes(data, max_len=64):
    """Normalized Hamming distance between consecutive key-sized blocks (lower = likelier)."""
    sample = data[:16384]
    res = []
    for ks in range(1, max_len + 1):
        nb = min(len(sample) // ks, 80)
        if nb < 6:
            break
        blocks = [sample[i * ks:(i + 1) * ks] for i in range(nb)]
        dist = sum(sum(bin(x ^ y).count('1') for x, y in zip(blocks[i], blocks[i + 1])) for i in range(nb - 1))
        res.append((dist / (nb - 1) / ks, ks))
    return sorted(res)


def crack_repeating_xor(data, max_len=64):
    """Classic Vigenere attack: try the likeliest key sizes, solve each column as single-byte XOR."""
    sample = data[:65536]
    best = None
    for _, ks in guess_keysizes(sample, max_len)[:6]:
        key = bytes(max(range(256), key=lambda k: text_score(bytes(b ^ k for b in sample[i::ks])))
                    for i in range(ks))
        # shrink k3y!k3y! -> k3y!
        for p in range(1, ks + 1):
            if ks % p == 0 and key == key[:p] * (ks // p):
                key = key[:p]
                break
        dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(sample[:8192]))
        sc = text_score(dec)
        if best is None or sc > best[0] + 0.02 or (abs(sc - best[0]) <= 0.02 and len(key) < len(best[1])):
            best = (sc, key)
    return best


def identify(data):
    hits = []
    for off, magic, desc in SIGS:
        if data[off:off + len(magic)] == magic:
            hits.append(desc)
    if data[:2] in (b'\x78\x01', b'\x78\x5e', b'\x78\x9c', b'\x78\xda'):
        hits.append('zlib stream')
    if data[:4] == b'FORM' and data[8:12] == b'GEN8':
        hits.append('GameMaker data.win (FORM/GEN8) -> UndertaleModTool')
    if data[:4] == b'RIFF':
        hits.append('RIFF container (%s)' % data[8:12].decode('latin-1'))
    tail = data[-300:]
    if b'\xe1\x12\x6f\x5a' in tail:
        hits.append('Unreal .pak (footer magic 0x5A6F12E1) -> FModel / repak (AES key if encrypted)')
    head = data[:4096]
    stripped = head.lstrip(b'\xef\xbb\xbf \t\r\n')
    if stripped[:1] in (b'{', b'[') and printable_ratio(head) > 0.85:
        hits.append('JSON-like text')
    elif stripped[:5] == b'<?xml' or stripped[:1] == b'<' and printable_ratio(head) > 0.85:
        hits.append('XML / markup text')
    if len(head) > 64 and (head[1::2].count(0) + head[1::2].count(6)) > len(head) * 0.4 \
            and head[0::2].count(0) < len(head) * 0.1:
        hits.append('probably UTF-16LE text / strings')
    return hits


def block_entropies(data, size=4096):
    return [entropy(data[i:i + size]) for i in range(0, len(data), size)] or [0.0]


def scan_streams(data, limit=40):
    found = []
    for m in re.finditer(rb'\x78[\x01\x5e\x9c\xda]|\x1f\x8b\x08|\x28\xb5\x2f\xfd|\x04\x22\x4d\x18', data):
        off = m.start()
        kind = None
        out = b''
        try:
            if data[off] == 0x78:
                d = zlib.decompressobj()
                out = d.decompress(data[off:off + 4 * 1024 * 1024], 1 << 20)
                kind = 'zlib'
            elif data[off] == 0x1f:
                d = zlib.decompressobj(16 + zlib.MAX_WBITS)
                out = d.decompress(data[off:off + 4 * 1024 * 1024], 1 << 20)
                kind = 'gzip'
            elif data[off] == 0x28:
                import zstandard
                out = zstandard.ZstdDecompressor().decompressobj().decompress(data[off:off + 4 * 1024 * 1024])[:1 << 20]
                kind = 'zstd'
            else:
                import lz4.frame
                out = lz4.frame.decompress(data[off:off + 4 * 1024 * 1024])[:1 << 20]
                kind = 'lz4'
        except Exception:
            continue
        if len(out) >= 16:
            found.append((off, kind, len(out), identify(out)[:1], out[:40]))
            if len(found) >= limit:
                break
    return found


def strings(data, min_len, limit):
    res = []
    for m in re.finditer(rb'[\x20-\x7e\t]{%d,}' % min_len, data):
        res.append((m.start(), 'ascii', m.group().decode('ascii')))
        if len(res) >= limit:
            break
    for m in re.finditer(rb'(?:[\xc2-\xf4][\x80-\xbf]{1,3}|[\x20-\x7e]){%d,}' % min_len, data):
        try:
            s = m.group().decode('utf-8')
        except UnicodeDecodeError:
            continue
        if any(ord(c) > 127 for c in s):
            res.append((m.start(), 'utf-8', s))
        if len(res) >= limit * 2:
            break
    # UTF-16LE: ASCII (xx 00) or Arabic / presentation forms (xx 06, xx 05, xx FB, xx FE)
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00|[\x00-\xff][\x05\x06\xfb\xfe]){%d,}' % min_len, data):
        try:
            s = m.group().decode('utf-16-le')
        except UnicodeDecodeError:
            continue
        if sum(ch.isprintable() for ch in s) > len(s) * 0.9:
            res.append((m.start(), 'utf-16le', s))
        if len(res) >= limit * 3:
            break
    return sorted(res)[:limit]


def parse_key(k):
    k = k.strip()
    if k.lower().startswith('0x') and len(k) <= 4:
        return bytes([int(k, 16)])
    k = k[2:] if k.lower().startswith('0x') else k
    if re.fullmatch(r'[0-9a-fA-F]+', k) and len(k) % 2 == 0:
        return bytes.fromhex(k)
    return k.encode('utf-8')


def probe(path, a):
    with open(path, 'rb') as f:
        data = f.read()
    n = len(data)
    print('=' * 78)
    print('%s  (%s bytes)' % (path, format(n, ',')))
    print('-' * 78)
    print('head: %s' % data[:32].hex(' '))
    print('      %s' % ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32]))
    ids = identify(data)
    print('signature: %s' % ('; '.join(ids) if ids else 'unknown'))
    be = block_entropies(data)
    e = entropy(data[:1 << 22])
    pr = printable_ratio(data[:65536])
    print('entropy: %.2f bits/byte (blocks min %.2f / max %.2f) | printable %.0f%%' % (e, min(be), max(be), pr * 100))
    if len(be) > 3 and min(be) < 6.5 < max(be):
        hi = sum(1 for x in be if x > 7.5)
        print('         mixed: %d/%d blocks look compressed/encrypted -> header + payload layout' % (hi, len(be)))
    is_text = looks_like_text(data[:65536])
    print('verdict: %s' % verdict(e, is_text))
    if not is_text and not ids and e < 7.5:
        top = xor_single(data)
        if top[0][0] > 0.3 and looks_like_text(bytes(b ^ top[0][1] for b in data[:8192])):
            print('single-byte XOR: key 0x%02X -> text score %.2f  (try --xor-key 0x%02X --out decoded.bin)'
                  % (top[0][1], top[0][0], top[0][1]))
        else:
            r = crack_repeating_xor(data)
            if r and r[0] > 0.3 and len(r[1]) <= 32 and \
                    looks_like_text(bytes(b ^ r[1][i % len(r[1])] for i, b in enumerate(data[:8192]))):
                k = r[1]
                shown = k.decode('latin-1') if all(32 <= x < 127 for x in k) else ''
                print('repeating-key XOR: key %s%s (%d bytes) -> text score %.2f  (try --xor-key %s --out decoded.bin)'
                      % (k.hex(), " '%s'" % shown if shown else '', len(k), r[0], k.hex()))
            else:
                ks = guess_keysizes(data)[:3]
                print('no simple XOR found; key-size hints (Hamming): %s - likely real encryption or '
                      'compression: find the decryption routine in the game code' % ', '.join('%d' % k for _, k in ks))
    if a.known:
        known = {'PNG': b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR', 'JSON': b'{"', 'UnityFS': b'UnityFS\x00',
                 'OGG': b'OggS\x00\x02', 'RIFF': b'RIFF'}.get(a.known) or \
            a.known.encode('utf-8').decode('unicode_escape').encode('latin-1')   # allows \\n \\x00 escapes
        skip = a.skip or 0
        key = bytes(x ^ y for x, y in zip(data[skip:skip + len(known)], known))
        print('XOR with known plaintext %r at offset %d -> key bytes: %s' % (known, skip, key.hex(' ')))
        if len(key) >= 4 and len(set(key)) == 1:
            print('   -> constant: single-byte key 0x%02X' % key[0])
        else:
            for p in range(1, len(key) // 2 + 1):
                if all(key[i] == key[i % p] for i in range(len(key))):
                    print('   -> repeats every %d bytes: key %s' % (p, key[:p].hex()))
                    break
    if a.scan:
        streams = scan_streams(data)
        print('embedded compressed streams: %d' % len(streams))
        for off, kind, size, idn, head in streams[:20]:
            prev = ''
            for enc in ('utf-8', 'utf-16-le'):
                try:
                    t = head[:40].decode(enc)
                    if t and sum(ch.isprintable() or ch.isspace() for ch in t) > len(t) * 0.9:
                        prev = t.replace('\n', ' ')[:30]
                        break
                except UnicodeDecodeError:
                    pass
            print('  @0x%08X %-4s -> %8d bytes %s  %s' % (off, kind, size, idn or '', prev or repr(head[:24])))
    if a.strings:
        print('strings (min %d):' % a.strings)
        for off, enc, s in strings(data, a.strings, 60):
            print('  @0x%08X %-8s %s' % (off, enc, s[:100]))
    if a.xor_key and a.out:
        key = parse_key(a.xor_key)
        skip = a.skip or 0
        body = bytes(b ^ key[i % len(key)] for i, b in enumerate(data[skip:]))
        with open(a.out, 'wb') as f:
            f.write((data[:skip] if a.keep_header else b'') + body)
        print('wrote %s (key %s, skipped %d header bytes%s)' % (a.out, key.hex(), skip, ', header kept' if a.keep_header else ''))


def diff(p1, p2):
    with open(p1, 'rb') as f:
        a = f.read()
    with open(p2, 'rb') as f:
        b = f.read()
    print('A %s: %d bytes | B %s: %d bytes' % (p1, len(a), p2, len(b)))
    n = min(len(a), len(b))
    ranges = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            ranges.append((i, j))
            i = j
        else:
            i += 1
    same = n - sum(j - i for i, j in ranges)
    print('identical bytes in common length: %d (%.1f%%), %d differing ranges' % (same, 100.0 * same / max(n, 1), len(ranges)))
    for i, j in ranges[:30]:
        print('  0x%08X-0x%08X (%d bytes)  A:%s  B:%s' % (i, j, j - i, a[i:min(j, i + 12)].hex(), b[i:min(j, i + 12)].hex()))
    if len(ranges) > 30:
        print('  ... %d more' % (len(ranges) - 30))


def main():
    ap = argparse.ArgumentParser(description='Identify / triage unknown or encrypted game files.')
    ap.add_argument('files', nargs='*')
    ap.add_argument('--strings', type=int, metavar='MINLEN', help='list strings of at least MINLEN')
    ap.add_argument('--scan', action='store_true', help='scan for embedded compressed streams')
    ap.add_argument('--known', help='known plaintext at start (or PNG / JSON / UnityFS / OGG / RIFF)')
    ap.add_argument('--skip', type=int, help='header bytes to skip for --known / --xor-key')
    ap.add_argument('--xor-key', help='0x5A, hex "a1b2c3", or text key')
    ap.add_argument('--keep-header', action='store_true', help='with --out: keep the skipped header bytes')
    ap.add_argument('--out', help='output for --xor-key')
    ap.add_argument('--diff', nargs=2, metavar=('A', 'B'))
    a = ap.parse_args()
    if a.diff:
        diff(*a.diff)
        return
    if not a.files:
        ap.error('give at least one file (or --diff A B)')
    for p in a.files:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in sorted(fs)[:200]:
                    probe(os.path.join(root, f), a)
        else:
            probe(p, a)


if __name__ == '__main__':
    main()
