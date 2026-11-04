"""Extend Metro's indexed bitmap fonts, preserving original Latin glyph images."""
import io,json,struct,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import lz4.block,ispc_texcomp
from metro_archive import extract
from metro_fonts import read_fonts,write_fonts

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
BASE=ROOT/'02_extracted/steam_local'

def signed16(value):
    """Native bitmap rectangles can start at -1 (stored as uint16 65535)."""
    return value if value<32768 else value-65536

def dds(raw,dim,mips=1):
    h=bytearray(148);h[:4]=b'DDS '
    struct.pack_into('<7I',h,4,124,0xA1007,dim,dim,dim*dim,0,mips)
    struct.pack_into('<II4s',h,76,32,4,b'DX10');struct.pack_into('<I',h,108,0x401008)
    struct.pack_into('<5I',h,128,98,3,0,1,0)
    return Image.open(io.BytesIO(h+raw)).convert('RGBA')

def pack(items,dim):
    x=y=row=0;positions={}
    for i,im,meta in sorted(items,key=lambda item:-item[1].height):
        w,h=im.size
        if x+w+2>dim:x=0;y+=row;row=0
        if y+h+2>dim:return None
        positions[i]=(x+1,y+1);x+=w+2;row=max(row,h+2)
    return positions

def arabic_glyph(c,font,line):
    # Baseline at 78% of original line height. Keep per-glyph advances for joins.
    x0,y0,x1,y1=font.getbbox(c,anchor='ls')
    w=max(1,x1-x0);h=max(1,y1-y0)
    # Native Metro fonts store independent ink/glow masks in R/G and an
    # opaque glyph rectangle in A. Coverage alpha distorts the LCD shader.
    pad=3;scale=4
    large_font=ImageFont.truetype(str(ROOT/'04_fonts/build/noto_arabic_pf.ttf'),font.size*scale)
    mask=Image.new('L',((w+pad*2)*scale,(h+pad*2)*scale))
    ImageDraw.Draw(mask).text(((pad-x0)*scale,(pad-y0)*scale),c,font=large_font,fill=255,anchor='ls')
    mask=mask.resize((w+pad*2,h+pad*2),Image.Resampling.LANCZOS)
    border=mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.55))
    rgba=Image.merge('RGBA',(mask,border,Image.new('L',mask.size),Image.new('L',mask.size,255)))
    return rgba,[0,0,*mask.size,(x0-pad)&65535,round(line*.78+y0-pad)&65535,max(0,round(font.getlength(c)))]

