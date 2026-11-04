"""Inspect fonts_us.bin reflection sections (MetroTools format reference)."""
import struct,json
from pathlib import Path
from metro_archive import Reader

def section(r):
    crc,n=r.get('II'); start=r.p; flags=r.get('B'); data=r.b[r.p:start+n]; r.p=start+n
    assert flags==4
    return crc,data

def read_fonts(b):
    assert b[0]==4
    r=Reader(b);r.p=1;assert r.get('I')==1;n=r.get('I');data=r.b[r.p:r.p+n];r.p+=n
    assert r.get('I')==2;n=r.get('I');sc=r.get('I');strings=r.b[r.p:r.p+n-4].split(b'\0')[:-1]
    assert len(strings)==sc
    strings=[s.decode() for s in strings]
    r=Reader(data);crc,data=section(r);r=Reader(data);num=r.get('I'); fonts=[]
    for i in range(num):
        crc,body=section(r);s=Reader(body)
        lang,name,texture=s.get('III');invx,invy,line=s.get('fff')
        tc,arr=section(s); assert s.p==len(body)
        a=Reader(arr);count=a.get('I');glyphs=[]
        for j in range(count):
            gc,gb=section(a);assert len(gb)==14
            glyphs.append(list(struct.unpack('<7H',gb)))
        assert a.p==len(arr)
        fonts.append(dict(name=strings[name],lang=strings[lang],texture=strings[texture],inv=[invx,invy],line=line,glyphs=glyphs))
    assert r.p==len(data)
    return fonts

def write_fonts(fonts):
    import zlib
    strings=[]
    def ref(s):
        if s not in strings:strings.append(s)
        return strings.index(s)
    def sec(name,body):
        return struct.pack('<II',zlib.crc32(name.encode()),len(body)+1)+b'\x04'+body
    records=[]
    for f in fonts:
        arr=struct.pack('<I',len(f['glyphs']))+b''.join(sec('rec_%04d'%i,struct.pack('<7H',*g)) for i,g in enumerate(f['glyphs']))
        body=struct.pack('<III3f',ref(f['lang']),ref(f['name']),ref(f['texture']),*f['inv'],f['line'])+sec('tcmap',arr)
        records.append(sec('rec_%04d'%len(records),body))
    data=sec('descriptions',struct.pack('<I',len(fonts))+b''.join(records))
    table=struct.pack('<I',len(strings))+b''.join(s.encode()+b'\0' for s in strings)
    return b'\x04'+struct.pack('<II',1,len(data))+data+struct.pack('<II',2,len(table))+table

if __name__=='__main__':
    fonts=read_fonts(Path('02_extracted/steam_local/patch_04/content/scripts/fonts_us.bin').read_bytes())
    for f in fonts:print(f['name'],f['texture'],len(f['glyphs']),f['inv'],f['line'])
    Path('02_extracted/steam_local/fonts.json').write_text(json.dumps(fonts,indent=1))
