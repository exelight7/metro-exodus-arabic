#!/usr/bin/env python3
"""
rpgmv_crypt.py - decrypt / re-encrypt RPG Maker MV & MZ encrypted assets.

Standard MV/MZ "encryption" (the one in the editor's deployment dialog):
  file = 16-byte header "RPGMV\\0\\0\\0\\0\\3\\1\\0\\0\\0\\0\\0"  +  original file whose FIRST 16 bytes
         are XORed with the 16-byte key from data/System.json "encryptionKey" (32 hex chars).
  MV extensions: .rpgmvp (png) .rpgmvo (ogg) .rpgmvm (m4a) .rpgmvw (wav)
  MZ extensions: .png_ .ogg_ .m4a_ .wav_
Only images/audio are encrypted this way; data/*.json and js/ are plain text.
If a game's JSON is unreadable too, it uses a CUSTOM scheme (e.g. The Coffin of Andy and
Leyley's .k9a files) -> use that game's community tools or read its JS loader.

Usage
  rpgmv_crypt.py findkey GAME_DIR              key from System.json, else recovered from any encrypted PNG
  rpgmv_crypt.py decrypt GAME_DIR/www/img --out dec_img [--key HEX]
  rpgmv_crypt.py encrypt edited_img --out enc_img --key HEX [--mz]
  rpgmv_crypt.py verify  ORIGINAL_ENC_DIR REENCRYPTED_DIR      (byte-compare after a roundtrip)
Edited images must keep the same file name (and ideally the same size) as the originals.
"""
import argparse
import hashlib
import json
import os
import sys

HEADER = bytes.fromhex('5250474d560000000003010000000000')
PNG16 = bytes.fromhex('89504e470d0a1a0a0000000d49484452')
DEC_EXT = {'.rpgmvp': '.png', '.rpgmvo': '.ogg', '.rpgmvm': '.m4a', '.rpgmvw': '.wav',
           '.png_': '.png', '.ogg_': '.ogg', '.m4a_': '.m4a', '.wav_': '.wav'}
ENC_MV = {'.png': '.rpgmvp', '.ogg': '.rpgmvo', '.m4a': '.rpgmvm', '.wav': '.rpgmvw'}
ENC_MZ = {'.png': '.png_', '.ogg': '.ogg_', '.m4a': '.m4a_', '.wav': '.wav_'}


def find_system_json(path):
    """System.json in PATH, under it (www/data, data) or in up to 3 parent folders."""
    if os.path.isfile(path) and path.lower().endswith('system.json'):
        return path
    here = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))
    for _ in range(4):
        for cand in ('www/data/System.json', 'data/System.json', 'System.json'):
            p = os.path.join(here, cand)
            if os.path.isfile(p):
                return p
        here = os.path.dirname(here)
    return None


def key_from_system(path):
    sj = find_system_json(path)
    if not sj:
        return None, None
    with open(sj, encoding='utf-8-sig') as f:
        d = json.load(f)
    k = d.get('encryptionKey')
    info = 'hasEncryptedImages=%s hasEncryptedAudio=%s' % (d.get('hasEncryptedImages'), d.get('hasEncryptedAudio'))
    return (bytes.fromhex(k) if k else None), '%s (%s)' % (sj, info)


def key_from_png(path):
    for root, _, files in os.walk(path) if os.path.isdir(path) else [(os.path.dirname(path), None, [os.path.basename(path)])]:
        for fn in files:
            if os.path.splitext(fn)[1].lower() in ('.rpgmvp', '.png_'):
                with open(os.path.join(root, fn), 'rb') as f:
                    blob = f.read(32)
                if blob[:16] == HEADER and len(blob) == 32:
                    return bytes(a ^ b for a, b in zip(blob[16:32], PNG16)), os.path.join(root, fn)
    return None, None


def decrypt_bytes(blob, key):
    if blob[:16] != HEADER:
        raise ValueError('no RPGMV header')
    body = bytearray(blob[16:])
    for i in range(min(16, len(body))):
        body[i] ^= key[i]
    return bytes(body)


def encrypt_bytes(blob, key):
    body = bytearray(blob)
    for i in range(min(16, len(body))):
        body[i] ^= key[i]
    return HEADER + bytes(body)


def iter_files(path, exts):
    if os.path.isfile(path):
        yield os.path.dirname(path), os.path.basename(path)
        return
    for root, _, files in os.walk(path):
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() in exts:
                yield root, fn


