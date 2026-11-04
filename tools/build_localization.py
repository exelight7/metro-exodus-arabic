import csv,json,re,sys,hashlib
from pathlib import Path
from collections import Counter
from metro_lng import parse,build
from build_arabic_fonts import build as build_fonts
from subtitle_layout import GameRenderer
from translation_terms import normalize_terms
from arabic_spelling import correct_spelling
from input_spacing import normalize_input_spacing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/vendor/game-arabization'))
from ar_shape import Shaper

def main():
    source=ROOT/'02_extracted/steam_local/patch_04/content/localization/stable_us.lng'
    original=source.read_bytes();oldchars,pairs=parse(original)
    assert build(original,oldchars,pairs)==original
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    overrides=json.loads((ROOT/'03_translation/overrides.json').read_text(encoding='utf-8'))
    by_id_path=ROOT/'03_translation/overrides_by_id.json'
    by_id=json.loads(by_id_path.read_text(encoding='utf-8')) if by_id_path.exists() else {}
    cache={}
    for line in (ROOT/'03_translation/tm/google_draft.jsonl').read_text(encoding='utf-8').splitlines():
        item=json.loads(line);cache[item['source']]=item['target']
    tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
    issues=[];output=[];renderer=GameRenderer()
    for r,(key,source_text) in zip(rows,pairs):
        assert key==r['id'] and source_text==r['source']
        if key in by_id:
            target=by_id[key];r['status']='reviewed'
        elif source_text in overrides:
            target=overrides[source_text];r['status']='reviewed'
        elif r['status']=='reviewed' and r['target']:
            target=r['target']
        elif source_text in cache:
            target=cache[source_text];r['status']='machine_draft'
        elif not re.search('[A-Za-z]',source_text):
            target=source_text;r['status']='preserved'
        else:
            target=source_text;r['status']='untranslated'
        target=normalize_terms(key,source_text,target)
        target=correct_spelling(key,target)
        target=normalize_input_spacing(key,target)
        # Use plain Arabic logical text as the editable source of truth.
        r['target']=target
        if Counter(tags.findall(source_text))!=Counter(tags.findall(target)):
            issues.append(dict(id=key,error='tag_mismatch'))
        if r['status']=='untranslated':issues.append(dict(id=key,error='untranslated'))
        if key.startswith('voices\\'):
            if re.search(r'\bDuke\b',source_text):target=target.replace('الدوق','ديوك').replace('دوق','ديوك')
            if re.search(r'\bIdiot\b',source_text):target=target.replace('الأحمق','إيديوت')
            r['target']=target
        rendered=renderer.render(key,target)
        output.append((key,rendered))
    supplemental_path=ROOT/'03_translation/supplemental_entries.json'
    supplemental=json.loads(supplemental_path.read_text(encoding='utf-8')) if supplemental_path.exists() else []
    original_keys={k for k,v in pairs}
    for r in supplemental:
        assert r['id'] not in original_keys and r['status']=='reviewed'
        assert Counter(tags.findall(r['source']))==Counter(tags.findall(r['target'])),r['id']
        output.append((r['id'],renderer.render(r['id'],r['target'])))
    chars=oldchars+''.join(sorted(set(''.join(v for k,v in output))-set(oldchars)))
    out=build(original,chars,output)
    assert parse(out)==(chars,output)
    assert [k for k,v in output[:len(pairs)]]==[k for k,v in pairs]
    assert len({k for k,v in output})==len(output)
    stage=ROOT/'06_build/stage/content/localization';stage.mkdir(parents=True,exist_ok=True)
    (stage/'stable_us.lng').write_bytes(out)
    origin_counts=dict(Counter(r['status'] for r in rows))
    for r in rows:
        r['translation_origin']=r['status']
        r['status']={'machine_draft':'draft','untranslated':'todo','preserved':'skip'}.get(r['status'],r['status'])
    with (ROOT/'03_translation/tables/game.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    report=dict(total=len(rows),runtime_entries=len(output),supplemental_reviewed_entries=len(supplemental),statuses=dict(Counter(r['status'] for r in rows)),origins=origin_counts,original_characters=len(oldchars),built_characters=len(chars),
        roundtrip_original_sha256=hashlib.sha256(original).hexdigest(),built_sha256=hashlib.sha256(out).hexdigest(),
        issues=issues,subtitle_layout=renderer.stats,runtime_tested=False,render_mode='visual_assumed_unverified')
    (ROOT/'08_qa/audit/localization_build.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='issues'}),flush=True)
    if issues and ('--draft' not in sys.argv or any(i['error']!='untranslated' for i in issues)):
        raise ValueError(f'{len(issues)} unresolved text issues; see localization_build.json')
    if '--text-only' not in sys.argv:build_fonts(chars,oldchars)
if __name__=='__main__':main()
