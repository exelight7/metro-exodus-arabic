"""Redirect selected patch_04 entries to a small supplemental VFS.
All unrelated index records and the original VFS archives remain unchanged.
"""
import struct,json,hashlib,zlib,shutil
from pathlib import Path
from metro_archive import index,extract

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
ORIG=ROOT/'01_original/steam_local/patch_04.vfx'

def sha(b):return hashlib.sha256(b).hexdigest()

def build_package(stage=None,patch=None,pakname='metro_arabic.vfs0',extra=None):
    stage=Path(stage) if stage else ROOT/'06_build/stage'
    config=(ROOT/'02_extracted/steam_local/patch_04/content/config.bin').read_bytes()
    nested={zlib.crc32(('content\\scripts\\'+p.name).encode()):p.read_bytes() for p in (stage/'content/scripts').glob('*.bin')}
    pos=0;parts=[];found=set()
    while pos<len(config):
        crc,n=struct.unpack_from('<II',config,pos);pos+=8;body=config[pos:pos+n];pos+=n
        if crc in nested:
            body=nested[crc];found.add(crc)
        parts.append(struct.pack('<II',crc,len(body))+body)
    assert found==set(nested)
    (stage/'content/config.bin').write_bytes(b''.join(parts))
    assets={str(p.relative_to(stage)).replace('\\','/'):p.read_bytes() for p in stage.rglob('*') if p.is_file() and p.parent!=stage/'content/scripts'}
    original=ORIG.read_bytes();idx=index(ORIG); np=len(idx['packs'])
    entries=idx['entries']; selected={};blob=bytearray()
    for e in entries:
        path=e['path'].replace('\\','/')
        if not e['flags']&8 and path in assets:
            data=assets.pop(path);selected[e['id']]=(np,len(blob),len(data),len(data));blob.extend(data)
    assert not assets,list(assets)
    patch=Path(patch) if patch else ROOT/'07_patch';patch.mkdir(parents=True,exist_ok=True)
    (patch/pakname).write_bytes(blob)
    prefix=bytearray(original[:entries[0]['record_offset']])
    version_end=original.index(0,8)+1;np_offset=version_end+16
    struct.pack_into('<I',prefix,np_offset,np+1)
    prefix+=pakname.encode()+b'\0'+struct.pack('<II',0,2)
    records=[]
    for i,e in enumerate(entries):
        end=entries[i+1]['record_offset'] if i+1<len(entries) else len(original)-8
        record=bytearray(original[e['record_offset']:end])
        if e['id'] in selected:struct.pack_into('<HIII',record,2,*selected[e['id']])
        records.append(record)
    new=bytes(prefix)+b''.join(records)+original[-8:]
    target=patch/'patch_04.vfx';target.write_bytes(new)
    rebuilt=index(target)
    assert len(rebuilt['entries'])==len(entries)
    for old,e in zip(entries,rebuilt['entries']):
        assert old['path']==e['path'] and old['flags']==e['flags']
        if old['id'] not in selected:
            for field in ('pak','offset','usize','csize','count','first'):assert old.get(field)==e.get(field)
        else:
            with (patch/pakname).open('rb') as f:f.seek(e['offset']);data=f.read(e['csize'])
            source=(stage/e['path'].replace('\\','/')).read_bytes();assert data==source
    manifest=dict(game_dir=str(GAME),original_index_sha256=sha(original),files={p.name:sha(p.read_bytes()) for p in [target,patch/pakname]},
        redirected_entries=len(selected),runtime_tested=False,translation_quality='machine_draft_with_reviewed_ui')
    validation=json.loads((ROOT/'08_qa/audit/localization_build.json').read_text())
    manifest['untranslated_entries']=validation['statuses'].get('todo',validation['statuses'].get('untranslated',0))
    if extra:manifest.update(extra)
    (patch/'verification.json').write_text(json.dumps(dict(unrelated_records_preserved=True,payloads_verified=len(selected),runtime_tested=False),indent=2))
    if not extra:(ROOT/'08_qa/audit/package.json').write_text(json.dumps(manifest,indent=2))
    (patch/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Verified archive records and all payload bytes:',len(selected),'assets,',len(blob),'bytes',flush=True)

if __name__=='__main__':build_package()