def get_key(a, search_from):
    if a.key:
        return bytes.fromhex(a.key)
    k, src = key_from_system(search_from)
    if k:
        print('key from %s' % src)
        return k
    k, src = key_from_png(search_from)
    if k:
        print('key recovered from PNG header of %s' % src)
        return k
    sys.exit('no key: pass --key HEX (32 hex chars from System.json "encryptionKey")')


def main():
    ap = argparse.ArgumentParser(description='RPG Maker MV/MZ asset decrypt / encrypt.')
    ap.add_argument('cmd', choices=['findkey', 'decrypt', 'encrypt', 'verify'])
    ap.add_argument('path')
    ap.add_argument('path2', nargs='?')
    ap.add_argument('--key', help='32 hex chars')
    ap.add_argument('--out', help='output folder (keeps relative paths)')
    ap.add_argument('--mz', action='store_true', help='encrypt with MZ extensions (.png_ ...)')
    a = ap.parse_args()

    if a.cmd == 'findkey':
        k, src = key_from_system(a.path)
        if k:
            print('System.json key: %s   %s' % (k.hex(), src))
        k2, src2 = key_from_png(a.path)
        if k2:
            print('key from encrypted PNG: %s   (%s)' % (k2.hex(), src2))
        if k and k2 and k != k2:
            print('WARNING: keys differ - assets were encrypted with another key')
        if not k and not k2:
            print('no key found (no System.json key and no encrypted PNG)')
        return 0

    if a.cmd == 'verify':
        if not a.path2:
            ap.error('verify needs two folders')
        bad = n = 0
        for root, fn in iter_files(a.path, set(DEC_EXT)):
            rel = os.path.relpath(os.path.join(root, fn), a.path)
            other = os.path.join(a.path2, rel)
            n += 1
            if not os.path.isfile(other):
                print('missing %s' % rel)
                bad += 1
                continue
            h1 = hashlib.sha256(open(os.path.join(root, fn), 'rb').read()).hexdigest()
            h2 = hashlib.sha256(open(other, 'rb').read()).hexdigest()
            if h1 != h2:
                print('DIFF %s' % rel)
                bad += 1
        print('%d files compared, %d different/missing' % (n, bad))
        return 1 if bad else 0

    if not a.out:
        ap.error('--out is required (originals are never overwritten)')
    if a.cmd == 'decrypt':
        key = get_key(a, os.path.dirname(os.path.abspath(a.path)) if os.path.isfile(a.path) else a.path)
        n = skipped = 0
        for root, fn in iter_files(a.path, set(DEC_EXT)):
            src = os.path.join(root, fn)
            base, ext = os.path.splitext(fn)
            rel = os.path.relpath(root, a.path) if os.path.isdir(a.path) else '.'
            dst_dir = os.path.join(a.out, rel)
            os.makedirs(dst_dir, exist_ok=True)
            with open(src, 'rb') as f:
                blob = f.read()
            try:
                plain = decrypt_bytes(blob, key)
            except ValueError:
                skipped += 1
                continue
            if ext.lower() in ('.rpgmvp', '.png_') and plain[:8] != PNG16[:8]:
                sys.exit('wrong key: %s does not decrypt to a PNG' % src)
            with open(os.path.join(dst_dir, base + DEC_EXT[ext.lower()]), 'wb') as f:
                f.write(plain)
            n += 1
        print('decrypted %d files -> %s (%d skipped: no header)' % (n, a.out, skipped))
    else:
        if not a.key:
            ap.error('encrypt needs --key (use findkey first)')
        key = bytes.fromhex(a.key)
        table = ENC_MZ if a.mz else ENC_MV
        n = 0
        for root, fn in iter_files(a.path, set(table)):
            base, ext = os.path.splitext(fn)
            rel = os.path.relpath(root, a.path) if os.path.isdir(a.path) else '.'
            dst_dir = os.path.join(a.out, rel)
            os.makedirs(dst_dir, exist_ok=True)
            with open(os.path.join(root, fn), 'rb') as f:
                blob = f.read()
            enc = encrypt_bytes(blob, key)
            assert decrypt_bytes(enc, key) == blob
            with open(os.path.join(dst_dir, base + table[ext.lower()]), 'wb') as f:
                f.write(enc)
            n += 1
        print('encrypted %d files -> %s' % (n, a.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
