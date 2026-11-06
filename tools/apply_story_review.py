"""Apply the explicit story contexts, preserving all unrelated authoring rows."""
import collections,csv,hashlib,json,re,shutil,sys
from pathlib import Path
from arabic_spelling import correct_spelling
ROOT=Path(__file__).resolve().parents[1]
def main():
 table=ROOT/'03_translation/tables/game.csv';backup=ROOT/'03_translation/review/story_context_r1_baseline.csv'
 if backup.exists():
  assert '--refresh' in sys.argv,'Baseline already exists; inspect before applying again'
  previous=json.loads((ROOT/'08_qa/audit/story_context_r1.json').read_text(encoding='utf-8'))
  assert hashlib.sha256(table.read_bytes()).hexdigest()==previous['target_sha256']
 else:shutil.copy2(table,backup)
 edits=json.loads((ROOT/'03_translation/story_context_r1.json').read_text(encoding='utf-8'))
 with backup.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]');changes=[]
 for row in rows:
  if row['id'] not in edits:continue
  target=correct_spelling(row['id'],edits[row['id']])
  assert collections.Counter(tags.findall(row['target']))==collections.Counter(tags.findall(target)),row['id']
  assert target!=row['target'],row['id']
  changes.append(dict(id=row['id'],source=row['source'],before=row['target'],after=target,old_status=row['status']))
  row['target']=target;row['status']='reviewed'
 assert len(changes)==len(edits)
 with table.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
 report=dict(revision='story_context_r1',rows_scanned=len(rows),contexts_manually_corrected=len(changes),
             previous_revision='spelling_full_r1',all_other_rows_preserved=True,full_manual_game_review=False,
             original_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),target_sha256=hashlib.sha256(table.read_bytes()).hexdigest(),
             game_launched=False,installed=False,published=False,changes=changes)
 (ROOT/'08_qa/audit/story_context_r1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
if __name__=='__main__':main()
