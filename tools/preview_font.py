"""Offline preview using the actual rebuilt bitmap glyphs and metrics."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
from metro_lng import parse
from metro_fonts import read_fonts
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/vendor/game-arabization'))
from ar_shape import Shaper
chars,pairs=parse((ROOT/'06_build/stage/content/localization/stable_us.lng').read_bytes())
fonts=read_fonts((ROOT/'06_build/stage/content/scripts/fonts_us.bin').read_bytes())
font=next(f for f in fonts if f['name']=='regular')
atlas=Image.open(ROOT/'04_fonts/build/atlases/font_font_regular_us.png')
canvas=Image.new('RGB',(1100,390),(15,20,26));d=ImageDraw.Draw(canvas)
d.text((30,20),'OFFLINE BITMAP PREVIEW - NOT A GAME SCREENSHOT',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25),fill=(170,185,200))
lines=['متابعة','لعبة جديدة','الخيارات','أرتيوم، علينا مواصلة الرحلة إلى أورورا.','الذخيرة: 30 / 120 - الهدف 250 مترًا']
s=Shaper(mode='visual',harakat='strip',normalize_persian=True)
def signed(n):return n if n<32768 else n-65536
for n,line in enumerate(lines):
    text=s.process(line);gs=[font['glyphs'][chars.index(c)] for c in text]
    width=sum(g[6] for g in gs);x=1040-width;y=60+n*60
    for g in gs:
        gx,gy,w,h,xo,yo,advance=g
        if w and h:
            crop=atlas.crop((gx,gy,gx+w,gy+h));mask=crop.getchannel('R')
            white=Image.new('RGB',crop.size,(240,230,200));canvas.paste(white,(x+signed(xo),y+signed(yo)),mask)
        x+=advance
canvas.save(ROOT/'08_qa/render_tests/arabic_bitmap_preview.png')
print('Saved offline bitmap preview')
