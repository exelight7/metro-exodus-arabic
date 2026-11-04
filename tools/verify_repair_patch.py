"""Regression checks for the user's missing-dialogue and gap screenshots."""
import json,csv,re,struct,zlib,string,unicodedata,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from metro_archive import index,extract
from metro_fonts import read_fonts
from subtitle_layout import GameRenderer,TAG,TIME
from build_arabic_fonts import signed16
from loading_layout import is_loading
ROOT=Path(__file__).resolve().parents[1]
PATCH=ROOT/'07_patch/phases/100_repair_r1'
def records(b):
    pos=10;out={}
    for _ in range(struct.unpack_from('<I',b,6)[0]):
        idx,n=struct.unpack_from('<II',b,pos);pos+=8;out[idx]=b[pos:pos+n];pos+=n
    assert pos==len(b);return out
def main():
    global PATCH
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='repair_r1');args=ap.parse_args()
    PATCH=ROOT/f'07_patch/phases/100_{args.revision}'
    p=package(args.revision,100);idx=index(PATCH/'patch_04.vfx')
    assert p['chars']==json.loads((ROOT/'04_fonts/build/font_characters.json').read_text()),'Font character table differs from LNG'
    assert not any(0xE000<=ord(c)<=0xEFFF for c in p['chars'])
    assert 'ar_speaker' not in {f['name'] for f in p['fonts']}
    source_fonts=read_fonts((ROOT/'02_extracted/steam_local/patch_04/content/scripts/fonts_us.bin').read_bytes())
    assert {f['name'] for f in p['fonts']}=={f['name'] for f in source_fonts}
    regular=next(f for f in p['fonts'] if f['name']=='regular');visible_glyphs=0;ascii_checks=0
    for c,g in zip(p['chars'],regular['glyphs']):
        if unicodedata.category(c).startswith('L') or c in string.digits:
            assert g[2]>0 and g[3]>0,('hidden body glyph',ascii(c))
            mask,_=tile(p,regular,c);assert mask.getextrema()[1]>=16,ascii(c);visible_glyphs+=1
    for f in p['fonts']:
        if len(f['glyphs'])!=len(p['chars']):continue
        for c in string.ascii_letters+string.digits:
            mask,_=tile(p,f,c);assert mask.getextrema()[1]>=16,(f['name'],c);ascii_checks+=1
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    renderer=GameRenderer();speaker_lines=0;timed=0;cues=0
    for r in rows:
        text=p['strings'][r['id']]
        assert not any(0xE000<=ord(c)<=0xEFFF for c in text),r['id']
        assert TIME.findall(text)==TIME.findall(r['source'])
        if TIME.search(r['source']):
            timed+=1
            for part in TIME.split(r['target']):
                if TIME.fullmatch(part):continue
                if TAG.sub('',part).strip():assert re.search('[\u0600-\u06ff]',part);cues+=1
        name=renderer.names.get(renderer.speakers.get(r['id']))
        if name and not is_loading(r['id']) and not r['id'].endswith('_deaf') and TAG.sub('',r['target']).strip() and not TIME.search(r['source']):
            first=TAG.sub('',text.split('<br>')[0]).rstrip()
            assert first.endswith(renderer.plain.process(name)),r['id']
            # All body letters and speaker letters use the same full visible font.
            assert not re.fullmatch(re.escape(renderer.plain.process(name+':')),TAG.sub('',text).strip())
            speaker_lines+=1
    assert timed==39 and cues==311
    supplemental_path=ROOT/'03_translation/supplemental_entries.json'
    supplemental=json.loads(supplemental_path.read_text(encoding='utf-8')) if supplemental_path.exists() else []
    assert len(p['strings'])==len(rows)+len(supplemental)
    for r in supplemental:
        assert p['strings'][r['id']]==renderer.render(r['id'],r['target'])
    menu=extract(PATCH,idx,next(e for e in idx['entries'] if e['name']=='menu_handles_storage.bin'))
    old=records((ROOT/'02_extracted/steam_local/patch_04/content/menu_handles_storage.bin').read_bytes());new=records(menu)
    expected=[42,51,67,88,100] if args.revision in ('diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1') else [51,67] if args.revision in ('loading_r1','graphics_label_r1') else [51]
    assert old.keys()==new.keys() and [k for k in old if old[k]!=new[k]]==expected
    if args.revision in ('loading_r1','graphics_label_r1','diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):
        from build_loading_ui import patch_record
        assert new[67]==patch_record(old[67])
    if args.revision in ('diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):
        from build_diary_ui import patch_record,TARGETS
        for i in TARGETS:assert new[i]==patch_record(old[i],i)
    assert len(old[51])==len(new[51])
    marker=b'controls\0count\0u32\0';q=new[51].index(marker)+len(marker)
    assert struct.unpack_from('<I',new[51],q)[0]==1
    assert b'ar_speaker' not in new[51] and b'subtitles_ar_names' not in new[51]
    font=b'text_font\0stringz\0regular\0';assert new[51].count(font)==1
    for name in ['text_color','deaf_color']:
        mark=name.encode()+b'\0vec4i\0';q=new[51].index(mark)+len(mark)
        assert struct.unpack_from('<4I',new[51],q)==(255,255,255,255)
    config=extract(PATCH,idx,next(e for e in idx['entries'] if e['name']=='config.bin'));pos=0;loader=None
    while pos<len(config):
        crc,n=struct.unpack_from('<II',config,pos);pos+=8
        if crc==zlib.crc32(b'content\\scripts\\loader_data.bin'):loader=config[pos:pos+n]
        pos+=n
    assert loader==(ROOT/'02_extracted/steam_local/patch_04/content/scripts/loader_data.bin').read_bytes()
    loading=p['strings']['voices\\m3_02_dead_moscow\\dmc_000_narration_01']
    assert not re.search(' {2,}',TAG.sub('',loading))
    canvas=Image.new('RGB',(1500,420),(12,17,24));draw=ImageDraw.Draw(canvas)
    draw.text((25,18),'OFFLINE: single control, complete visible dialogue, no padding glyphs',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22),fill='white')
    y=80
    for key in ['voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_04','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_16','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_17']:
        for line in p['strings'][key].split('<br>'):
            text=TAG.sub('',line);x=(1500-sum(regular['glyphs'][p['chars'].index(c)][6] for c in text))//2
            for c in text:
                g=regular['glyphs'][p['chars'].index(c)]
                if g[2] and g[3] and c!=' ':
                    mask,g=tile(p,regular,c);canvas.paste((255,255,255),(x+signed16(g[4]),y+signed16(g[5])),mask)
                x+=g[6]
            y+=60
        y+=15
    canvas.save(ROOT/f'08_qa/render_tests/{args.revision}_subtitle_preview.png')
    report=dict(single_native_control=True,complete_visible_body_font=True,visible_regular_letters_digits=visible_glyphs,
        packaged_ascii_checks=ascii_checks,speaker_lines=speaker_lines,timed_entries=timed,timed_cues=cues,
        private_mask_and_padding_characters=0,loader_restored=True,unrelated_menu_records_preserved=210,
        dialogue_color='white',speaker_color='white_temporarily',orange_name_color_pending=True,runtime_tested=False)
    report['unrelated_menu_records_preserved']=len(old)-len(expected)
    report.update(total_runtime_entries=len(p['strings']),supplemental_reviewed_entries=len(supplemental))
    (ROOT/f'08_qa/audit/{args.revision}.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
