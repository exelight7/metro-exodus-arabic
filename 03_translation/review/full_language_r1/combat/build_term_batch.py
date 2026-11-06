import pathlib,json,sys
p=pathlib.Path(__file__).resolve().parent
s=json.loads((p/sys.argv[1]).read_text(encoding='utf-8-sig'))
rows=[json.loads(x) for x in (p/'input.jsonl').read_text(encoding='utf-8').splitlines()]
cs={}
for i in s.pop('reviewed_term_indices',[]):
 assert s['start']<=i<s['end']
 assert 'drifter' in rows[i]['source'].lower() and 'التائه' in rows[i]['target'],i
 cs[str(i)]={'decision':'change','target':rows[i]['target'].replace('التائه','المتجوّل'),'reason':'توحيد drifter إلى المتجوّل بعد فحص سياق هذا السطر؛ المعنى لا يثبت الضياع.'}
cs.update(s.get('changes',{}));s['changes']=cs
out='batch_'+str(s['start']).zfill(6)+'.json'
(p/out).write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)