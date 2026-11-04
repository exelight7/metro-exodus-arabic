#!/usr/bin/env python3
"""4A Engine text workbench: VFX names/LZ4 and lossless chunked LNG.

Independent Python implementation; format references: MetroEX and MetroTools.
Never executes a game or installs a generated patch. Python 3.10+, optional lz4.
"""
from __future__ import annotations
import argparse, collections, csv, fnmatch, hashlib, json, os, re, struct, sys, tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

VERSION = '0.2.0'
MAX_TEXT = 128 * 1024 * 1024
MAX_CHARS = 8384
LAST_LIGHT_GUIDS = {
    struct.pack('<IHHH6B', *v) for v in [
        (0xE4727F4A,0xF56A,0x4998,0x2E84,0xFC,0xD2,0x75,0x22,0xEB,0x3D),
        (0xB03B72E1,0x7659,0x4D74,0x618C,0xBF,0x1F,0xBD,0x55,0x22,0x1B),
        (0x3541E232,0x1A41,0x4B20,0xAC94,0x86,0x43,0x31,0xC2,0x4C,0x41),
        (0x96B68062,0x41B8,0x41EE,0xEAB2,0x90,0xED,0xF0,0x78,0xF2,0x22),
        (0x292A1047,0x06A4,0x4423,0xE980,0xB3,0xEA,0x49,0x32,0xB0,0x31),
        (0xA328D21D,0x8D8C,0x477D,0x4AA8,0xFD,0xDA,0x86,0x59,0xEF,0x62),
    ]
}
PROTECTED = re.compile(r'<(?!br\s*>)[^>]+>|\{[^}]+\}|%(?:\d+\$)?[-+# 0]*\d*(?:\.\d+)?[sdifuoxX]|\\[nrt]')

class FormatError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise FormatError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_small(path, limit=MAX_TEXT):
    path = Path(path)
    need(path.stat().st_size <= limit, f'Input exceeds {limit} byte limit: {path.name}')
    return path.read_bytes()

def relative_name(name):
    """Normalize an archive path and reject platform aliases/traversal/ADS."""
    name = name.replace('\\', '/')
    parts = name.split('/')
    need(bool(name) and not name.startswith('/') and ':' not in name and '\0' not in name,
         f'Unsafe archive path: {name!r}')
    for part in parts:
        need(part not in ('', '.', '..') and part == part.rstrip(' .'), f'Unsafe path component: {part!r}')
        need(not re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', part.split('.')[0], re.I),
             f'Reserved device path: {part!r}')
    return '/'.join(parts)

def inside(root, name):
    name = relative_name(name)
    result = Path(root).joinpath(*PurePosixPath(name).parts)
    need(result.resolve().is_relative_to(Path(root).resolve()), 'Path escapes output/source root')
    current = result
    while current != Path(root):
        need(not current.is_symlink(), 'Symbolic links are not accepted for archive paths')
        current = current.parent
    return result

