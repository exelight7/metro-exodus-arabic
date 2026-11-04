"""Check all diary profiles, changed scope, actual font metrics and native UI."""
import csv,json,re,struct,collections,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from verify_graphics_fonts import package,tile
from verify_repair_patch import records
from metro_archive import index,extract
from diary_layout import profile,NOTE,TAG
from subtitle_layout import GameRenderer
from build_diary_ui import TARGETS,patch_record
from build_arabic_fonts import signed16
from loading_layout import is_loading
ROOT=Path(__file__).resolve().parents[1]

def preview(p,key):
    f=next(f for f in p['fonts'] if f['name']=='regular')
    glyphs=dict(zip(p['chars'],f['glyphs']));fontmap={}
    # Draw at actual atlas resolution, then resize the complete page uniformly.
    lines=p['strings'][key].split('<br>')
    width=math.ceil(650*56/24);height=len(lines)*56+60
    page=Image.new('RGB',(width,height),(239,218,176))
    for line_no,line in enumerate(lines):
        visible=TAG.sub('',line)
        x=width-28-sum(glyphs[c][6] for c in visible);y=10+line_no*56
        for c in visible:
            g=glyphs[c]
            if c!=' ' and g[2] and g[3]:
                if c not in fontmap:fontmap[c]=tile(p,f,c)[0]
                page.paste((24,20,14),(x+signed16(g[4]),y+signed16(g[5])),fontmap[c])
            x+=g[6]
    page=page.resize((1000,round(height*1000/width)),Image.Resampling.LANCZOS)
    canvas=Image.new('RGB',(1080,page.height+165),(25,27,30));draw=ImageDraw.Draw(canvas)
    draw.text((40,22),'OFFLINE - full diary text / right aligned / original game glyphs',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24),fill='white')
    draw.text((40,60),'Native page scrolling is retained. This preview is not a game screenshot.',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19),fill=(190,195,200))
    canvas.paste(page,(40,110))
    out=ROOT/'08_qa/render_tests/diary_r1_dusty_diary.png';canvas.save(out)

def main():
    before=package('graphics_label_r1',100);after=package('diary_r1',100)
    assert before['chars']==after['chars'] and before['fonts']==after['fonts']
    assert before['strings'].keys()==after['strings'].keys()
    reviewed=json.loads((ROOT/'03_translation/review/diary_r1_review_receipt.json').read_text(encoding='utf-8'))
    allowed=set(reviewed['reviewed_keys'])
    changed=[k for k in after['strings'] if after['strings'][k]!=before['strings'][k]]
    assert all(profile(k) or k in allowed for k in changed),[k for k in changed if not profile(k) and k not in allowed]
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    renderer=GameRenderer();counts=collections.Counter()
    for r in rows:
        if not profile(r['id']):continue
        actual=after['strings'][r['id']];assert actual==renderer.render(r['id'],r['target']),r['id']
        counts[profile(r['id'])]+=1
        assert '<tab>' not in actual and '<br><br><br>' not in actual and not re.search(' {2,}',TAG.sub('',actual)),r['id']
        assert collections.Counter(re.findall('<[^>]+>',r['source']))==collections.Counter(re.findall('<[^>]+>',r['target'])),r['id']
    assert counts['note']==116
    metric=json.loads((ROOT/'04_fonts/maps/diary_advances.json').read_text(encoding='utf-8'))
    for f in after['fonts']:
        if f['name'] in metric:
            assert metric[f['name']]['line']==f['line']
            assert metric[f['name']]['advances']=={c:g[6] for c,g in zip(after['chars'],f['glyphs'])}
    menu_font=metric['menu'];titles=[]
    for r in rows:
        if NOTE.match(r['id']) and r['id'].endswith('_name'):
            w=sum(menu_font['advances'][c] for c in after['strings'][r['id']])*30/menu_font['line']
            assert w<=650-24,(r['id'],w)
            titles.append(r['id'])
    assert len(titles)==112
    patch=ROOT/'07_patch/phases/100_diary_r1';idx=index(patch/'patch_04.vfx')
    menu=extract(patch,idx,next(e for e in idx['entries'] if e['name']=='menu_handles_storage.bin'))
    clean=records((ROOT/'02_extracted/steam_local/patch_04/content/menu_handles_storage.bin').read_bytes());new=records(menu)
    assert [i for i in clean if clean[i]!=new[i]]==[42,51,67,88,100]
    for i in TARGETS:
        assert new[i]==patch_record(clean[i],i)
        old=new[i]
        for name in TARGETS[i]:
            m=b'\3'+name.encode()+b'\0type\0u32\0';pos=old.index(m);n=struct.unpack_from('<I',old,pos-4)[0];c=old[pos:pos+n]
            h=b'h_alignment\0u8\0';assert c[c.index(h)+len(h)]==1
        # Native scrolling and page relationships are untouched.
        assert new[i].count(b'scroll_pages\0bool\0\1')==clean[i].count(b'scroll_pages\0bool\0\1')
    assert all(before['strings'][k]==after['strings'][k] for k in before['strings'] if is_loading(k))
    key='m3_01_moscow_diary_3_dsc'
    source_target=next(r['target'] for r in rows if r['id']==key)
    assert 'الصواريخ تحلق' in source_target and 'شورا' in source_target
    assert renderer.plain.process('الصواريخ تحلق') in after['strings'][key]
    preview(after,key)
    report=dict(revision='diary_r1',profile_entries=dict(counts),note_titles_checked=len(titles),
        reviewed_translation_entries=reviewed['reviewed_count'],changed_lng_entries=len(changed),
        unrelated_lng_entries_preserved=len(after['strings'])-len(changed),actual_font_metrics_verified=True,
        all_lines_within_native_columns=True,scrolling_retained=True,loading_text_identical=True,
        changed_menu_records=[42,51,67,88,100],unchanged_font_and_atlas=True,runtime_tested=False,
        per_entry=renderer.diary.audit)
    (ROOT/'08_qa/audit/diary_r1_layout.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='per_entry'}))
if __name__=='__main__':main()
