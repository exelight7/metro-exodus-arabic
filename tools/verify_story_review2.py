"""Verify the second semantic review and keep all unrelated resources intact."""
from pathlib import Path
import collections,csv,json,re,sys
from translation_terms import normalize_terms
from arabic_spelling import correct_spelling
from input_spacing import normalize_input_spacing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive,LNG
def table(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
 before=table(ROOT/'03_translation/review/story_context_r2_baseline.csv');after=table(ROOT/'03_translation/tables/game.csv')
 manual=json.loads((ROOT/'03_translation/story_context_r2.json').read_text(encoding='utf-8'))
 aliases=json.loads((ROOT/'03_translation/story_names_r2.json').read_text(encoding='utf-8'))
 expected=set(manual)|set(aliases);assert not set(manual)&set(aliases)
 tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
 assert len(before)==len(after)==38221
 for a,b in zip(before,after):
  assert {k:v for k,v in a.items() if k not in ['target','status']}=={k:v for k,v in b.items() if k not in ['target','status']}
  assert (a['target']!=b['target'])==(b['id'] in expected)
  assert b['status']==('reviewed' if b['id'] in manual else a['status'])
  assert collections.Counter(tags.findall(a['target']))==collections.Counter(tags.findall(b['target']))
  assert normalize_input_spacing(b['id'],correct_spelling(b['id'],normalize_terms(b['id'],b['source'],b['target'])))==b['target'],b['id']
  if b['id'] in aliases:
   assert re.sub(r'(?<![\u0621-\u064a])جيول(?![\u0621-\u064a])','غيول',a['target'])==b['target']
   assert re.search(r'\bGiul\b',b['source'],re.I)
  if 'credits' not in b['id'] and re.search(r'\bGiul\b',b['source'],re.I):
   assert not re.search(r'(?<![\u0621-\u064a])جيول(?![\u0621-\u064a])',b['target'])
 previous=Archive(ROOT/'07_patch/phases/100_story_context_r1_verified/patch_04.vfx')
 current=Archive(ROOT/'07_patch/phases/100_story_context_r2_verified/patch_04.vfx')
 changed_assets=[];same=0
 for a,b in zip(previous.entries,current.entries):
  assert a.path==b.path and a.flags==b.flags
  if a.folder:continue
  if a.pak==len(previous.packages)-1:
   if previous.read(a)!=current.read(b):changed_assets.append(a.path)
   else:same+=1
 assert len(changed_assets)==1 and changed_assets[0].endswith('stable_us.lng')
 def lng(archive):return LNG(archive.read(next(e for e in archive.matching() if e.name=='stable_us.lng')))
 old,new=lng(previous),lng(current);assert old.chars==new.chars and list(old.texts)==list(new.texts)
 actual={k for k in old.texts if old.texts[k]!=new.texts[k]};assert actual==expected,actual^expected
 prior=set(json.loads((ROOT/'03_translation/story_context_r1.json').read_text(encoding='utf-8')))
 assert not prior&actual,'This round unexpectedly changed a prior reviewed context'
 report=dict(revision='story_context_r2',table_rows_checked=len(after),runtime_entries=len(new.texts),
             individually_reviewed_contexts=len(manual),name_only_consistency_fixes=len(aliases),changed_runtime_entries=len(actual),
             other_runtime_entries_preserved=len(new.texts)-len(actual),previous_74_reviewed_contexts_preserved=True,
             nontext_assets_preserved=same,ids_sources_status_policy_tags_and_timings_verified=True,
             normalization_idempotent=True,full_manual_game_review=False,installed=False,published=False,
             live_game_written=False,game_launched=False)
 (ROOT/'08_qa/audit/story_context_r2_verified.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
