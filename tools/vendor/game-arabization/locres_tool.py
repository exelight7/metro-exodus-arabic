#!/usr/bin/env python3
"""
locres_tool.py - read / translate / write Unreal Engine 4 & 5 .locres files (all versions 0-3).

  info    version, namespaces, keys, unique strings, encodings
  export  -> CSV: namespace,key,source,target   (source = the text currently in the file)
  import  CSV translations -> new .locres; everything except the strings stays byte-identical
          (namespace/key hashes and source-string hashes are kept, so the game still finds every key)

Layout handled (from the engine's FTextLocalizationResource::LoadFromArchive):
  v0 Legacy        no magic, strings inline per key
  v1 Compact       magic + version + offset to a shared array of FString
  v2 Optimized_CRC32, v3 Optimized_CityHash64_UTF16
                   + entries count, uint32 hash before each namespace/key, array items = FString + int32 refcount
FString: int32 length (+ = ANSI incl. NUL, - = UTF-16LE incl. NUL). Arabic is written as UTF-16.

Usage
  locres_tool.py info Game.locres
  locres_tool.py export Game.locres -o game_en.csv
  locres_tool.py import Game.locres game_ar.csv -o Game_ar.locres [--target-col target]
  locres_tool.py roundtrip Game.locres      (parse + rewrite unchanged -> must be byte-identical)
Arabic in Unreal 4/5 is usually shaped by the engine: keep the CSV LOGICAL (no ar_shape.py) unless
your T01 test showed disconnected letters. Put the result in a *_P.pak with the same path.
"""
import argparse
import csv
import io
import os
import struct
import sys

VERSIONS = {0: 'Legacy', 1: 'Compact', 2: 'Optimized_CRC32', 3: 'Optimized_CityHash64_UTF16'}


def _magic_bytes():
    # FGuid(0x7574140E, 0xFC034A67, 0x9B1A9F86, 0x96C6E81D) serialized as 4 little-endian uint32
    return struct.pack('<4I', 0x7574140E, 0xFC034A67, 0x9B1A9F86, 0x96C6E81D)


MAGIC = _magic_bytes()


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def i64(self):
        v = struct.unpack_from('<q', self.d, self.p)[0]
        self.p += 8
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return '', 'ansi'
        if n > 0:
            raw = self.d[self.p:self.p + n]
            self.p += n
            return raw[:-1].decode('latin-1'), 'ansi'
        n = -n
        raw = self.d[self.p:self.p + 2 * n]
        self.p += 2 * n
        return raw[:-2].decode('utf-16-le', 'surrogatepass'), 'utf16'


