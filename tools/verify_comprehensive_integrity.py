"""Verify changed meaning-sensitive lines and retained reading/layout conventions."""
import csv,json,re,collections,argparse
from pathlib import Path
from verify_graphics_fonts import package
from subtitle_layout import GameRenderer,TAG
from diary_layout import profile
from input_spacing import normalize_input_spacing
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',choices=['comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'],default='comprehensive_r1');args=ap.parse_args()
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    before=package({'comprehensive_r1':'formal_terms_r4','comprehensive_r2':'comprehensive_r1','comprehensive_r3':'comprehensive_r2','final_review_r1':'comprehensive_r3'}[args.revision],100);after=package(args.revision,100)
    change=json.loads((ROOT/f'08_qa/audit/{args.revision}_language.json').read_text(encoding='utf-8'))
    for r in change['changes']:
        numeric_target=TAG.sub('',r['target'])
        # One month is written naturally in the reviewed provisions note.
        # This narrowly scoped equivalence leaves every other numeric token strict.
        if args.revision=='comprehensive_r3' and r['id']=='m3_12_val_diary_23_dsc':
            assert numeric_target.count('لشهر واحد')==1
            numeric_target=numeric_target.replace('لشهر واحد','1')
        assert collections.Counter(re.findall(r'\d+',TAG.sub('',r['source'])))==collections.Counter(re.findall(r'\d+',numeric_target)),('numeric content',r['id'])
    renderer=GameRenderer();profiles=collections.Counter();icon_entries=0;tech=[]
    exceptions={'directx','dx 11','dx 12','nvidia rtx','ray tracing','hairworks','advanced physx','tessellation','v-sync','vsync','shading rate','dlss'}
    for r in rows:
        key=r['id'];plain=TAG.sub('',r['source']).strip().casefold()
        if plain in exceptions:
            assert before['strings'][key]==after['strings'][key],('graphics exception',key)
            tech.append(key)
        assert normalize_input_spacing(key,r['target'])==r['target'],key
        if re.search('<(?:menu_ok|wpn_|popup_|use>|inventory>)',r['source']) and not key.startswith('voices\\'):icon_entries+=1
        if profile(key):
            actual=renderer.render(key,r['target']);assert actual==after['strings'][key],key
            profiles[profile(key)]+=1
        elif key.startswith(('m3_loader_diary_','voices\\')) and ('_000_narration' in key or key.startswith('m3_loader_diary_')):
            assert renderer.render(key,r['target'])==after['strings'][key],key
    for font in after['fonts']:
        metrics=json.loads((ROOT/'04_fonts/maps/diary_advances.json').read_text(encoding='utf-8')).get(font['name'])
        if metrics:
            assert metrics['line']==font['line']
            assert metrics['advances']=={c:g[6] for c,g in zip(after['chars'],font['glyphs'])}
    assert profiles==dict(note=116,journal=84,advice=20),profiles
    for r in rows:
        if 'credits' not in r['id']:
            assert 'العدو أسفل' not in r['target'],r['id']
            assert not re.search('يمارس الجنس|الجنس مع',r['target']),r['id']
    report=dict(revision=args.revision,changed_entries_numbers_preserved=len(change['changes']),graphics_exception_entries_preserved=len(tech),
        reading_profiles=dict(profiles),reading_metrics_match_packaged_fonts=True,loading_records_checked=len(renderer.loading.audit),
        input_spacing_idempotent_across_all_rows=len(rows),input_entries=icon_entries,reading_lines_within_actual_native_columns=True,
        known_literal_down_and_sexual_idiom_errors_remaining=0,runtime_tested=False,
        note='Pattern and structural checks support the reviewed edits; unreviewed prose remains draft.')
    (ROOT/f'08_qa/audit/{args.revision}_integrity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
if __name__=='__main__':main()
