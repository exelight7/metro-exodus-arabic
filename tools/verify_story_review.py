"""Check story-context edits, cumulative spelling fixes and separate patch bytes."""
import collections,csv,json,re,sys
from pathlib import Path
from translation_terms import normalize_terms
from arabic_spelling import correct_spelling
from input_spacing import normalize_input_spacing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive,LNG
def table(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
 before=table(ROOT/'03_translation/review/story_context_r1_baseline.csv');after=table(ROOT/'03_translation/tables/game.csv')
 edits=json.loads((ROOT/'03_translation/story_context_r1.json').read_text(encoding='utf-8'))
 tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
 assert len(before)==len(after)==38221
 for a,b in zip(before,after):
  assert {k:v for k,v in a.items() if k not in ['target','status']}=={k:v for k,v in b.items() if k not in ['target','status']}
  assert (a['target']!=b['target'])==(b['id'] in edits)
  assert b['status']==('reviewed' if b['id'] in edits else a['status'])
  assert collections.Counter(tags.findall(a['target']))==collections.Counter(tags.findall(b['target']))
  assert normalize_input_spacing(b['id'],correct_spelling(b['id'],normalize_terms(b['id'],b['source'],b['target'])))==b['target'],b['id']
 # Distinguish literal radio commands from invitations to enter a room.
 by={r['id']:r['target'] for r in after}
 assert 'ادخل' not in by['voices\\m3_06_bridge\\bri_011_terminalradio_04']
 assert 'تعال' in by['voices\\m3_13_dead_city\\nvs_002_katyartyomtalk_01_01']
 assert 'التنظيم' in by['m3_m10_ym_defence_note']
 assert 'التنظيم' in by['voices\\m3_ending\\end_glukh_02_21']
 assert 'توقعت' in by['m3_loader_diary_valley_06_02_wolfbanditagain_killed'] or 'أنتظر' in by['m3_loader_diary_valley_06_02_wolfbanditagain_killed']
 previous=Archive(ROOT/'07_patch/phases/100_spelling_full_r1_verified/patch_04.vfx')
 current=Archive(ROOT/'07_patch/phases/100_story_context_r1_verified/patch_04.vfx')
 changes=[];same=0
 for a,b in zip(previous.entries,current.entries):
  assert a.path==b.path and a.flags==b.flags
  if a.folder:continue
  if a.pak==len(previous.packages)-1:
   if previous.read(a)!=current.read(b):changes.append(a.path)
   else:same+=1
 assert len(changes)==1 and changes[0].endswith('stable_us.lng')
 def lng(archive):return LNG(archive.read(next(e for e in archive.matching() if e.name=='stable_us.lng')))
 old,new=lng(previous),lng(current)
 assert old.chars==new.chars and list(old.texts)==list(new.texts)
 actual={k for k in old.texts if old.texts[k]!=new.texts[k]};assert actual==set(edits),(actual^set(edits))
 report=dict(revision='story_context_r1',rows_checked=len(after),runtime_entries=len(new.texts),
             individually_reviewed_context_corrections=len(edits),unchanged_runtime_entries=len(new.texts)-len(actual),
             previous_spelling_fixes_preserved=True,nontext_assets_preserved=same,
             ids_sources_placeholders_and_timings_preserved=True,normalization_idempotent=True,
             invitation_vs_radio_distinction_checked=True,branch_specific_notes_kept_separate=True,
             full_manual_game_review=False,installed=False,published=False,game_launched=False,live_game_written=False)
 (ROOT/'08_qa/audit/story_context_r1_verified.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
