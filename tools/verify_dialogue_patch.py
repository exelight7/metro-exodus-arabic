import csv,json,re,string,unicodedata
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from build_arabic_fonts import signed16
from subtitle_layout import GameRenderer,TAG,TIME
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=package('dialogue_r1');rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    renderer=GameRenderer();timed=[r for r in rows if TIME.search(r['source'])];assert len(timed)==39
    cue_count=0
    for r in timed:
        output=p['strings'][r['id']]
        assert TIME.findall(output)==TIME.findall(r['source']),r['id']
        for part in TIME.split(r['target']):
            if TIME.fullmatch(part):continue
            visible=TAG.sub('',part).strip()
            if visible:
                assert re.search('[\u0600-\u06ff]',visible),(r['id'],visible)
                cue_count+=1
    for key in renderer.actors:
        if key in p['strings']:assert p['strings'][key]=='',key
    tested=0
    from ar_shape import Shaper
    simple=Shaper(mode='visual',harakat='strip',normalize_persian=True,newline_tokens=['\n','<br>'])
    for r in rows:
        persona=renderer.speakers.get(r['id']);name=renderer.names.get(persona)
        if not name or r['id'].endswith('_deaf') or TIME.search(r['source']):continue
        if not TAG.sub('',r['target']).strip():continue
        first=TAG.sub('',p['strings'][r['id']].split('<br>')[0]).rstrip()
        assert first.endswith(simple.process(name)),r['id']
        assert sum(unicodedata.category(c) not in ('Mn','Me','Cf') for c in first)<=72,r['id']
        tested+=1
    glyph_count=0
    for f in p['fonts']:
        if len(f['glyphs'])!=len(p['chars']):continue
        for c in string.ascii_letters+string.digits:
            mask,_=tile(p,f,c);assert mask.getextrema()[1]>=16,(f['name'],c);glyph_count+=1
    font=next(f for f in p['fonts'] if f['name']=='regular')
    canvas=Image.new('RGB',(1500,450),(10,15,22));d=ImageDraw.Draw(canvas)
    title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    d.text((30,18),'OFFLINE SUBTITLE LAYOUT - speaker at the right, dialogue continues to the left',font=title,fill='white')
    examples=['voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_04','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_16','voices\\m3_02_dead_moscow\\dmc_001_spartans_save_01_00_17']
    y=80
    for key in examples:
        lines=p['strings'][key].split('<br>')
        for line in lines:
            text=TAG.sub('',line);width=sum(font['glyphs'][p['chars'].index(c)][6] for c in text);x=(1500-width)//2
            for c in text:
                g=font['glyphs'][p['chars'].index(c)]
                if c!=' ':
                    mask,g=tile(p,font,c);canvas.paste((240,163,62),(x+signed16(g[4]),y+signed16(g[5]),x+signed16(g[4])+mask.width,y+signed16(g[5])+mask.height),mask)
                x+=g[6]
            y+=62
        y+=18
    canvas.save(ROOT/'08_qa/render_tests/subtitle_order_preview.png')
    report=dict(timed_entries=39,translated_cues=cue_count,time_markers_preserved=True,verified_speaker_lines=tested,packaged_glyph_checks=glyph_count,video_files_reencoded=False,other_untranslated_entries=sum(r['status']=='todo' for r in rows),runtime_tested=False)
    (ROOT/'08_qa/audit/dialogue_r1.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
