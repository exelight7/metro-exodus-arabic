"""Synthetic fixtures plus optional read-only checks on user-supplied real files."""
import collections,csv,importlib.util,json,os,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
import lz4.block
import foura_dialogue as f

def make_lng(texts=None, chars=None, encoded=None):
    texts=texts or {'menu':'Hello <button>','voices\\intro':'Go!<time=125> Wait.'}
    chars=chars or '\0'+''.join(sorted(set(''.join(texts.values()))-{'\0'}))
    lookup={c:i for i,c in enumerate(chars)}
    def enc(text):
        out=bytearray()
        for c in text:
            n=lookup[c]
            out.extend([n] if n<224 else [224+(n-224)//255,(n-224)%255+1])
        return bytes(out)
    body=encoded if encoded is not None else b''.join(k.encode()+b'\0'+enc(v)+b'\0' for k,v in texts.items())
    chunks=[(91,b'unknown-before'),(1,chars.encode('utf-16le')),(77,b'\x99keep'),(2,body),(99,b'unknown-after')]
    return b''.join(struct.pack('<II',tag,len(raw))+raw for tag,raw in chunks)

def fixture(root, version=3, legacy=False, compressed=True, file_name='stable_us.lng', external=False):
    root.mkdir(parents=True,exist_ok=True)
    data=make_lng({'menu':'Hello <button>','voices\\intro':'Go!<time=125> Wait.'+' abc'*4000})
    block=data
    if compressed:
        block=b'';window=b''
        for p in range(0,len(data),4096):
            part=data[p:p+4096];c=lz4.block.compress(part,store_size=False,dict=window)
            block+=struct.pack('<II',len(c)+8,len(part))+c;window=(window+part)[-65536:]
    other=b'unrelated metadata';(root/'test.vfs0').write_bytes(block+other)
    guid=next(iter(sorted(f.LAST_LIGHT_GUIDS))) if legacy else b'F'*16
    prefix=struct.pack('<II',version,1)+(b'unit-test\0' if version==3 else b'')+guid+struct.pack('<III',1,4,0)
    prefix+=b'test.vfs0\0'+(struct.pack('<I',len(block)+len(other)) if legacy else struct.pack('<II',0,2))
    def name(s):
        b=s.encode();return bytes((len(b)+1,0xA9))+bytes(x^0xA9 for x in b)+b'\0'
    flag=16 if legacy else 8
    records=[struct.pack('<HHI',flag,1,1)+name('content'),struct.pack('<HHI',flag,2,2)+name('localization'),
             struct.pack('<HHIII',0,5 if external else 0,0,len(data),len(block))+name(file_name),
             struct.pack('<HHIII',0,0,len(block),len(other),len(other))+name('other.txt')]
    path=root/'test.vfx';path.write_bytes(prefix+b''.join(records)+b'\0'*8)
    return path,data

class CodecTests(unittest.TestCase):
    def test_noedit_byte_identical_and_unknown_chunks(self):
        raw=make_lng();lng=f.LNG(raw);self.assertEqual(lng.rebuild({}),raw)
        changed=lng.rebuild({'menu':'مرحبا <button>'})
        self.assertEqual(f.LNG(changed).texts['menu'],'مرحبا <button>')
        self.assertEqual([(t,b) for t,b in f.chunks(raw) if t not in (1,2)],[(t,b) for t,b in f.chunks(changed) if t not in (1,2)])
    def test_index_encoding_boundaries(self):
        chars=''.join(chr(i) for i in range(f.MAX_CHARS))
        codes=bytes([223,224,1,224,255,225,1,255,255])
        raw=make_lng(chars=chars,encoded=b'key\0'+codes+b'\0')
        self.assertEqual([ord(c) for c in f.LNG(raw).texts['key']],[223,224,478,479,8383])
    def test_missing_unknown_key_refused(self):
        with self.assertRaises(f.FormatError):f.LNG(make_lng()).rebuild({'no-such-key':'x'})
    def test_malformed_chunks_and_lead_byte(self):
        for raw in [b'\x01',struct.pack('<II',1,100),make_lng(encoded=b'k\0\xe0\0'),make_lng(encoded=b'k\0\xff\xff\0')]:
            with self.subTest(size=len(raw)):
                with self.assertRaises(f.FormatError):f.LNG(raw)
    def test_duplicate_chunk_or_id_refused(self):
        raw=make_lng()
        for bad in [raw+struct.pack('<II',1,2)+b'\0\0',make_lng(encoded=b'k\0\0k\0\0')]:
            with self.assertRaises(f.FormatError):f.LNG(bad)
    def test_nonbmp_and_null_refused(self):
        for text in ['bad\0value','emoji \U0001f642']:
            with self.assertRaises(f.FormatError):f.LNG(make_lng()).rebuild({'menu':text})
    def test_unchanged_ambiguous_codes_preserved(self):
        raw=make_lng(chars='\0aa',encoded=b'k\0\x02\0j\0\x01\0')
        self.assertEqual(f.LNG(raw).rebuild({'k':'a'}),raw)
        updated=f.LNG(raw).rebuild({'j':'ب'})
        self.assertIn(b'k\0\x02\0',dict(f.chunks(updated))[2])
    def test_csv_roundtrip_and_protected_timing(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);source=p/'original.lng';source.write_bytes(make_lng());table=p/'text.csv'
            f.export_lng(source,table);f.import_lng(source,table,p/'roundtrip.lng')
            self.assertEqual(source.read_bytes(),(p/'roundtrip.lng').read_bytes())
            with table.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
            rows[0]['target']='مرحبا <button>';rows[1]['target']='هيا!<time=125> انتظر.'
            with table.open('w',encoding='utf-8-sig',newline='') as out:
                w=csv.DictWriter(out,fieldnames=['id','source','target']);w.writeheader();w.writerows(rows)
            f.import_lng(source,table,p/'arabic.lng');self.assertEqual(f.LNG((p/'arabic.lng').read_bytes()).texts[rows[0]['id']],rows[0]['target'])
            rows[1]['target']='هيا!<time=126> انتظر.'
            with table.open('w',encoding='utf-8-sig',newline='') as out:
                w=csv.DictWriter(out,fieldnames=['id','source','target']);w.writeheader();w.writerows(rows)
            with self.assertRaises(f.FormatError):f.import_lng(source,table,p/'bad.lng')
            self.assertFalse((p/'bad.lng').exists())
    def test_partial_dialogue_csv_keeps_others(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);source=p/'a.lng';source.write_bytes(make_lng());table=p/'d.csv'
            f.export_lng(source,table,True)
            with table.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
            self.assertEqual([r['id'] for r in rows],['voices\\intro'])
            f.import_lng(source,table,p/'b.lng');self.assertEqual(source.read_bytes(),(p/'b.lng').read_bytes())
    def test_stale_csv_duplicate_and_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);s=p/'a.lng';s.write_bytes(make_lng());table=p/'x.csv'
            table.write_text('id,source,target\nmenu,WRONG,text\n')
            with self.assertRaises(f.FormatError):f.import_lng(s,table,p/'bad.lng')
            table.write_text('id,target,target\nmenu,text,text\n')
            with self.assertRaises(f.FormatError):f.import_lng(s,table,p/'bad.lng')
            with self.assertRaises(f.FormatError):f.export_lng(s,s)
            self.assertEqual(f.LNG(s.read_bytes()).texts['menu'],'Hello <button>')

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='foura-test-');self.root=Path(self.temp.name).resolve();self.addCleanup(self.temp.cleanup)
    def test_vfx_profiles_1_2_3_and_multiblock_lz4(self):
        for version in (1,2,3):
            p,expected=fixture(self.root/str(version),version=version)
            a=f.Archive(p);self.assertEqual(a.version,version);self.assertEqual(a.read(a.matching()[0]),expected)
    def test_extract_outside_source_only(self):
        p,data=fixture(self.root/'game');a=f.Archive(p);before=p.read_bytes()
        with self.assertRaises(f.FormatError):f.extract_archive(a,a.root/'out')
        result=f.extract_archive(a,self.root/'extracted')
        self.assertEqual(result['extracted'],1);self.assertEqual((self.root/'extracted/content/localization/stable_us.lng').read_bytes(),data)
        self.assertEqual(p.read_bytes(),before)
    def test_repack_payload_and_unrelated_records(self):
        p,original=fixture(self.root/'game');a=f.Archive(p);changes=self.root/'replacement/content/localization';changes.mkdir(parents=True)
        updated=f.LNG(original).rebuild({'menu':'مرحبا <button>'});(changes/'stable_us.lng').write_bytes(updated)
        report=f.pack_archive(a,self.root/'replacement',self.root/'patch')
        result=f.Archive(self.root/'patch/test.vfx');self.assertEqual(result.read(result.matching()[0]),updated)
        self.assertEqual(a.entries[3].raw,result.entries[3].raw);self.assertTrue(report['unrelated_records_preserved'])
        self.assertEqual(a.read(a.matching()[0]),original)
    def test_repack_v1_v2(self):
        for version in (1,2):
            p,data=fixture(self.root/('game'+str(version)),version=version);a=f.Archive(p)
            change=self.root/('replacement'+str(version))/'content/localization';change.mkdir(parents=True)
            (change/'stable_us.lng').write_bytes(data)
            dest=self.root/('patch'+str(version));f.pack_archive(a,change.parents[1],dest)
            b=f.Archive(dest/'test.vfx');self.assertEqual(b.read(b.matching()[0]),data)
    def test_unknown_version_compression_and_tree(self):
        p,data=fixture(self.root/'game');raw=p.read_bytes()
        for header in [(4,1),(3,2)]:
            p.write_bytes(struct.pack('<II',*header)+raw[8:])
            with self.assertRaises(f.FormatError):f.Archive(p)
            self.assertFalse(f.probe(p)['supported'])
    def test_traversal_and_device_paths(self):
        for name in ['../escape.lng','/abs.lng','C:\\x.lng','a/../../b','a:stream','CON.txt','a/NUL','a/b.','a//c']:
            with self.subTest(name=name):
                with self.assertRaises(f.FormatError):f.relative_name(name)
    def test_inherited_reference_lists_but_not_resolves(self):
        p,data=fixture(self.root/'game',external=True);a=f.Archive(p)
        self.assertEqual(a.summary()['inherited_package_references'],1)
        with self.assertRaises(f.FormatError):a.read(a.matching()[0])
    def test_legacy_recognized_compressed_refused(self):
        p,data=fixture(self.root/'game',version=1,legacy=True);a=f.Archive(p)
        self.assertTrue(a.legacy)
        with self.assertRaisesRegex(f.FormatError,'QuickLZ'):a.read(a.matching()[0])
    def test_legacy_uncompressed_readable(self):
        p,data=fixture(self.root/'game',version=1,legacy=True,compressed=False);a=f.Archive(p)
        self.assertEqual(a.read(a.matching()[0]),data)
    def test_unknown_replacement_and_existing_output(self):
        p,data=fixture(self.root/'game');a=f.Archive(p);folder=self.root/'replacement';folder.mkdir();(folder/'unknown.txt').write_bytes(b'abc')
        with self.assertRaises(f.FormatError):f.pack_archive(a,folder,self.root/'out')
        self.assertFalse((self.root/'out').exists())
        with self.assertRaises(f.FormatError):f.extract_archive(a,a.root)
    def test_truncated_stream_and_bounded_extract(self):
        p,data=fixture(self.root/'game');a=f.Archive(p)
        with self.assertRaises(f.FormatError):a.read(a.matching()[0],limit=10)
        (a.root/'test.vfs0').write_bytes(b'x')
        with self.assertRaises(f.FormatError):f.extract_archive(a,self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_cli_end_to_end(self):
        p,data=fixture(self.root/'game');cli=Path(f.__file__)
        result=subprocess.run([sys.executable,str(cli),'extract',str(p),'--out',str(self.root/'dump')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        source=self.root/'dump/content/localization/stable_us.lng'
        result=subprocess.run([sys.executable,str(cli),'export-lng',str(source),'--out',str(self.root/'rows.csv')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        result=subprocess.run([sys.executable,str(cli),'import-lng',str(source),'--table',str(self.root/'rows.csv'),'--out',str(self.root/'rebuild.lng')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual((self.root/'rebuild.lng').read_bytes(),data)

if __name__=='__main__':unittest.main(verbosity=2)
