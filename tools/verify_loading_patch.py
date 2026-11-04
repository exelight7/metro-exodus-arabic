"""Validate packaged loading scope and reconstruct its static text offline."""
import csv,json,re,hashlib,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from loading_layout import is_loading,TAG
from subtitle_layout import GameRenderer
from build_arabic_fonts import signed16
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='loading_r1');args=parser.parse_args()
    before=package('spelling_r2',100);after=package(args.revision,100)
    assert before['chars']==after['chars'] and before['fonts']==after['fonts']
    assert before['strings'].keys()==after['strings'].keys()
    changes=[k for k in after['strings'] if before['strings'][k]!=after['strings'][k]]
    assert changes and all(is_loading(k) or (args.revision=='graphics_label_r1' and k=='$video') for k in changes)
    if args.revision=='graphics_label_r1':
        prior=package('loading_r1',100)
        assert [k for k in after['strings'] if prior['strings'][k]!=after['strings'][k]]==['$video']
        assert after['strings']['$video']==GameRenderer().plain.process('الرسوميات')
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    renderer=GameRenderer()
    for r in rows:
        if is_loading(r['id']):assert after['strings'][r['id']]==renderer.render(r['id'],r['target'])
    key='voices\\m3_02_dead_moscow\\dmc_000_narration_01'
    text=after['strings'][key];lines=text.split('<br>');audit=renderer.loading.audit[key]
    assert len(lines)==10 and len(lines)*(22+4)<=280
    assert not re.search(r' {2,}',TAG.sub('',text))
    f=next(f for f in after['fonts'] if f['name']=='regular')
    metric=json.loads((ROOT/'04_fonts/maps/loading_advances.json').read_text())
    assert f['line']==metric['line']
    assert {c:g[6] for c,g in zip(after['chars'],f['glyphs'])}==metric['advances']
    canvas=Image.new('RGB',(1160,760),(19,23,29));draw=ImageDraw.Draw(canvas)
    draw.text((24,20),'OFFLINE loading layout: native Right=1; original reveal timing retained',fill='white',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22))
    right=1090;y=88
    draw.line((right,76,right,710),fill=(70,100,120),width=1)
    for line,w in zip(lines,audit['line_widths']):
        x=right-w
        for c in TAG.sub('',line):
            g=f['glyphs'][after['chars'].index(c)]
            if g[2] and g[3] and c!=' ':
                mask,g=tile(after,f,c);canvas.paste((245,245,245),(x+signed16(g[4]),y+signed16(g[5])),mask)
            x+=g[6]
        assert x==right
        y+=58
    canvas.save(ROOT/f'08_qa/render_tests/{args.revision}_static_preview.png')
    report=dict(changed_loading_entries=sum(is_loading(k) for k in changes),other_label_changes=sum(not is_loading(k) for k in changes),unrelated_strings_preserved=len(after['strings'])-len(changes),
        loading_profile_entries=len(renderer.loading.audit),native_alignment='right_1',no_padding=True,
        moscow_lines=len(lines),moscow_height_estimate=260,moscow_rect_height=280,
        loading_native_limit=audit['limit'],actual_font_metrics_verified=True,
        loader_typing_animation_fixed=False,loader_timing_unchanged=True,runtime_tested=False)
    report['revision']=args.revision
    (ROOT/f'08_qa/audit/{args.revision}_layout.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
