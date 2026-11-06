"""Verify recorded review coverage, tokens, source identity and rebuilt resources."""
from pathlib import Path
import csv,collections,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive,LNG
from translation_terms import normalize_terms
from arabic_spelling import correct_spelling
from input_spacing import normalize_input_spacing
def main():
 def table(p):
  with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 before=table(ROOT/'03_translation/review/full_language_r1/baseline.csv');after=table(ROOT/'03_translation/tables/game.csv')
 changes=json.loads((ROOT/'03_translation/full_language_r1_context.json').read_text(encoding='utf8'))
 assert len(before)==len(after)==38221
 tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
 for a,b in zip(before,after):
  assert all(a[k]==b[k] for k in a if k not in ['target','status']),b['id']
  assert b['target']==changes.get(b['id'],a['target']),b['id']
  assert collections.Counter(tags.findall(a['target']))==collections.Counter(tags.findall(b['target'])),b['id']
  assert not b['source'].strip() or b['target'].strip(),b['id']
  assert normalize_input_spacing(b['id'],correct_spelling(b['id'],normalize_terms(b['id'],b['source'],b['target'])))==b['target'],b['id']
 old=Archive(ROOT/'07_patch/phases/100_story_context_r4_verified/patch_04.vfx')
 new=Archive(ROOT/'07_patch/phases/100_full_language_r1/patch_04.vfx')
 same=0;changed=[]
 for a,b in zip(old.entries,new.entries):
  assert (a.path,a.flags)==(b.path,b.flags)
  if a.folder or a.pak!=len(old.packages)-1:continue
  if old.read(a)==new.read(b):same+=1
  else:changed.append(a.path)
 assert same==11 and len(changed)==1 and changed[0].endswith('stable_us.lng')
 def lng(p):return LNG(p.read(next(e for e in p.matching() if e.name=='stable_us.lng')))
 x,y=lng(old),lng(new);assert x.chars==y.chars and list(x.texts)==list(y.texts) and len(y.texts)==38223
 actual=sum(x.texts[k]!=y.texts[k] for k in x.texts)
 report=json.loads((ROOT/'08_qa/audit/full_language_r1.json').read_text(encoding='utf8'))
 report.update(normalization_idempotent=True,nontext_assets_preserved=same,runtime_entries=len(y.texts),changed_runtime_entries=actual,game_started=False,live_game_written=False)
 (ROOT/'08_qa/audit/full_language_r1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('PASS:',len(after),'table rows;',len(y.texts),'runtime strings;',same,'nontext assets unchanged;',actual,'runtime strings changed')
if __name__=='__main__':main()
