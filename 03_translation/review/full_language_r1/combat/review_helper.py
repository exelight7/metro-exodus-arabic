import json, pathlib, sys, re, os, itertools

ROOT = pathlib.Path(__file__).resolve().parent
ROWS = [json.loads(s) for s in (ROOT/'input.jsonl').read_text(encoding='utf-8').splitlines()]

def show(start, count):
    ix = range(start, min(start+count, len(ROWS)))
    for category, indices in itertools.groupby(ix, key=lambda i: ROWS[i]['id'].rsplit(chr(92),1)[0]):
        indices = list(indices)
        prefix = os.path.commonprefix([ROWS[i]['id'] for i in indices])
        if len(indices)==1: prefix=category+chr(92)
        print('ID prefix: '+prefix)
        captions = {}
        for i in indices:
            r = ROWS[i]
            if r['source'].startswith('ENEMY:'):
                captions.setdefault((r['source'],r['target']),[]).append(f"{i}:{r['id'][len(prefix):]}")
            else:
                print(f"{i} [{r['id'][len(prefix):]}] {r['source']} || {r['target']}")
        for (src,tgt), ids in captions.items():
            print('CAPTION '+src+' || '+tgt)
            print('ALL CONTEXT IDS '+', '.join(ids))

def record():
    batch = json.loads((ROOT/(sys.argv[2] if len(sys.argv)>2 else 'batch.json')).read_text(encoding='utf-8-sig'))
    progress = json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
    start, end = batch['start'], batch['end']
    assert start == progress['next_index'], (start, progress)
    changes = batch.get('changes', {})
    decisions = []
    for i in range(start, end):
        r = ROWS[i]
        d = dict(id=r['id'],row=r['row'],decision='keep',reason='المعنى والصياغة ملائمان للسياق.')
        c = changes.get(str(i))
        if c is None:
            c = batch.get('common',{}).get(r['source'])
        if isinstance(c,str):
            c = dict(decision='change',target=c,reason=batch.get('reason','تصحيح المعنى أو الصياغة أو المطابقة بحسب الأصل وسياق المعرّف.'))
        if c:
            d.update(c)
            if d['decision'] == 'change':
                token = r'<[^>]+>|\{[^}]+\}|%\w+'
                assert sorted(re.findall(token, r['target'])) == sorted(re.findall(token, d['target'])), (i, 'protected tokens')
                assert d['target'] != r['target'], (i, 'unchanged change')
            else:
                assert 'target' not in d
        decisions.append(d)
    with (ROOT/'decisions.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        for d in decisions:
            f.write(json.dumps(d,ensure_ascii=False)+'\n')
    progress.update(reviewed=end,next_index=end,complete=end==len(ROWS))
    (ROOT/'progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(reviewed=end,changes=sum(d['decision']=='change' for d in decisions),needs_context=sum(d['decision']=='needs_context' for d in decisions)),ensure_ascii=False))

if sys.argv[1] == 'show': show(int(sys.argv[2]),int(sys.argv[3]))
elif sys.argv[1] == 'record': record()
