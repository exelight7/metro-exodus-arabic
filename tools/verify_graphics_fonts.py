"""Regression checks against the actual packaged LNG/config/BC7 glyph data."""
import json,struct,string,zlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import lz4.block
from metro_archive import index,extract
from metro_fonts import read_fonts
from metro_lng import parse
from build_arabic_fonts import dds,signed16

ROOT=Path(__file__).resolve().parents[1]
def package(revision,phase=75):
    patch=ROOT/f'07_patch/phases/{phase}_{revision}';idx=index(patch/'patch_04.vfx')
    def file(name):return extract(patch,idx,next(e for e in idx['entries'] if e['name']==name))
    chars,pairs=parse(file('stable_us.lng'))
    config=file('config.bin');pos=0;fonts=None
    while pos<len(config):
        crc,n=struct.unpack_from('<II',config,pos);pos+=8
        if crc==zlib.crc32(b'content\\scripts\\fonts_us.bin'):fonts=read_fonts(config[pos:pos+n])
        pos+=n
    assert fonts is not None
    textures={}
    for f in fonts:
        if len(f['glyphs'])!=len(chars):continue
        name=f['texture'].split('\\')[-1];dim=round(1/f['inv'][0]);key=(name,dim)
        if key not in textures:
            n=sum(max(4,dim>>i)**2 for i in range(10 if dim==512 else 1))
            raw=lz4.block.decompress(file(name+f'.{dim}'),uncompressed_size=n)
            textures[key]=dds(raw,dim,10 if dim==512 else 1)
    return dict(chars=chars,strings=dict(pairs),fonts=fonts,textures=textures)

def tile(p,f,c):
    glyph=f['glyphs'][p['chars'].index(c)];x,y,w,h,*_=glyph
    atlas=p['textures'][(f['texture'].split('\\')[-1],round(1/f['inv'][0]))]
    assert 0<=x<x+w<=atlas.width and 0<=y<y+h<=atlas.height,(f['name'],c,glyph)
    return atlas.crop((x,y,x+w,y+h)).getchannel('R'),glyph

def draw_text(canvas,p,text,x,y):
    f=next(f for f in p['fonts'] if f['name']=='menu')
    for c in text:
        g=f['glyphs'][p['chars'].index(c)]
        if c!=' ':
            mask,g=tile(p,f,c)
            canvas.paste((240,230,200),(x+signed16(g[4]),y+signed16(g[5]),x+signed16(g[4])+mask.width,y+signed16(g[5])+mask.height),mask)
        x+=g[6]

def main():
    before=package('settings_r1');after=package('settings_r2');recovered={};checked=0
    for f in after['fonts']:
        if len(f['glyphs'])!=len(after['chars']):continue
        old=next(o for o in before['fonts'] if o['name']==f['name']);fixed=[]
        for c in string.ascii_letters+string.digits:
            mask,_=tile(after,f,c);assert mask.getextrema()[1]>=16,(f['name'],c,'missing packaged glyph')
            oldmask,_=tile(before,old,c)
            if oldmask.getextrema()[1]<16:fixed.append(c)
            checked+=1
        recovered[f['name']]=''.join(fixed)
    expected={'$vsync':'VSync','$direct_x':'DirectX','$raytrace':'NVIDIA RTX','$rtgi':'Ray Tracing','options_video_hairworks':'HairWorks','$adv_phisics':'Advanced PhysX','$tesselation':'Tessellation','$shading_rate':'Shading Rate','$dlss':'DLSS','$af_16x':'AF 16X'}
    for key,value in expected.items():assert after['strings'][key]==value,(key,after['strings'][key])
    assert set('cdkS')<=set(recovered['menu'])
    assert before['strings']==after['strings'],'Font repair must preserve all localization text'
    canvas=Image.new('RGB',(1000,550),(18,24,32));d=ImageDraw.Draw(canvas);title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    d.text((30,20),'BEFORE: packaged font with missing glyphs',font=title,fill='white')
    d.text((525,20),'AFTER: corrected signed coordinates',font=title,fill='white')
    for i,text in enumerate(['VSync','DirectX','NVIDIA RTX','Ray Tracing','HairWorks','Advanced PhysX','Tessellation','Shading Rate']):
        draw_text(canvas,before,text,35,65+i*54);draw_text(canvas,after,text,530,65+i*54)
    d.text((30,515),'Offline reconstruction from the actual patch; not an in-game screenshot.',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18),fill=(160,180,200))
    canvas.save(ROOT/'08_qa/render_tests/graphics_font_before_after.png')
    report=dict(glyph_checks=checked,recovered_characters=recovered,english_labels=expected,all_localization_text_preserved=True,runtime_tested=False)
    (ROOT/'08_qa/audit/settings_r2.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
