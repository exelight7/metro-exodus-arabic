"""Build distributable deltas from verified local originals; never install them."""
from pathlib import Path
import hashlib,json,shutil,sys,time
import bsdiff4
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from metro_archive import index,extract
import loading_native_patch as native

def digest(b):return hashlib.sha256(b).hexdigest()

def main(revision='final_review_r1',version='0.1.0-review'):
    out=ROOT/'06_build/installer_resources';out.mkdir(exist_ok=True)
    assets=ROOT/'06_build/installer_assets';assets.mkdir(exist_ok=True)
    game=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
    final=ROOT/'07_patch/phases'/('100_'+revision)
    original=ROOT/'01_original/steam_local/patch_04.vfx'
    oi=index(original);pi=index(final/'patch_04.vfx')
    changed=[e for e in pi['entries'] if not e['flags']&8 and e['pak']==len(pi['packs'])-1]
    base=[];entries=[]
    for e in changed:
        src=oi['entries'][e['id']];raw=extract(game,oi,src);base.append(raw)
        entries.append(dict(id=src['id'],path=src['path'],archive=oi['packs'][src['pak']],offset=src['offset'],csize=src['csize'],usize=src['usize'],sha256=digest(raw)))
        print('Verified original:',src['path'],len(raw),flush=True)
    clean_index=original.read_bytes();installed_index=(final/'patch_04.vfx').read_bytes()
    payload_name=pi['packs'][-1];payload=(final/payload_name).read_bytes()
    clean_exe=native.verified_original(game/'MetroExodus.exe',ROOT);patched_exe=native.build(clean_exe)
    pairs={'index.forward.bsdiff':(clean_index,installed_index),'index.reverse.bsdiff':(installed_index,clean_index),'payload.bsdiff':(b''.join(base),payload)}
    cache=out/'build-inputs.json';inputs={n:[digest(a),digest(b)] for n,(a,b) in pairs.items()}
    previous=json.loads(cache.read_text()) if cache.exists() else {}
    hashes={}
    for name,(a,b) in pairs.items():
        dest=out/name
        if not dest.exists() or previous.get(name)!=inputs[name]:
            print('Building delta:',name,flush=True);dest.write_bytes(bsdiff4.diff(a,b))
        delta=dest.read_bytes();assert bsdiff4.patch(a,delta)==b
        hashes[name]=digest(delta);print('Verified delta:',name,len(delta),flush=True)
    cache.write_text(json.dumps(inputs,indent=2))
    profile=dict(schema=1,revision=revision,installer_version=version,game='Metro Exodus Steam Windows',platforms=['Windows x86_64','Linux x86_64 / Proton'],original_index=digest(clean_index),installed_index=digest(installed_index),original_exe=digest(clean_exe),installed_exe=digest(patched_exe),installed_payload=digest(payload),payload_name=payload_name,native_offset=native.OFFSET,native_before=native.BEFORE.hex(),native_after=native.AFTER.hex(),required_free_bytes=768*1024*1024,resources=hashes,base_assets=entries)
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ('NotoSansArabic.ttf','OFL.txt'):shutil.copy2(ROOT/'04_fonts/src'/name,assets/name)
    (assets/'fonts.conf').write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig><include ignore_missing="yes">/etc/fonts/fonts.conf</include><dir prefix="relative">.</dir><cachedir prefix="xdg">fontconfig</cachedir></fontconfig>\n',encoding='utf-8')
    # Original geometric rail icon, rendered at native sizes for both platforms.
    im=Image.new('RGBA',(512,512),'#111819');d=ImageDraw.Draw(im)
    d.rectangle((0,0,511,18),fill='#ee913c');d.rectangle((0,493,511,511),fill='#ee913c')
    d.polygon([(70,400),(70,112),(139,112),(256,265),(373,112),(442,112),(442,400),(371,400),(371,239),(256,385),(141,239),(141,400)],fill='#edeee2')
    d.line((44,456,468,456),fill='#ee913c',width=8)
    im.save(assets/'icon.png');im.save(assets/'icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    print('READY:',out,'assets:',assets,flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--revision',default='final_review_r1');p.add_argument('--version',default='0.1.0-review');a=p.parse_args()
    main(a.revision,a.version)
