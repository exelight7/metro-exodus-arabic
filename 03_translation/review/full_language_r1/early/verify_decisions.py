import collections, json, pathlib, re, sys
sys.stdout.reconfigure(encoding='utf-8')
p=pathlib.Path(__file__).parent
rows=[json.loads(s) for s in (p/'input.jsonl').read_text(encoding='utf-8').splitlines()]
ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
issues=[]
for i,d in enumerate(ds):
 r=rows[i]
 if (d['id'],d['row'])!=(r['id'],r['row']): issues.append([i,'identity'])
 if d['decision']!='change': continue
 a=re.findall(r'<[^>]+>',r['source']); z=re.findall(r'<[^>]+>',d['target'])
 if collections.Counter(a)!=collections.Counter(z): issues.append([i,'tags',a,z])
 if re.findall(r'<time=[^>]+>',r['source'])!=re.findall(r'<time=[^>]+>',d['target']): issues.append([i,'timing'])
 if d['target']==r['target'] or not d['target']: issues.append([i,'empty/noop'])
result={'reviewed':len(ds),'counts':dict(collections.Counter(d['decision'] for d in ds)),'issues':issues,'complete':len(ds)==len(rows)}
(p/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
sys.exit(bool(issues))
