"""Merge only recorded bilingual decisions; preserve untouched draft rows."""
from pathlib import Path
import csv,json,re,collections,hashlib
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'03_translation/review/full_language_r1'
def main():
 rows=list(csv.DictReader((B/'baseline.csv').open(encoding='utf-8-sig',newline='')))
 inputs={p:[json.loads(s) for s in (B/p/'input.jsonl').read_text(encoding='utf8').splitlines()] for p in ['root','early','late','combat']}
 decisions={}
 def amend(part,index,target,reason):
  r=inputs[part][index]; ds=decisions[part]; d=next(x for x in ds if x['id']==r['id'])
  d.update(decision='change',target=target,reason=reason)
 for part,items in inputs.items():
  ds=[json.loads(s) for s in (B/part/'decisions.jsonl').read_text(encoding='utf8').splitlines()]
  assert len(ds)==json.loads((B/part/'progress.json').read_text())['reviewed']
  assert [(d['id'],d['row']) for d in ds]==[(r['id'],r['row']) for r in items[:len(ds)]]
  decisions[part]=ds
 amend('root',3892,'أسلحة الرمي المستخدمة','حُسم Fast drops used بالروسي المحلي: Использовано метательного оружия.')
 for n in [3505,3506]:
  d=next(d for d in decisions['root'] if d['id']==inputs['root'][n]['id'])
  amend('root',n,d.get('target',inputs['root'][n]['target']).replace('ستاليون','الفحل'),'توحيد Stallion مع اسم السلاح الفحل في العتاد.')
 for n,old,new in [(3953,'باغتتني المتحولات اللعينة!','باغتني المتحولون اللعينون!'),(3957,'الحمد لله أن معنا أسلحة','لحسن الحظ أن معنا أسلحة'),(4007,'وكانوا أضيع من أن يتحدوا لانشغالهم بقتال بعضهم بعضًا.','وكانوا منشغلين بقتال بعضهم بعضًا فلم يحاولوا الاتحاد أصلًا.'),(4007,'لكن تحركهم كان أضعف وأفوت من أن ينفع','لكن تحركهم جاء ضعيفًا ومتأخرًا')]:
  d=next(d for d in decisions['root'] if d['id']==inputs['root'][n]['id'])
  if old in d['target']:amend('root',n,d['target'].replace(old,new),d['reason']+' تدقيق صياغة نهائي مع حفظ المعنى.')
  else:assert new in d['target'],(n,old)
 # The local Russian originals resolve two previously flagged idioms.
 for part,key,new,why in [
 ('late','voices\\m3_09_summer\\sum_120_radio_03_7','أظن أن أحمق ما وصل إلى هناك فعلًا وكسر الأسطوانة في النهاية! هاها!','الروسي пластинку эту сломал يحسم كسر أسطوانة التسجيل لا تحطيم رقم قياسي.'),
 ('late','voices\\m3_12_valley\\val_002_lineinthesand_01_02','<ffx:anger>هذه أرض إخوة الساحل! <ffx:smile>خطوة أخرى، وسنعبث بك كما نشاء! <ffx:neutral>','الروسي мы с тобой поиграем يحسم تهديد العبث بالدخيل لا تشغيل جهاز.'),
 ('combat','voices\\universal_m3\\factions\\bandit_2\\car\\carseen_02','مهلًا، ذلك اللعين يقود السيارة على نحو مذهل!','Like nobody’s business تعجب من شدة الفعل، دون تعيين السرعة أو المهارة بقرينة غير موجودة؛ إزالة النفي الحرفي عن شأن الآخرين.')]:
  n=next(n for n,r in enumerate(inputs[part]) if r['id']==key);amend(part,n,new,why)
 d=next(d for d in decisions['root'] if d['id']=='bino_zoom')
 d['target']=d['target'].replace('<wpn_fire>،','<wpn_fire> ،')
 tags=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
 changed={};issues=[];coverage={};seen=set();tag_diffs=[]
 for part,ds in decisions.items():
  for d in ds:
   assert d['id'] not in seen;seen.add(d['id']);r=rows[d['row']];assert r['id']==d['id']
   if d['decision']=='change':
    t=d['target']; assert t.strip() and t!=r['target'],d['id']
    if collections.Counter(tags.findall(r['target']))!=collections.Counter(tags.findall(t)):
     tag_diffs.append({'id':r['id'],'old':tags.findall(r['target']),'new':tags.findall(t),'source':tags.findall(r['source'])})
    r['target']=t;changed[r['id']]=t
   if d['decision'] in ['keep','change']:r['status']='reviewed'
   if d['decision']=='needs_context':issues.append(d)
  coverage[part]={'reviewed':len(ds),'assigned':len(inputs[part]),'counts':dict(collections.Counter(d['decision'] for d in ds))}
  (B/part/'decisions.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf8')
 (B/'tag_diffs.json').write_text(json.dumps(tag_diffs,ensure_ascii=False,indent=2),encoding='utf8')
 if tag_diffs:raise ValueError('Inspect protected-token differences before merge: '+str(len(tag_diffs)))
 dest=ROOT/'03_translation/tables/game.csv'
 if hashlib.sha256(dest.read_bytes()).hexdigest()!=hashlib.sha256((B/'baseline.csv').read_bytes()).hexdigest():
  old_context=json.loads((ROOT/'03_translation/full_language_r1_context.json').read_text(encoding='utf8'))
  current=list(csv.DictReader(dest.open(encoding='utf-8-sig',newline='')))
  baseline=list(csv.DictReader((B/'baseline.csv').open(encoding='utf-8-sig',newline='')))
  assert len(current)==len(baseline)
  for a,b in zip(baseline,current):
   assert all(a[k]==b[k] for k in a if k not in ['target','status'])
   assert b['target']==old_context.get(a['id'],a['target']),'Unrecorded edit: '+a['id']
 with dest.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (ROOT/'03_translation/full_language_r1_context.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 report={'revision':'full_language_r1','table_rows':len(rows),'reviewed_rows':len(seen),'changed_rows':len(changed),'unreviewed_rows':len(rows)-len(seen),'full_manual_game_review':False,'coverage':coverage,'needs_context':issues,'protected_tokens_preserved':True,'sources_ids_order_preserved':True,'scope_change':'User requested light finishing and publishing all project files on 2026-11-06; stopped at persisted checkpoints.','game_started':False,'live_game_written':False}
 (ROOT/'08_qa/audit/full_language_r1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['coverage','needs_context']},ensure_ascii=False));print('Needs context:',len(issues))
if __name__=='__main__':main()
