"""Closing audit of the current package; never executes the game."""
import csv,json,re,collections
from pathlib import Path
from translation_terms import normalize_terms
from arabic_spelling import correct_spelling
from input_spacing import normalize_input_spacing
from verify_graphics_fonts import package
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    glossary=json.loads((ROOT/'03_translation/settings_glossary.json').read_text(encoding='utf-8'))
    context=json.loads((ROOT/'03_translation/final_review_r1_context.json').read_text(encoding='utf-8'))
    protected=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
    canonical_checked=[];by={r['id']:r for r in rows}
    for r in rows:
        key=r['id'];source=r['source'];target=r['target']
        assert normalize_input_spacing(key,correct_spelling(key,normalize_terms(key,source,target)))==target,('not normalized',key)
        assert collections.Counter(protected.findall(source))==collections.Counter(protected.findall(target)),('protected format',key)
        if not key.startswith('voices\\') and 'credits' not in key and source.strip() in glossary:
            assert target.strip()==glossary[source.strip()],('canonical setting',key)
            canonical_checked.append(key)
    assert 'الإعدادات > الرسوميات' in by['video_optimal_settings']['target']
    assert 'ما لم يهددوه' in by['general_hint_91_2034']['target']
    assert '<quicksave_date> دقيقة' in by['quick_load_date']['target']
    assert 'اضغط باستمرار' in by['m3_special_ammo_hint_xbox']['target']
    assert 'أي حقيبة الإسعافات' not in ''.join(r['target'] for r in rows)
    bysource=collections.defaultdict(list)
    for r in rows:
        if not r['id'].startswith('voices\\') and 'credits' not in r['id'] and len(r['source'])<135:
            bysource[r['source'].strip()].append(r)
    controls=[g for s,g in bysource.items() if len(g)>1 and re.search(r'hold|toggle|aim|medkit|crouch|filter|melee|reload|quality|vibration|sensitivity|mouse|weapon|language|subtitle',s,re.I)]
    for group in controls:assert len({r['target'].strip() for r in group})==1,('duplicate terminology',[r['id'] for r in group])
    before=package('comprehensive_r3',100);after=package('final_review_r1',100)
    changed=[k for k in after['strings'] if after['strings'][k]!=before['strings'][k]]
    assert set(changed)==set(context),changed
    assert all(before['strings'][k]==after['strings'][k] for k in before['strings'] if k not in context)
    report=dict(revision='final_review_r1',rows_checked=len(rows),whole_pipeline_idempotent=True,all_protected_formats_preserved=True,
        canonical_setting_entries=len(canonical_checked),consistent_duplicate_control_groups=len(controls),confirmed_corrections=len(changed),
        only_explicit_review_ids_changed=True,other_runtime_entries_preserved=len(after['strings'])-len(changed),game_launched=False,runtime_tested=False,
        scope='Closing structural/terminology review and explicit context corrections. Full manual prose review, in-game visual confirmation and orange speaker coloring remain incomplete.')
    (ROOT/'08_qa/audit/final_review_r1_closing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
if __name__=='__main__':main()
