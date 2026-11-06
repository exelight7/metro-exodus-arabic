import pathlib,json
p=pathlib.Path('WORKSPACE/MetroExodus_AR/03_translation/review/full_language_r1/combat')
ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
t='الوثني مختبئ أيها الإخوة! فلا نخشَ غضبه، ولننقذ روحه بتخليصها من جسده الآثم!'
ds[7990]['target']=t
(p/'decisions.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf-8')
f=p/'batch_007760.json';b=json.loads(f.read_text(encoding='utf-8'));b['changes']['7990']=t;f.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Corrected negation in 7990; counts',__import__('collections').Counter(d['decision'] for d in ds))