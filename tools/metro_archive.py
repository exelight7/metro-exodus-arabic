"""Metro Exodus archive reader. Format reference: ShokerStlk/MetroEX (MIT)."""
import struct,json
from pathlib import Path
import lz4.block
class Reader:
 def __init__(self,b): self.b=b; self.p=0
 def get(self,fmt):
  v=struct.unpack_from('<'+fmt,self.b,self.p); self.p+=struct.calcsize('<'+fmt); return v[0] if len(v)==1 else v
 def z(self):
  e=self.b.index(b'\0',self.p); v=self.b[self.p:e]; self.p=e+1; return v.decode('utf-8')
 def name(self):
  n,k=self.get('BB'); v=bytes(x^k for x in self.b[self.p:self.p+n-1]); self.p+=n; return v.decode('utf-8')
def index(path):
 b=Path(path).read_bytes(); r=Reader(b)
 assert r.get('II')==(3,1)
 ver=r.z(); r.p+=16; np,nf,unk=r.get('III'); packs=[]
 for _ in range(np):
  name=r.z(); levels=[r.z() for i in range(r.get('I'))]; chunk=r.get('I'); packs.append(name)
 entries=[]
 for i in range(nf):
  start=r.p; flags=r.get('H'); d=dict(id=i,flags=flags,record_offset=start)
  if flags&8: d.update(zip(('count','first'),r.get('HI')))
  else: d.update(zip(('pak','offset','usize','csize'),r.get('HIII')))
  d['name']=r.name(); entries.append(d)
 assert len(b)-r.p in (0,8),(r.p,len(b))
 def walk(i,parent):
  e=entries[i]; e['path']=parent+'/'+e['name'] if parent else e['name']
  if e['flags']&8:
   for c in range(e['first'],e['first']+e['count']): walk(c,e['path'])
 walk(0,'')
 return dict(version=ver,packs=packs,entries=entries)
def extract(game,idx,e):
 with (Path(game)/idx['packs'][e['pak']]).open('rb') as f: f.seek(e['offset']); b=f.read(e['csize'])
 if e['csize']==e['usize']: return b
 r=Reader(b); out=b''
 while r.p<len(b):
  n,u=r.get('II'); block=b[r.p:r.p+n-8]; r.p+=n-8
  out+=lz4.block.decompress(block,uncompressed_size=u,dict=out[-65536:])
 assert len(out)==e['usize']; return out
if __name__=='__main__':
 game=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
 dest=Path('02_extracted/steam_local'); dest.mkdir(parents=True,exist_ok=True)
 for vf in sorted(game.glob('*.vfx')):
  idx=index(vf); (dest/(vf.stem+'_index.json')).write_text(json.dumps(idx,indent=1),encoding='utf-8')
  for e in idx['entries']:
   if not e['flags']&8 and ('localization' in e['path'].lower() or e['name'].endswith(('.lng','.ttf','.otf','.fnt'))):
    print(vf.name,e['path'],e['usize'])
    out=dest/vf.stem/e['path']; out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(extract(game,idx,e))
