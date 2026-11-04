"""Four cumulative text milestones, measured against visible English entries."""
import csv,json,re,math,shutil,sys,hashlib,argparse
from pathlib import Path
from metro_lng import parse,build
from metro_fonts import read_fonts
from package_patch import build_package

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/vendor/game-arabization'))
from ar_shape import Shaper

def visible(s):return re.sub(r'<[^>]+>','',s)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='');parser.add_argument('--phase',type=int,choices=[25,50,75,100]);args=parser.parse_args()
    assert not args.revision or re.fullmatch('[a-z0-9_]+',args.revision)
    suffix='_'+args.revision if args.revision else ''
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    original=(ROOT/'02_extracted/steam_local/patch_04/content/localization/stable_us.lng').read_bytes()
    old,pairs=parse(original)
    chars,_=parse((ROOT/'06_build/stage/content/localization/stable_us.lng').read_bytes())
    eligible=[r for r in rows if re.search('[A-Za-z]',visible(r['source']))]
    by_id_path=ROOT/'03_translation/overrides_by_id.json'
    by_id=json.loads(by_id_path.read_text(encoding='utf-8')) if by_id_path.exists() else {}
    retained_english={k:v for k,v in by_id.items() if re.search('[A-Za-z]',v) and not re.search('[\u0600-\u06ff]',v)}
    available=[r for r in eligible if r['status'] in ('draft','reviewed') and re.search('[\u0600-\u06ff]',visible(r['target']))]
    def priority(r):
        key=r['id']
        # Interface / tutorials first, then story dialogue, then the credits.
        return (2 if 'credits' in key else 1 if key.startswith('voices\\') else 0,key)
    available.sort(key=priority)
    assert len(rows)==len(pairs)
    assert all(r['id']==k and r['source']==v for r,(k,v) in zip(rows,pairs))
    fonts=read_fonts((ROOT/'06_build/stage/content/scripts/fonts_us.bin').read_bytes())
    assert all(len(f['glyphs'])==len(chars) for f in fonts if len(f['glyphs'])!=256)
    shaper=Shaper(mode='visual',harakat='strip',normalize_persian=True,newline_tokens=['\n','<br>'])
    tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
    from collections import Counter
    overview=dict(basis='visible English text entry count; not all game assets or reviewed quality',total_text_entries=len(eligible),available_arabic_entries=len(available),runtime_tested=False,phases=[])
    for percent in (25,50,75,100):
        if args.phase and args.phase!=percent:continue
        required=math.ceil(len(eligible)*percent/100)
        if len(available)<required:
            overview['phases'].append(dict(percent=percent,state='blocked',required=required,available=len(available),shortfall=required-len(available)))
            continue
        chosen=available[:required];ids={r['id'] for r in chosen};targets={r['id']:r['target'] for r in chosen}
        output=[]
        for key,source in pairs:
            if key in ids:
                target=targets[key]
                assert Counter(tags.findall(source))==Counter(tags.findall(target)),key
                text=shaper.process(target)
                assert all(c in chars for c in text),key
            elif key in retained_english:text=retained_english[key]
            else:text=source
            output.append((key,text))
        data=build(original,chars,output);assert parse(data)==(chars,output)
        assert sum(v!=source for (k,v),(_,source) in zip(output,pairs) if k not in retained_english)==required
        stage=ROOT/f'06_build/phases/{percent}{suffix}'
        shutil.copytree(ROOT/'06_build/stage',stage,dirs_exist_ok=True)
        (stage/'content/localization/stable_us.lng').write_bytes(data)
        patch=ROOT/f'07_patch/phases/{percent}{suffix}'
        extra=dict(phase=percent,phase_status='private_machine_draft',coverage_basis=overview['basis'],
            total_text_entries=len(eligible),arabic_entries=required,english_entries=len(eligible)-required,
            source_untranslated_entries=sum(r['status']=='todo' for r in rows),untranslated_entries=len(eligible)-required,
            revision=args.revision,retained_english_technologies=retained_english)
        build_package(stage,patch,f'metro_arabic_{percent}{suffix}.vfs0',extra)
        with (patch/'selected_ids.json').open('w',encoding='utf-8') as f:json.dump([r['id'] for r in chosen],f)
        overview['phases'].append(dict(percent=percent,state='built_verified',arabic_entries=required,actual_percent=required/len(eligible)*100,patch=str(patch)))
        print('PHASE',percent,'Arabic entries',required,'/',len(eligible),flush=True)
    (ROOT/f'00_admin/phases{suffix}.json').write_text(json.dumps(overview,indent=2))
    print(json.dumps(overview,indent=2))
if __name__=='__main__':main()
