import collections,json,pathlib,re,sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT=pathlib.Path(__file__).resolve().parent
ROWS=[json.loads(x) for x in (ROOT/'input.jsonl').read_text(encoding='utf-8').splitlines()]
def show(start,end):
    for i in range(start,end):
        x=ROWS[i]
        print(f"{i} {x['id']}\nEN {x['source']}\nAR {x['target']}")
def tagged(i,body,reason='تصحيح المعنى والنحو والصياغة بحسب سياق المشهد.'):
    tags=re.findall(r'<[^>]*>',ROWS[i]['target'])
    parts=body.split('|')
    assert len(parts)==len(tags)-1,(i,len(parts),len(tags))
    return (''.join(t+p for t,p in zip(tags[:-1],parts))+tags[-1],reason)
def tagged_open(i,body,reason='تصحيح المعنى والنحو والصياغة بحسب سياق المشهد.'):
    tags=re.findall(r'<[^>]*>',ROWS[i]['target']);parts=body.split('|')
    assert len(parts)==len(tags),(i,len(parts),len(tags))
    return (''.join(t+p for t,p in zip(tags,parts)),reason)
def commit(start,end,changes,contexts=None,nontranslatable=None):
    contexts=contexts or {};nontranslatable=nontranslatable or set()
    p=ROOT/'decisions.jsonl'
    old=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []
    assert len(old)==start,(len(old),start)
    tags=lambda s: re.findall(r'<[^>]*>',s)
    result=[]
    for i in range(start,end):
        x=ROWS[i];r={'id':x['id'],'row':x['row'],'decision':'keep','reason':'المعنى والصياغة مناسبان للسياق.'}
        if i in changes:
            target,reason=changes[i]
            assert tags(target)==tags(x['target']),(i,tags(target),tags(x['target']))
            assert target!=x['target'],i
            r.update(decision='change',target=target,reason=reason)
        elif i in contexts:r.update(decision='needs_context',reason=contexts[i])
        elif i in nontranslatable:r.update(decision='nontranslatable',reason='إرشاد أداء أو وسم محمي، وليس حوارًا معروضًا للترجمة.')
        result.append(r)
    assert set(changes).issubset(range(start,end))
    with p.open('a',encoding='utf-8',newline='\n') as f:
        for r in result:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    counts=collections.Counter(r['decision'] for r in old+result)
    (ROOT/'progress.json').write_text(json.dumps({'partition':'late','assigned':len(ROWS),'reviewed':end,'next_index':end,'complete':end==len(ROWS),'counts':dict(counts)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(end,dict(counts))
def compact(start,end):
    group=None
    clean=lambda s:re.sub(r'<ffx:[^>]+>','|',s)
    for i in range(start,end):
        x=ROWS[i];g,n=x['id'].rsplit('\\',1)
        if g!=group:print('GROUP '+g);group=g
        print(f"{i} {n}\nE {clean(x['source'])}\nA {clean(x['target'])}")
if __name__=='__main__':
    (compact if len(sys.argv)>3 else show)(int(sys.argv[1]),int(sys.argv[2]))
