import json,pathlib
p=pathlib.Path('WORKSPACE/MetroExodus_AR/03_translation/review/full_language_r1/combat'); f=p/'decisions.jsonl'
ds=[json.loads(s) for s in f.read_text(encoding='utf-8').splitlines()]
ds[4926].update(decision='change',target='يا إلهي، كم أشتهي بعض سمك الأبراميس المدخن الآن... نعم، كانت تلك أيامًا جميلة...',reason='الروسية подлещик ومرجع FAO Fisheries Synopsis 36 يحسمان bream النهري بأنه Abramis brama؛ الاسم النوعي الأبراميس أدق من دنيس البحر، وتحفظ صفة التدخين من الإنجليزية.')
f.write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf-8')
for f in p.glob('batch*.json'):
 b=json.loads(f.read_text(encoding='utf-8-sig'))
 if b['start']<=4926<b['end']:
  b.setdefault('changes',{})['4926']={k:v for k,v in ds[4926].items() if k not in ('id','row')}; f.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('bream resolved')