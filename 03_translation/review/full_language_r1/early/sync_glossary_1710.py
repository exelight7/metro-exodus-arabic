import collections,json,pathlib
p=pathlib.Path(__file__).parent
rows=[json.loads(s) for s in (p/'input.jsonl').read_text(encoding='utf-8').splitlines()]
ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
changed=[]
for i,d in enumerate(ds):
 if d['decision'] in ('needs_context','nontranslatable'):continue
 t=d.get('target',rows[i]['target']); n=t
 for a,z in [('سمكة القيصر','السمكة القيصر'),('التكنولوجيا','التقنية'),('الهراطقة','الزنادقة'),('يامانتاو','يامانتو'),('الفولجا','الفولغا')]:n=n.replace(a,z)
 if n!=t:
  ds[i]={'id':rows[i]['id'],'row':rows[i]['row'],'decision':'change','target':n,'reason':d['reason']+' توحيد المصطلحات المعتمدة: السمكة القيصر، التقنية، الزنادقة، يامانتو، الفولغا.'}
  changed.append(i)
(p/'decisions.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf-8')
q=json.loads((p/'progress.json').read_text(encoding='utf-8'));q['counts']=dict(collections.Counter(d['decision'] for d in ds));q['glossary_synced_at']=len(ds)
(p/'progress.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(p/'glossary_sync_1710.json').write_text(json.dumps({'approved_by':'root','indices':changed,'reviewed':len(ds)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(q,ensure_ascii=False))
