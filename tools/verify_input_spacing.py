"""Check actual packaged icon spacing, unchanged scope and representative preview."""
import csv,json,re,struct,collections
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from metro_archive import index,extract
from subtitle_layout import GameRenderer,TAG
from input_spacing import normalize_input_spacing,INPUT
from build_arabic_fonts import signed16
ROOT=Path(__file__).resolve().parents[1]

def main():
    before=package('diary_r1',100);after=package('input_spacing_r1',100)
    assert before['chars']==after['chars'] and before['fonts']==after['fonts']
    assert before['strings'].keys()==after['strings'].keys()
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    by={r['id']:r for r in rows};renderer=GameRenderer()
    changed=[k for k in after['strings'] if after['strings'][k]!=before['strings'][k]]
    for k in changed:
        assert not k.startswith('voices\\') and INPUT.search(by[k]['source']),k
        assert collections.Counter(t for t in TAG.findall(after['strings'][k]) if t!='<br>')==collections.Counter(t for t in TAG.findall(before['strings'][k]) if t!='<br>'),k
        assert after['strings'][k]==renderer.render(k,by[k]['target']),k
        assert normalize_input_spacing(k,by[k]['target'])==by[k]['target'],k
    for k,t in [('video_skip_hint','<menu_ok>'),('video_skip_hint_cstm','<xpad_x>'),('video_skip_hint_xbox','<xpad_x>')]:
        expected=renderer.plain.process('للتخطي')+'  '+t+'  '+renderer.plain.process('اضغط على')
        assert after['strings'][k]==expected,(k,ascii(after['strings'][k]),ascii(expected))
        assert k in changed
    # No native menu, font, texture, loader configuration or other asset changes.
    payloads=[]
    for revision in ['diary_r1','input_spacing_r1']:
        folder=ROOT/f'07_patch/phases/100_{revision}';idx=index(folder/'patch_04.vfx')
        payloads.append({e['path']:extract(folder,idx,e) for e in idx['entries'] if e.get('pak')==len(idx['packs'])-1})
    assert payloads[0].keys()==payloads[1].keys()
    assets=[k for k in payloads[0] if payloads[0][k]!=payloads[1][k]]
    assert len(assets)==1 and assets[0].endswith('stable_us.lng'),assets
    font=next(f for f in after['fonts'] if f['name']=='regular');glyphs=dict(zip(after['chars'],font['glyphs']))
    canvas=Image.new('RGB',(1100,370),(18,21,27));d=ImageDraw.Draw(canvas)
    label=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    d.text((25,16),'OFFLINE - same game glyphs; representative E button, actual binding remains dynamic',font=label,fill=(210,215,220))
    masks={}
    for row,(label_text,pkg) in enumerate([('Before',before),('After',after)]):
        y=100+row*150;d.text((25,y+10),label_text,font=label,fill='white')
        visual=pkg['strings']['video_skip_hint'];width=sum(glyphs[c][6] for c in TAG.sub('',visual))+48
        x=1060-width
        for part in re.split('(<[^>]+>)',visual):
            if part.startswith('<'):
                d.rounded_rectangle((x,y+1,x+47,y+56),radius=5,fill=(230,232,235))
                d.text((x+14,y+9),'E',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',32),fill=(40,45,50));x+=48
            else:
                for c in part:
                    g=glyphs[c]
                    if c!=' ' and g[2] and g[3]:
                        if c not in masks:masks[c]=tile(after,font,c)[0]
                        canvas.paste('white',(x+signed16(g[4]),y+signed16(g[5])),masks[c])
                    x+=g[6]
    canvas.save(ROOT/'08_qa/render_tests/input_spacing_r1_before_after.png')
    report=dict(revision='input_spacing_r1',changed_entries=len(changed),changed_keys=changed,
        unrelated_entries_preserved=len(after['strings'])-len(changed),skip_variants_checked=3,
        joined_word_bug_removed=True,skip_gap_native_units_each_side=2*glyphs[' '][6],
        tags_preserved=True,dynamic_button_bindings_preserved=True,other_assets_byte_identical=True,
        fonts_unchanged=True,runtime_tested=False)
    (ROOT/'08_qa/audit/input_spacing_r1_spacing.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='changed_keys'}))
if __name__=='__main__':main()
