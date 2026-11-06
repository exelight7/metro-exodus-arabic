"""Whole-table spelling regression and isolated patch comparison; read-only."""
from pathlib import Path
import collections,csv,hashlib,json,re,sys
from arabic_spelling import correct_spelling
from translation_terms import normalize_terms
from input_spacing import normalize_input_spacing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive,LNG

def read_table(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

def main():
    before=read_table(ROOT/'03_translation/review/spelling_full_baseline.csv')
    after=read_table(ROOT/'03_translation/tables/game.csv')
    receipt=json.loads((ROOT/'08_qa/audit/spelling_full_r1.json').read_text(encoding='utf-8'))
    changed={r['id'] for r in receipt['changes']};assert len(before)==len(after)==38221
    protected=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
    for a,b in zip(before,after):
        assert {k:v for k,v in a.items() if k!='target'}=={k:v for k,v in b.items() if k!='target'}
        assert (a['target']!=b['target'])==(b['id'] in changed)
        assert collections.Counter(protected.findall(a['target']))==collections.Counter(protected.findall(b['target']))
        assert normalize_input_spacing(b['id'],correct_spelling(b['id'],normalize_terms(b['id'],b['source'],b['target'])))==b['target'],b['id']
        assert not b['source'].strip() or b['target'].strip()
    for row in json.loads((ROOT/'03_translation/supplemental_entries.json').read_text(encoding='utf-8')):
        assert correct_spelling(row['id'],row['target'])==row['target']
    old=Archive(ROOT/'07_patch/phases/100_final_review_r1/patch_04.vfx')
    new=Archive(ROOT/'07_patch/phases/100_spelling_full_r1_verified/patch_04.vfx')
    assets_changed=[];untouched=0
    for a,b in zip(old.entries,new.entries):
        assert a.path==b.path and a.flags==b.flags
        if a.folder:continue
        if a.pak==len(old.packages)-1:
            if old.read(a)!=new.read(b):assets_changed.append(a.path)
            else:untouched+=1
    assert len(assets_changed)==1 and assets_changed[0].replace('\\','/').endswith('localization/stable_us.lng')
    a=next(e for e in old.matching() if e.name=='stable_us.lng')
    b=next(e for e in new.matching() if e.name=='stable_us.lng')
    oldtext=LNG(old.read(a));newtext=LNG(new.read(b))
    actual={k for k in oldtext.texts if oldtext.texts[k]!=newtext.texts[k]}
    assert actual==changed and list(oldtext.texts)==list(newtext.texts)
    assert oldtext.chars==newtext.chars
    report=dict(rows_checked=38221,runtime_entries_checked=len(newtext.texts),confirmed_corrections=len(changed),
                other_runtime_entries_unchanged=len(newtext.texts)-len(changed),nontext_assets_preserved=untouched,
                ids_sources_statuses_and_placeholders_preserved=True,normalization_idempotent=True,
                font_character_table_preserved=True,full_manual_prose_review=False,
                game_launched=False,live_game_written=False,installed=False)
    (ROOT/'08_qa/audit/spelling_full_r1_verified.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
