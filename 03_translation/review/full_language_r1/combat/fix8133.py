import pathlib,json
p=pathlib.Path('WORKSPACE/MetroExodus_AR/03_translation/review/full_language_r1/combat')
ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
t='آه... أيتها السمكة، لِمَ تمتحنينني هكذا...'
ds[8133]['target']=t
(p/'decisions.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf-8')
f=p/'batch_008000.json';b=json.loads(f.read_text(encoding='utf-8'));b['changes']['8133']=t;f.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Corrected explicit interrogative in 8133')