def new_file(path, data):
    path = Path(path)
    need(not path.is_symlink() and not path.exists(), f'Output already exists: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids replacing an existing output or source.
    with path.open('xb') as f:
        f.write(data)

class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0
    def read(self, count):
        need(0 <= count <= len(self.data) - self.pos, 'Truncated input')
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result
    def number(self, fmt):
        result = struct.unpack('<' + fmt, self.read(struct.calcsize('<' + fmt)))
        return result[0] if len(result) == 1 else result
    def string(self):
        end = self.data.find(b'\0', self.pos, min(len(self.data), self.pos + 65536))
        need(end >= 0, 'Missing or oversized null-terminated string')
        data = self.read(end - self.pos + 1)[:-1]
        return data.decode('utf-8')
    def xored(self):
        count, mask = self.number('BB')
        need(count >= 1, 'Invalid XOR name length')
        data = self.read(count)
        need(data[-1] == 0, 'Missing XOR name terminator')
        return bytes(c ^ mask for c in data[:-1]).decode('utf-8')

@dataclass
class Entry:
    id: int
    flags: int
    raw: bytes
    name: str
    path: str = ''
    pak: int = -1
    offset: int = 0
    usize: int = 0
    csize: int = 0
    first: int = 0
    count: int = 0
    @property
    def folder(self):
        return bool(self.flags & 8)

class Archive:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.root = self.path.parent
        self.raw = load_small(self.path)
        r = Reader(self.raw)
        self.version, compression = r.number('II')
        need(self.version in (1, 2, 3), 'Unsupported VFX version (expected 1, 2 or 3)')
        need(compression == 1, 'Unsupported VFX compression field')
        self.content_version = r.string() if self.version == 3 else ''
        self.guid = r.read(16)
        self.legacy = self.guid in LAST_LIGHT_GUIDS
        self.count_offset = r.pos
        np, nf, self.duplicates = r.number('III')
        need(0 < np <= 65535 and 0 < nf <= 1_000_000, 'Invalid VFX package/file count')
        self.packages = []
        for _ in range(np):
            name = r.string()
            relative_name(name)
            if self.legacy:
                meta = {'size': r.number('I')}
            else:
                count = r.number('I')
                need(count <= 65535, 'Invalid VFX level count')
                meta = {'levels': [r.string() for _ in range(count)], 'chunk': r.number('I')}
            self.packages.append({'name': name, **meta})
        self.prefix = self.raw[:r.pos]
        self.entries = []
        for i in range(nf):
            start = r.pos
            flags = r.number('H')
            logical_flags = flags >> 1 if self.legacy else flags
            e = Entry(i, logical_flags, b'', '')
            if e.folder:
                e.count, e.first = r.number('HI')
                need(e.first + e.count <= nf, 'Folder references entries outside index')
            else:
                e.pak, e.offset, e.usize, e.csize = r.number('HIII')
                # Patch indexes may retain inherited/global package references.
                # Preserve them verbatim; resolve only a selected local file.
            e.name = r.xored()
            e.raw = self.raw[start:r.pos]
            self.entries.append(e)
        self.tail = self.raw[r.pos:]
        # A folder graph must be a tree, not a cycle or repeated reference.
        visited, stack = set(), [(0, '', 0)]
        while stack:
            i, parent, depth = stack.pop()
            need(i not in visited and depth <= 256, 'Cyclic or excessively deep VFX folder graph')
            visited.add(i)
            e = self.entries[i]
            e.path = (parent + '/' + e.name if parent and e.name else parent or e.name).replace('\\', '/')
            if e.path:
                relative_name(e.path)
            if e.folder:
                stack.extend((j, e.path, depth + 1) for j in reversed(range(e.first, e.first + e.count)))
        need(len(visited) == nf, 'Unreachable entries in VFX index; unsupported tree layout')
    def matching(self, pattern='*.lng'):
        return [e for e in self.entries if not e.folder and fnmatch.fnmatchcase(e.path.lower(), pattern.lower())]
    def read(self, entry, limit=MAX_TEXT):
        need(not entry.folder, 'Cannot extract a folder as a file')
        need(0 <= entry.pak < len(self.packages), 'Selected file uses an inherited/global package reference; mount resolution is not implemented')
        need(entry.usize <= limit and entry.csize <= limit, 'Selected file exceeds extraction limit')
        path = inside(self.root, self.packages[entry.pak]['name'])
        need(path.stat().st_size >= entry.offset + entry.csize, 'VFS file is missing/truncated')
        with path.open('rb') as f:
            f.seek(entry.offset)
            raw = f.read(entry.csize)
        if entry.csize == entry.usize:
            return raw
        need(not self.legacy, 'Last Light QuickLZ stream is recognized but not implemented; no output written')
        try:
            import lz4.block
        except ImportError:
            raise FormatError('Install lz4: python -m pip install -r requirements.txt') from None
        reader, output, window = Reader(raw), bytearray(), b''
        while reader.pos < len(raw):
            count, size = reader.number('II')
            need(count >= 8 and 0 < size <= entry.usize - len(output), 'Invalid LZ4 block lengths')
            block = reader.read(count - 8)
            try:
                decoded = lz4.block.decompress(block, uncompressed_size=size, dict=window)
            except lz4.block.LZ4BlockError:
                raise FormatError('Invalid LZ4 compressed block') from None
            need(len(decoded) == size, 'LZ4 output length mismatch')
            output.extend(decoded)
            window = (window + decoded)[-65536:]
        need(len(output) == entry.usize, 'VFS uncompressed size mismatch')
        return bytes(output)
    def summary(self):
        return {'kind': 'VFX', 'version': self.version, 'content_version': self.content_version,
                'profile': 'last-light-quicklz' if self.legacy else {1:'redux-v1',2:'arktika-v2',3:'exodus-v3'}[self.version],
                'packages': [p['name'] for p in self.packages], 'entries': len(self.entries),
                'duplicates': self.duplicates, 'localization_files': [e.path for e in self.matching()],
                'inherited_package_references':sum(not e.folder and e.pak >= len(self.packages) for e in self.entries),
                'legacy_compressed_extraction': False if self.legacy else None}

def chunks(raw):
    r, result = Reader(raw), []
    while r.pos < len(raw):
        tag, size = r.number('II')
        result.append((tag, r.read(size)))
    return result

class LNG:
    def __init__(self, raw):
        need(len(raw) <= MAX_TEXT, 'LNG exceeds size limit')
        self.raw, self.chunks = raw, chunks(raw)
        tables = {t: [b for k,b in self.chunks if k == t] for t in (1,2)}
        need(all(len(v) == 1 for v in tables.values()), 'Expected one character table and one string table')
        need([t for t,b in self.chunks].index(1) < [t for t,b in self.chunks].index(2), 'LNG characters must precede strings')
        self.chars = tables[1][0].decode('utf-16le')
        need(0 < len(self.chars) <= MAX_CHARS and self.chars[0] == '\0', 'Unsupported LNG character table')
        need(not any(ord(c) > 0xFFFF for c in self.chars), 'Non-BMP character tables are not supported')
        parts = tables[2][0].split(b'\0')
        need(parts[-1] == b'' and len(parts) % 2 == 1, 'Invalid LNG string-pair table')
        self.records, self.texts = [], {}
        for i in range(0, len(parts) - 1, 2):
            key, value = parts[i].decode('utf-8'), self.decode(parts[i+1])
            need(key not in self.texts, f'Duplicate LNG key: {key}')
            self.texts[key] = value
            self.records.append((key, parts[i], parts[i+1]))
    def decode(self, raw):
        result, p = [], 0
        while p < len(raw):
            n = raw[p]; p += 1
            if n >= 224:
                need(p < len(raw) and raw[p] != 0, 'Truncated LNG two-byte character code')
                n = n * 255 + raw[p] - 0xDE41; p += 1
            need(n < len(self.chars), 'LNG character index outside table')
            result.append(self.chars[n])
        return ''.join(result)
    def rebuild(self, updates):
        need(set(updates) <= set(self.texts), 'Translation table contains keys absent from original LNG')
        changed = {k:v for k,v in updates.items() if v != self.texts[k]}
        if not changed:
            return self.raw
        need(not any('\0' in v or any(ord(c) > 0xFFFF for c in v) for v in changed.values()),
             'Embedded nulls and non-BMP target characters are not supported')
        chars = self.chars + ''.join(sorted(set(''.join(changed.values())) - set(self.chars)))
        need(len(chars) <= MAX_CHARS, 'LNG two-byte character table capacity exceeded')
        lookup = {}
        for i,c in enumerate(chars):lookup.setdefault(c,i)
        def encode(text):
            output = bytearray()
            for c in text:
                n = lookup[c]
                need(n != 0, 'Embedded null character')
                if n < 224:output.append(n)
                else:output.extend((224 + (n - 224)//255, (n - 224)%255 + 1))
            return bytes(output)
        body = b''.join(kbytes + b'\0' + (encode(changed[k]) if k in changed else encoded) + b'\0'
                        for k,kbytes,encoded in self.records)
        result = b''.join(struct.pack('<II',t,len(b)) + b for t,b in
                          [(t,chars.encode('utf-16le') if t == 1 else body if t == 2 else b) for t,b in self.chunks])
        parsed = LNG(result)
        need(list(parsed.texts) == list(self.texts), 'LNG record order changed')
        need(parsed.texts == {k:updates.get(k,v) for k,v in self.texts.items()}, 'LNG rebuild validation failed')
        return result

def extract_archive(archive, output, pattern='*.lng', limit=MAX_TEXT):
    output = Path(output).resolve()
    need(not output.is_relative_to(archive.root), 'Extraction output must be outside the source/game folder')
    need(not output.exists(), 'Extraction output directory already exists')
    selected = archive.matching(pattern)
    need(selected, 'No matching files')
    seen, results = set(), []
    for e in selected:
        key = relative_name(e.path).casefold()
        need(key not in seen, 'Archive paths collide on case-insensitive filesystems')
        seen.add(key)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage every file before publishing a new output directory.
    with tempfile.TemporaryDirectory(prefix='.foura-extract-', dir=output.parent) as temp:
        stage = Path(temp)
        for e in selected:
            data = archive.read(e, limit)
            new_file(inside(stage,e.path), data)
            results.append({'id':e.id,'path':e.path,'bytes':len(data),'sha256':sha(data)})
        new_file(stage/'foura-manifest.json', json.dumps({'index_sha256':sha(archive.raw),'files':results},indent=2).encode())
        need(not output.exists(), 'Output appeared during extraction')
        os.rename(stage, output)
    return {'extracted':len(results),'output':str(output),'files':results}

def pack_archive(archive, replacements, output, pak_name='foura_localization.vfs0'):
    """New index+raw supplemental VFS; no installation or source modification."""
    replacements, output = Path(replacements).resolve(), Path(output).resolve()
    need(not archive.legacy and archive.duplicates == 0 and len(archive.tail) in (0,8),
         'Repacking needs a non-legacy VFX with zero duplicates and a known trailer')
    need(not output.is_relative_to(archive.root), 'Patch output must be outside the source/game folder')
    need(not output.exists(), 'Patch output directory already exists')
    need(replacements.is_dir() and replacements != archive.root and not replacements.is_relative_to(archive.root),
         'Use a separate replacement directory outside the game folder')
    need(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.vfs0',pak_name) is not None, 'Invalid supplemental VFS name')
    need(pak_name.casefold() not in {p['name'].casefold() for p in archive.packages}, 'VFS name already used by source index')
    need(len(archive.packages) < 65535, 'VFX package limit reached')
    indexed = {}
    for e in archive.entries:
        if not e.folder:
            key = relative_name(e.path).casefold()
            need(key not in indexed, 'VFX paths collide; cannot repack safely')
            indexed[key] = e
    changes = {}
    for p in replacements.rglob('*'):
        need(not p.is_symlink(), 'Replacement tree contains a symbolic link')
        if not p.is_file():continue
        rel = relative_name(p.relative_to(replacements).as_posix())
        e = indexed.get(rel.casefold())
        need(e is not None, f'Replacement path absent from VFX: {rel}')
        need(e.id not in changes, 'Duplicate replacement path')
        data = load_small(p)
        if p.suffix.lower() == '.lng':LNG(data)
        changes[e.id] = data
    need(changes, 'No replacement files supplied')
    blob, fields = bytearray(), {}
    for e in archive.entries:
        if e.id in changes:
            data = changes[e.id]
            need(len(blob) + len(data) <= 0xFFFFFFFF, 'Supplemental VFS exceeds 32-bit offsets')
            fields[e.id] = (len(archive.packages),len(blob),len(data),len(data));blob.extend(data)
    prefix = bytearray(archive.prefix)
    struct.pack_into('<I',prefix,archive.count_offset,len(archive.packages)+1)
    prefix.extend(pak_name.encode() + b'\0' + struct.pack('<II',0,2))
    records = []
    for e in archive.entries:
        record = bytearray(e.raw)
        if e.id in fields:struct.pack_into('<HIII',record,2,*fields[e.id])
        records.append(record)
    index_data = bytes(prefix) + b''.join(records) + archive.tail
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.foura-pack-', dir=output.parent) as temp:
        stage = Path(temp)
        new_file(stage/pak_name,bytes(blob));new_file(stage/archive.path.name,index_data)
        rebuilt = Archive(stage/archive.path.name)
        for old, new in zip(archive.entries,rebuilt.entries):
            need(old.path == new.path and old.flags == new.flags, 'Repack changed names/tree')
            if old.id in changes:need(rebuilt.read(new) == changes[old.id], 'Repacked payload mismatch')
            else:need(old.raw == new.raw, 'Repack changed an unrelated VFX record')
        report = {'source_index_sha256':sha(archive.raw),'version':archive.version,'replaced_files':len(changes),
                  'unrelated_records_preserved':True,'files':{archive.path.name:sha(index_data),pak_name:sha(bytes(blob))},
                  'installed':False,'game_launched':False}
        new_file(stage/'patch-manifest.json',json.dumps(report,indent=2).encode())
        need(not output.exists(), 'Output appeared during repacking')
        os.rename(stage,output)
    return report

def export_lng(source, output, dialogue_only=False):
    source, output = Path(source), Path(output)
    lng = LNG(load_small(source))
    selected = [(k,v) for k,v in lng.texts.items() if not dialogue_only or k.startswith('voices\\') or '<time=' in v]
    need(not output.exists() and output.resolve() != source.resolve(), 'CSV output already exists or aliases source')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['id','source','target']);writer.writeheader()
        writer.writerows({'id':k,'source':v,'target':v} for k,v in selected)
    return {'exported':len(selected),'source_sha256':sha(lng.raw),'chars':len(lng.chars)}

def import_lng(source, table, output, allow_format_changes=False):
    source, table, output = Path(source), Path(table), Path(output)
    need(output.resolve() not in (source.resolve(),table.resolve()), 'Output aliases an input file')
    lng, updates = LNG(load_small(source)), {}
    csv.field_size_limit(MAX_TEXT)
    with table.open(encoding='utf-8-sig',newline='') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames and {'id','target'} <= set(reader.fieldnames), 'CSV needs id and target columns')
        need(len(reader.fieldnames) == len(set(reader.fieldnames)), 'Duplicate CSV column names')
        for row in reader:
            key, target = row['id'], row['target']
            need(key not in updates and key in lng.texts and target is not None, f'Invalid/duplicate CSV key: {key}')
            if 'source' in row:need(row['source'] == lng.texts[key], f'Stale/edited source column: {key}')
            if not allow_format_changes:
                need(collections.Counter(PROTECTED.findall(lng.texts[key])) == collections.Counter(PROTECTED.findall(target)),
                     f'Protected tags/variables/timing changed: {key}')
            updates[key] = target
    raw = lng.rebuild(updates)
    new_file(output,raw)
    return {'rows':len(updates),'changed':sum(v != lng.texts[k] for k,v in updates.items()),
            'original_sha256':sha(lng.raw),'output_sha256':sha(raw),'unknown_chunks_preserved':True}

def probe(path):
    path = Path(path)
    if path.is_dir():
        return {'directory':str(path),'indexes':[probe(p) for p in sorted(path.iterdir()) if p.suffix.lower() in ('.vfx','.vfi')]}
    with path.open('rb') as f:head=f.read(8)
    if path.suffix.lower() == '.vfx' or len(head) == 8 and struct.unpack('<II',head) in ((1,1),(2,1),(3,1)):
        try:return {'file':path.name,**Archive(path).summary()}
        except (FormatError,UnicodeError,struct.error) as e:return {'file':path.name,'kind':'VFX','supported':False,'reason':str(e)}
    if path.suffix.lower() in ('.vfi','.upk'):
        return {'file':path.name,'kind':path.suffix[1:].upper(),'support':'recognized-only; legacy archive extraction not implemented'}
    try:
        lng=LNG(load_small(path))
    except (FormatError,UnicodeError,struct.error):
        return {'file':path.name,'kind':'unknown','supported':False}
    return {'file':path.name,'kind':'LNG','records':len(lng.texts),'characters':len(lng.chars),'roundtrip_sha256':sha(lng.rebuild({}))}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--version',action='version',version=VERSION)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('probe',help='Identify format, without modifying inputs');p.add_argument('input',type=Path)
    p=sub.add_parser('list',help='List matching indexed paths');p.add_argument('index',type=Path);p.add_argument('--pattern',default='*.lng')
    p=sub.add_parser('extract',help='Decode XOR paths and decompress selected files');p.add_argument('index',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--pattern',default='*.lng');p.add_argument('--max-file-mib',type=int,default=128)
    p=sub.add_parser('export-lng',help='Export editable UTF-8 CSV');p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--dialogue-only',action='store_true')
    p=sub.add_parser('import-lng',help='Rebuild a separate LNG, retaining unknown chunks');p.add_argument('input',type=Path);p.add_argument('--table',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--allow-format-changes',action='store_true')
    p=sub.add_parser('verify-lng',help='Check structure and no-edit byte roundtrip');p.add_argument('input',type=Path)
    p=sub.add_parser('pack-vfx',help='Create a supplemental patch in a NEW external directory');p.add_argument('index',type=Path);p.add_argument('--from',dest='replacements',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--pak-name',default='foura_localization.vfs0')
    args=parser.parse_args(argv)
    try:
        if args.command=='probe':result=probe(args.input)
        elif args.command=='list':
            archive=Archive(args.index);result=[{'id':e.id,'path':e.path,'bytes':e.usize,'stored_bytes':e.csize} for e in archive.matching(args.pattern)]
        elif args.command=='extract':
            need(0 < args.max_file_mib <= 1024, 'Extraction limit must be 1..1024 MiB')
            result=extract_archive(Archive(args.index),args.out,args.pattern,args.max_file_mib*1024*1024)
        elif args.command=='export-lng':result=export_lng(args.input,args.out,args.dialogue_only)
        elif args.command=='import-lng':result=import_lng(args.input,args.table,args.out,args.allow_format_changes)
        elif args.command=='pack-vfx':result=pack_archive(Archive(args.index),args.replacements,args.out,args.pak_name)
        else:
            raw=load_small(args.input);lng=LNG(raw);rebuilt=lng.rebuild({})
            need(raw==rebuilt,'LNG no-edit roundtrip mismatch')
            result={'records':len(lng.texts),'chars':len(lng.chars),'roundtrip_equal':True,'sha256':sha(raw)}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (FormatError,OSError,UnicodeError,struct.error,KeyError,ValueError) as e:
        print('ERROR: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