def build(chars,original_chars):
    fonts=read_fonts((BASE/'patch_04/content/scripts/fonts_us.bin').read_bytes())
    idx=json.loads((BASE/'patch_04_index.json').read_text())
    stage=ROOT/'06_build/stage';outdir=ROOT/'04_fonts/build/atlases';outdir.mkdir(parents=True,exist_ok=True)
    built={}; report=[]
    for f in fonts:
        if len(f['glyphs'])!=len(original_chars):continue
        if f['name']=='main_menu':continue
        texture=f['texture'];dim=round(1/f['inv'][0]);name=texture.split('\\')[-1]
        if texture in built:
            f['glyphs']=copy.deepcopy(built[texture]);continue
        e=next(e for e in idx['entries'] if e['name']==name+f'.{dim}')
        data=extract(GAME,idx,e)
        raw=lz4.block.decompress(data,uncompressed_size=sum(max(4,dim>>i)**2 for i in range(10 if dim==512 else 1)))
        original=dds(raw,dim,10 if dim==512 else 1)
        olditems=[];unused_lcd=set()
        for i,g in enumerate(f['glyphs']):
            # The small main-menu display only shows the menu titles. Its
            # unused accented Latin alphabet need not reduce Arabic resolution.
            if f['name']=='main_menu_lcd' and ord(original_chars[i])>=128 and ord(original_chars[i])<0x2000:
                unused_lcd.add(i);continue
            x,y,w,h,*_=g
            if w and h:
                sx,sy=signed16(x),signed16(y)
                assert -8<=sx<dim and -8<=sy<dim,(f['name'],i,x,y)
                crop=original.crop((sx,sy,sx+w,sy+h));meta=g.copy()
                if original_chars[i].isascii() and original_chars[i].isalnum():
                    assert crop.getchannel('R').getextrema()[1]>0,(f['name'],original_chars[i],'empty original glyph')
                # Make space for Arabic at a comparable reading size in the fixed
                # 512px atlases; retain the original Latin artwork, scaled evenly.
                if dim==512 and f['line']>=50:
                    factor=.65
                    crop=crop.resize((max(1,round(w*factor)),max(1,round(h*factor))),Image.Resampling.LANCZOS)
                    meta[2:4]=list(crop.size)
                    meta[4]=round(signed16(g[4])*factor)&65535
                    meta[5]=round(f['line']*.78+(signed16(g[5])-f['line']*.78)*factor)&65535
                    meta[6]=round(g[6]*factor)
                olditems.append((i,crop,meta))
        start_size=round(f['line']*.82)
        for size in range(start_size,13,-1):
            font=ImageFont.truetype(str(ROOT/'04_fonts/build/noto_arabic_pf.ttf'),size)
            items=olditems.copy()
            for i,c in enumerate(chars[len(original_chars):],len(original_chars)):
                im,g=arabic_glyph(c,font,f['line']);items.append((i,im,g))
            positions=pack(items,dim)
            if positions:break
        if not positions:raise ValueError('Atlas overflow: '+name)
        atlas=Image.new('RGBA',(dim,dim));glyphs=copy.deepcopy(f['glyphs'])+[[0]*7 for c in chars[len(original_chars):]]
        for i in unused_lcd:glyphs[i]=[0]*7
        for i,im,g in items:
            x,y=positions[i];atlas.paste(im,(x,y));g[0:2]=[x,y];glyphs[i]=g
        f['glyphs']=glyphs;built[texture]=glyphs
        atlas.save(outdir/(name+'.png'))
        levels=[];im=atlas
        while True:
            im_bc=im if min(im.size)>=4 else im.resize((4,4))
            surface=ispc_texcomp.RGBASurface(im_bc.tobytes(),*im_bc.size)
            levels.append(ispc_texcomp.compress_blocks_bc7(surface,ispc_texcomp.BC7EncSettings.from_profile('alpha_slow')))
            if im.width==1:break
            next_size=(max(1,im.width//2),max(1,im.height//2))
            # These are data channels, not an ordinary premultiplied RGBA photo.
            im=Image.merge('RGBA',[ch.resize(next_size,Image.Resampling.LANCZOS) for ch in im.split()])
        # .512 contains the full lower mip chain; .1024 is the separate top level.
        if dim==1024:
            outputs={1024:levels[0],512:b''.join(levels[1:])}
        else:outputs={512:b''.join(levels)}
        for res,pixels in outputs.items():
            target=stage/'content/textures/font'/(name+f'.{res}');target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(lz4.block.compress(pixels,store_size=False))
            assert dds(pixels,res).size==(res,res)
        report.append(dict(font=f['name'],dimension=dim,arabic_size=size,original_chars=len(original_chars),total_chars=len(chars)))
        print('atlas',f['name'],dim,'size',size,'glyphs',len(glyphs),flush=True)
    menu=next(f for f in fonts if f['name']=='menu')
    main=next(f for f in fonts if f['name']=='main_menu')
    main.update(texture=menu['texture'],glyphs=copy.deepcopy(menu['glyphs']),inv=menu['inv'])
    result=write_fonts(fonts);assert read_fonts(result)==fonts
    output=stage/'content/scripts/fonts_us.bin';output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
    (ROOT/'08_qa/audit/font_build.json').write_text(json.dumps(report,indent=2))
    (ROOT/'04_fonts/build/font_characters.json').write_text(json.dumps(chars),encoding='utf-8')
    return result
