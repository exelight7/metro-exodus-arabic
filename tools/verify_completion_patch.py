"""Verify the bytes actually shipped; preview is explicitly an offline render."""
import csv,json,re,string,struct,zlib,unicodedata,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from metro_archive import index,extract
from subtitle_layout import GameRenderer,TAG,TIME
from subtitle_color import aliases,decode_name
from rtl_layout import SPACERS
from build_arabic_fonts import signed16
ROOT=Path(__file__).resolve().parents[1]
PATCH=ROOT/'07_patch/phases/100_text_complete_r1'

def records(b):
    assert b[:6]==b'AVER\x07\0';p=10;out={}
    for _ in range(struct.unpack_from('<I',b,6)[0]):
        i,n=struct.unpack_from('<II',b,p);p+=8;out[i]=b[p:p+n];p+=n
    assert p==len(b);return out

def main():
    global PATCH
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='text_complete_r1');args=ap.parse_args()
    PATCH=ROOT/f'07_patch/phases/100_{args.revision}'
    p=package(args.revision,100)
    assert p['chars']==json.loads((ROOT/'04_fonts/build/font_characters.json').read_text(encoding='utf-8'))
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    report=json.loads((ROOT/'08_qa/audit/localization_build.json').read_text())
    assert not report['issues'] and not report['statuses'].get('todo')
    assert len(p['strings'])==len(rows)==38221
    renderer=GameRenderer();timed=0;cues=0;speakers=0
    for r in rows:
        built=p['strings'][r['id']]
        assert built==renderer.render(r['id'],r['target']),r['id']
        assert TIME.findall(built)==TIME.findall(r['source']),r['id']
        if TIME.search(r['source']):
            timed+=1
            for part in TIME.split(r['target']):
                if TIME.fullmatch(part):continue
                if TAG.sub('',part).strip():
                    assert re.search('[\u0600-\u06ff]',part),r['id'];cues+=1
        persona=renderer.speakers.get(r['id']);name=renderer.names.get(persona)
        if name and not r['id'].endswith('_deaf') and TAG.sub('',r['target']).strip() and not TIME.search(r['source']):
            first=TAG.sub('',decode_name(built).split('<br>')[0]).rstrip()
            assert first.endswith(renderer.plain.process(name)),r['id']
            if args.revision!='rtl_r1':assert sum(unicodedata.category(c) not in ('Mn','Me','Cf') for c in first)<=72,r['id']
            speakers+=1
    assert timed==39 and cues==311
    regular=next(f for f in p['fonts'] if f['name']=='regular')
    orange=next(f for f in p['fonts'] if f['name']=='ar_speaker')
    alias_chars=set(aliases().values());glyph_count=0
    if args.revision=='rtl_r1':
        native=json.loads((ROOT/'04_fonts/maps/native_advances.json').read_text())
        for f in p['fonts']:
            if f['name'] not in ('regular','menu','typewriter'):continue
            for c,g in zip(p['chars'],f['glyphs']):
                if c in SPACERS:assert g==[0,0,0,0,0,0,SPACERS[c]]
                elif c in native[f['name']]['advances']:assert g[6]==native[f['name']]['advances'][c],(f['name'],c)
    for i,c in enumerate(p['chars']):
        a,b=regular['glyphs'][i],orange['glyphs'][i]
        assert a[4:]==b[4:],c
        if c in alias_chars:
            assert a[:4]==[0,0,0,0];mask,_=tile(p,orange,c)
            assert mask.getextrema()[1]>16,c
        else:assert b[:4]==[0,0,0,0],c
    for f in p['fonts']:
        if len(f['glyphs'])!=len(p['chars']) or f['name']=='ar_speaker':continue
        for c in string.ascii_letters+string.digits:
            mask,_=tile(p,f,c);assert mask.getextrema()[1]>=16,(f['name'],c);glyph_count+=1
    idx=index(PATCH/'patch_04.vfx')
    menu=extract(PATCH,idx,next(e for e in idx['entries'] if e['name']=='menu_handles_storage.bin'))
    original=records((ROOT/'02_extracted/steam_local/patch_04/content/menu_handles_storage.bin').read_bytes())
    result=records(menu);assert result.keys()==original.keys()
    assert [i for i in result if result[i]!=original[i]]==[51]
    body=result[51];marker=b'controls\0array\0';a=body.index(marker)+len(marker)
    crc,n=struct.unpack_from('<II',body,a);a+=8;end=a+n
    count_marker=b'\x03controls\0count\0u32\0';assert body[a:a+len(count_marker)]==count_marker
    a+=len(count_marker);assert struct.unpack_from('<I',body,a)[0]==2;a+=4;controls=[]
    for name in ['subtitles','subtitles_ar_names']:
        crc,n=struct.unpack_from('<II',body,a);a+=8;assert crc==zlib.crc32(name.encode())
        child=body[a:a+n];a+=n;assert child.startswith(b'\x03'+name.encode()+b'\0')
        field=b'\x03hide_base\0';q=child.index(field)-8;_,size=struct.unpack_from('<II',child,q)
        assert child[q+8:q+8+size].startswith(field)
        assert child[q+8+size:].startswith(b'text_color\0vec4i\0')
        col=b'text_color\0vec4i\0';q=child.index(col)+len(col)
        assert struct.unpack_from('<4I',child,q)==((255,255,255,255) if name=='subtitles' else (255,100,0,255))
        controls.append(child)
    assert a==end
    def field(child,name,n):
        mark=name.encode()+b'\0';q=child.index(mark)+len(mark)
        return child[q:q+n]
    # Same text rectangles, sizes and line spacing in both native layers.
    for marker,n in [('text_rect\0vec4f',16),('text_size\0fp32',4),('line_spacing\0u32',4)]:
        assert field(controls[0],marker,n)==field(controls[1],marker,n)
    for key in ['m3_loader_hint_hold','m3_loader_hint_hold_xbox','m3_hold_continue','m3_hold_continue_xbox']:
        assert next(r for r in rows if r['id']==key)['target'].startswith('متابعة ')
    # Render complementary masks from actual packaged BC7 data.
    canvas=Image.new('RGB',(1500,440),(12,17,24));draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    draw.text((30,20),'OFFLINE PACKAGE PREVIEW - white speech / orange speaker (in-game check pending)',font=font,fill='white')
    y=85
    for key in ['voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_04','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_16','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_17']:
        for line in p['strings'][key].split('<br>'):
            text=TAG.sub('',line);width=sum(regular['glyphs'][p['chars'].index(c)][6] for c in text);x=(1500-width)//2
            for c in text:
                f=orange if c in alias_chars else regular;g=f['glyphs'][p['chars'].index(c)]
                if g[2] and g[3] and c!=' ':
                    mask,g=tile(p,f,c);box=(x+signed16(g[4]),y+signed16(g[5]));canvas.paste((255,100,0) if c in alias_chars else (255,255,255),box,mask)
                x+=g[6]
            y+=60
        y+=15
    canvas.save(ROOT/f'08_qa/render_tests/{args.revision}_subtitle_preview.png')
    report.update(timed_entries_verified=timed,translated_cues_verified=cues,verified_speaker_lines=speakers,
        packaged_ascii_checks=glyph_count,complementary_font_masks_verified=True,
        menu_records_preserved=len(result)-1,native_subtitle_control_count=2,
        runtime_tested=False,native_overlay_subscription_verified=False)
    if args.revision=='rtl_r1':
        layouts=json.loads((ROOT/'08_qa/audit/rtl_layout_entries.json').read_text())
        report.update(rtl_layout_entries=len(layouts),right_aligned_native_advances=True,rtl_animation_supported=False)
        report['right_alignment_profile_entries']=sum(v['profile'] is not None for v in layouts.values())
        report['right_alignment_unresolved_entries']=sum(v.get('right_alignment_unresolved',False) for v in layouts.values())
        over=[k for k,v in layouts.items() if any(w>v['native_limit'] for w in v['line_widths'])]
        report['unbreakable_overwidth_entries']=len(over)
        (ROOT/'08_qa/audit/rtl_overwidth_entries.json').write_text(json.dumps(over))
    (ROOT/f'08_qa/audit/{args.revision}.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
