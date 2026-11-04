"""Offline loading-paragraph preview from the actual packaged bitmap font."""
import re,struct,json,zlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from metro_archive import index,extract
from build_arabic_fonts import signed16
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=package('rtl_r1',100);f=next(f for f in p['fonts'] if f['name']=='regular')
    key='voices\\m3_02_dead_moscow\\dmc_000_narration_01'
    audit=json.loads((ROOT/'08_qa/audit/rtl_layout_entries.json').read_text());limit=audit[key]['native_limit']
    lines=p['strings'][key].split('<br>');canvas=Image.new('RGB',(1120,120+len(lines)*58),(14,18,24))
    ImageDraw.Draw(canvas).text((25,22),'OFFLINE loading-text layout - real packaged glyph metrics',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23),fill='white')
    y=80;right_edges=[]
    for line in lines:
        text=re.sub('<[^>]+>','',line);x=60
        width=sum(f['glyphs'][p['chars'].index(c)][6] for c in text)
        if text.strip():assert width==limit,(width,limit);right_edges.append(width)
        for c in text:
            g=f['glyphs'][p['chars'].index(c)]
            if g[2] and g[3]:
                mask,g=tile(p,f,c);canvas.paste((255,255,255),(x+signed16(g[4]),y+signed16(g[5])),mask)
            x+=g[6]
        y+=58
    canvas.save(ROOT/'08_qa/render_tests/rtl_r1_loading_preview.png')
    # Confirm the live configuration patch only replaces fonts and loader timing.
    patch=ROOT/'07_patch/phases/100_rtl_r1';idx=index(patch/'patch_04.vfx')
    config=extract(patch,idx,next(e for e in idx['entries'] if e['name']=='config.bin'))
    def chunks(b):
        out={};pos=0
        while pos<len(b):
            crc,n=struct.unpack_from('<II',b,pos);pos+=8;out[crc]=b[pos:pos+n];pos+=n
        assert pos==len(b);return out
    old=chunks((ROOT/'02_extracted/steam_local/patch_04/content/config.bin').read_bytes());new=chunks(config)
    assert old.keys()==new.keys()
    expected={zlib.crc32(('content\\scripts\\'+n+'.bin').encode()) for n in ['fonts_us','loader_data']}
    assert {k for k in old if old[k]!=new[k]}==expected
    print('PASS Moscow paragraph right edges, logical wrapping and only two intended config replacements')
if __name__=='__main__':main()