def w_fstring(s, enc=None):
    if s == '' and enc != 'utf16':
        return struct.pack('<i', 0)
    if enc == 'ansi' or (enc is None and all(ord(c) < 128 for c in s)):
        try:
            b = s.encode('latin-1') + b'\x00'
            return struct.pack('<i', len(b)) + b
        except UnicodeEncodeError:
            pass
    b = s.encode('utf-16-le', 'surrogatepass') + b'\x00\x00'
    return struct.pack('<i', -(len(b) // 2)) + b


class Locres:
    def __init__(self, data):
        self.data = data
        r = Reader(data)
        if data[:16] == MAGIC:
            r.p = 16
            self.version = r.u8()
        else:
            self.version = 0
        if self.version > 3:
            raise SystemExit('unknown locres version %d' % self.version)
        self.strings = []          # [text, enc, refcount_or_None]
        self.array_offset = None
        if self.version >= 1:
            self.array_offset_pos = r.p
            self.array_offset = r.i64()
            if self.array_offset != -1:
                save = r.p
                r.p = self.array_offset
                count = r.i32()
                for _ in range(count):
                    s, enc = r.fstring()
                    rc = r.i32() if self.version >= 2 else None
                    self.strings.append([s, enc, rc])
                self.array_end = r.p
                r.p = save
        if self.version >= 2:
            self.entries_count = r.u32()
        self.entries = []          # dict(ns, key, srchash, index_pos, index | inline)
        ns_count = r.u32()
        for _ in range(ns_count):
            if self.version >= 2:
                r.u32()
            ns, _ = r.fstring()
            kc = r.u32()
            for _ in range(kc):
                if self.version >= 2:
                    r.u32()
                key, _ = r.fstring()
                srchash = r.u32()
                if self.version >= 1:
                    pos = r.p
                    idx = r.i32()
                    self.entries.append({'ns': ns, 'key': key, 'src': srchash, 'pos': pos, 'idx': idx})
                else:
                    start = r.p
                    s, enc = r.fstring()
                    self.entries.append({'ns': ns, 'key': key, 'src': srchash, 'pos': start, 'end': r.p,
                                         'text': s, 'enc': enc})
        self.body_end = r.p

    def text_of(self, e):
        return e['text'] if self.version == 0 else self.strings[e['idx']][0]

    def build(self, new_texts=None):
        """new_texts: {(ns,key): text}. Returns bytes."""
        new_texts = new_texts or {}
        if self.version == 0:
            out = bytearray()
            last = 0
            for e in self.entries:
                t = new_texts.get((e['ns'], e['key']))
                if t is None:
                    continue
                out += self.data[last:e['pos']] + w_fstring(t)
                last = e['end']
            out += self.data[last:]
            return bytes(out)
        strings = [list(s) for s in self.strings]
        users = {}
        for e in self.entries:
            users.setdefault(e['idx'], []).append(e)
        new_idx = {}
        for idx, es in users.items():
            wanted = [new_texts.get((e['ns'], e['key'])) for e in es]
            if all(w is None for w in wanted):
                continue
            first = next(w for w in wanted if w is not None)
            if all(w == first or w is None for w in wanted) and all(w is not None for w in wanted):
                strings[idx][0], strings[idx][1] = first, None
                continue
            # keys sharing one string now need different texts: split them
            keep_old = [e for e, w in zip(es, wanted) if w is None]
            groups = {}
            for e, w in zip(es, wanted):
                if w is not None:
                    groups.setdefault(w, []).append(e)
            items = list(groups.items())
            if not keep_old:
                txt, grp = items.pop(0)
                strings[idx][0], strings[idx][1] = txt, None
                if strings[idx][2] is not None:
                    strings[idx][2] = len(grp)
            elif strings[idx][2] is not None:
                strings[idx][2] = len(keep_old)
            for txt, grp in items:
                strings.append([txt, None, len(grp) if self.version >= 2 else None])
                for e in grp:
                    new_idx[e['pos']] = len(strings) - 1
        head = bytearray(self.data[:self.body_end])
        for pos, idx in new_idx.items():
            struct.pack_into('<i', head, pos, idx)
        body = bytearray(struct.pack('<i', len(strings)))
        for s, enc, rc in strings:
            body += w_fstring(s, enc)
            if self.version >= 2:
                body += struct.pack('<i', rc if rc is not None else 1)
        if self.array_offset == -1:
            raise SystemExit('this locres has no string array (offset -1); nothing to rewrite')
        if self.array_offset < self.body_end:
            raise SystemExit('unexpected layout: string array before the entries')
        out = head + self.data[self.body_end:self.array_offset] + body + self.data[self.array_end:]
        return bytes(out)


def load(path):
    with open(path, 'rb') as f:
        return Locres(f.read())


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Unreal .locres info / export / import.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('info')
    s.add_argument('locres')
    s = sub.add_parser('roundtrip')
    s.add_argument('locres')
    s = sub.add_parser('export')
    s.add_argument('locres')
    s.add_argument('-o', '--output')
    s = sub.add_parser('import')
    s.add_argument('locres')
    s.add_argument('csv')
    s.add_argument('-o', '--output', required=True)
    s.add_argument('--target-col', default='target')
    a = ap.parse_args()
    L = load(a.locres)
    if a.cmd == 'info':
        nss = {e['ns'] for e in L.entries}
        u16 = sum(1 for s_ in L.strings if s_[1] == 'utf16') if L.version else sum(1 for e in L.entries if e['enc'] == 'utf16')
        print('version %d (%s) | namespaces %d | keys %d | unique strings %d | UTF-16 strings %d'
              % (L.version, VERSIONS[L.version], len(nss), len(L.entries),
                 len(L.strings) if L.version else len(L.entries), u16))
        for e in L.entries[:5]:
            print('  [%s] %s = %r' % (e['ns'], e['key'], L.text_of(e)[:60]))
        return 0
    if a.cmd == 'roundtrip':
        ok = L.build() == L.data
        print('roundtrip: %s' % ('byte-identical' if ok else 'DIFFERENT - do not trust import on this file'))
        return 0 if ok else 1
    if a.cmd == 'export':
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator='\n')
        w.writerow(['namespace', 'key', 'source', 'target'])
        for e in L.entries:
            w.writerow([e['ns'], e['key'], L.text_of(e), ''])
        out = buf.getvalue()
        if a.output:
            os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
            with open(a.output, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(out)
            print('exported %d keys -> %s' % (len(L.entries), a.output))
        else:
            sys.stdout.write(out)
        return 0
    with open(a.csv, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    known = {(e['ns'], e['key']) for e in L.entries}
    new = {}
    unknown = 0
    for r in rows:
        t = r.get(a.target_col, '')
        if not t:
            continue
        k = (r['namespace'], r['key'])
        if k not in known:
            unknown += 1
            continue
        new[k] = t
    out = L.build(new)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, 'wb') as f:
        f.write(out)
    check = Locres(out)
    bad = sum(1 for e in check.entries if (e['ns'], e['key']) in new and check.text_of(e) != new[(e['ns'], e['key'])])
    same = sum(1 for e1, e2 in zip(L.entries, check.entries)
               if (e1['ns'], e1['key']) not in new and L.text_of(e1) != check.text_of(e2))
    print('translated %d keys, %d CSV rows with unknown keys, verify: %d wrong, %d untouched keys changed -> %s'
          % (len(new), unknown, bad, same, a.output))
    return 1 if bad or same else 0


if __name__ == '__main__':
    sys.exit(main())
