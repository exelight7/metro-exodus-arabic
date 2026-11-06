import json, pathlib, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
BASE = pathlib.Path(__file__).resolve().parent
ROWS = [json.loads(s) for s in (BASE/'input.jsonl').read_text(encoding='utf-8').splitlines()]
if sys.argv[1] == 'read':
    start, count = map(int, sys.argv[2:4])
    for i in range(start, min(start+count, len(ROWS))):
        r=ROWS[i]
        print(f"[{i}] {r['id']}\nEN {r['source']}\nAR {r['target']}")
elif sys.argv[1] == 'amend':
    amendments=json.loads((BASE/sys.argv[2]).read_text(encoding='utf-8-sig'))
    records=[json.loads(s) for s in (BASE/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
    for k,d in amendments.items():
        i=int(k); assert 0<=i<len(records)
        r=ROWS[i]; assert records[i]['id']==r['id']
        assert d['decision'] in ('keep','change','needs_context','nontranslatable')
        if d['decision']=='change': assert d['target'] and d['target']!=r['target']
        else: assert 'target' not in d
        records[i]={'id':r['id'],'row':r['row'],**d}
    (BASE/'decisions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    progress=json.loads((BASE/'progress.json').read_text(encoding='utf-8'))
    progress['counts']=dict(collections.Counter(r['decision'] for r in records))
    (BASE/'progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(progress,ensure_ascii=False))
elif sys.argv[1] == 'record':
    batch=json.loads((BASE/sys.argv[2]).read_text(encoding='utf-8-sig'))
    progress=json.loads((BASE/'progress.json').read_text(encoding='utf-8'))
    assert batch['start']==progress['next_index']
    start,end=batch['start'],batch['end']
    assert 0<=start<end<=len(ROWS)
    special=batch.get('decisions',{})
    assert all(start<=int(k)<end for k in special)
    records=[]
    for i in range(start,end):
        r=ROWS[i]; d=special.get(str(i), {'decision':'keep','reason':'المعنى والصياغة مناسبان للأصل والسياق المجاور.'})
        assert d['decision'] in ('keep','change','needs_context','nontranslatable')
        out={'id':r['id'],'row':r['row'],**d}
        if d['decision']=='change':
            assert d['target'] and d['target']!=r['target']
        else:
            assert 'target' not in d
        records.append(out)
    with (BASE/'decisions.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        for r in records: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    all_records=[json.loads(s) for s in (BASE/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(all_records)==end
    counts=dict(collections.Counter(r['decision'] for r in all_records))
    progress.update(reviewed=end,next_index=end,complete=end==len(ROWS),counts=counts,last_batch=sys.argv[2])
    (BASE/'progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(progress,ensure_ascii=False))
