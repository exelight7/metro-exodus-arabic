"""Resumable public game-text translation drafts; no runtime/game execution."""
import concurrent.futures as cf
import csv, json, re, time, urllib.parse, urllib.request, urllib.error, threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TABLE=ROOT/'03_translation/tables/game.csv'
CACHE=ROOT/'03_translation/tm/google_draft.jsonl'
TOK=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]|\[[^\]\n]{1,60}\]')
STOP=threading.Event()

def translate_batch(batch):
    texts=[]; protected=[]
    for source in batch:
        tokens=[]
        def sub(m):
            tokens.append(m.group()); return f' ZXQ{len(tokens)-1}QXZ '
        texts.append(TOK.sub(sub,source).replace('\n',' ZXQNLQXZ '))
        protected.append(tokens)
    q='\n'.join(texts)
    url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl='en',tl='ar',dt='t',q=q))
    for attempt in range(5):
        try:
            if STOP.is_set():raise RuntimeError('Translation service paused; saved drafts are retained')
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            result=json.load(urllib.request.urlopen(req,timeout=45))
            translated=''.join(s[0] for s in result[0] if s[0]).split('\n')
            if len(translated)!=len(batch):
                if len(batch)==1: translated=['\n'.join(translated)]
                else:
                    mid=len(batch)//2
                    return translate_batch(batch[:mid])+translate_batch(batch[mid:])
            out=[]
            for source,target,tokens in zip(batch,translated,protected):
                target=re.sub(r'\s*ZXQNLQXZ\s*','\n',target,flags=re.I)
                for i,token in enumerate(tokens):
                    pattern=rf'\s*ZXQ\s*{i}\s*QXZ\s*'
                    if len(re.findall(pattern,target,re.I))!=1: raise ValueError('placeholder mismatch')
                    target=re.sub(pattern,lambda m:token,target,flags=re.I)
                if re.search(r'ZXQ|QXZ',target,re.I): raise ValueError('placeholder residue')
                out.append((source,target.strip()))
            return out
        except Exception as error:
            if isinstance(error,urllib.error.HTTPError) and error.code in (401,403,429):
                STOP.set();raise
            if STOP.is_set():raise
            if attempt==1 and len(batch)==1 and (tokens or '\n' in batch[0]):
                parts=re.split('('+TOK.pattern+'|\\n)',batch[0]); result=[]
                for part in parts:
                    if not part.strip() or TOK.fullmatch(part) or part=='\n':result.append(part)
                    else:result.append(translate_batch([part])[0][1])
                return [(batch[0],''.join(result))]
            if attempt==2:
                if len(batch)>1:
                    mid=len(batch)//2
                    return translate_batch(batch[:mid])+translate_batch(batch[mid:])
                raise
            time.sleep(2+attempt*3)

def main():
    rows=list(csv.DictReader(TABLE.open(encoding='utf-8-sig')))
    cache={}
    if CACHE.exists():
        for line in CACHE.read_text(encoding='utf-8').splitlines():
            item=json.loads(line); cache[item['source']]=item['target']
    sources=list(dict.fromkeys(r['source'] for r in rows if r['source'].strip() and re.search('[A-Za-z]',r['source'])))
    todo=[s for s in sources if s not in cache]
    # Menus and short repeated phrases first, retaining all source rows.
    todo.sort(key=len)
    batches=[]; batch=[]; size=0
    for s in todo:
        if batch and (size+len(s)>3300 or len(batch)>=35): batches.append(batch);batch=[];size=0
        batch.append(s);size+=len(s)+1
    if batch:batches.append(batch)
    print(f'unique={len(sources)} cached={len(cache)} batches={len(batches)}',flush=True)
    def save():
        for r in rows:
            if r['status']=='reviewed': continue
            if r['source'] in cache: r.update(target=cache[r['source']],status='draft',translation_origin='machine_draft')
            elif not re.search('[A-Za-z]',r['source']): r.update(target=r['source'],status='skip',translation_origin='preserved')
        tmp=TABLE.with_suffix('.writing.csv')
        with tmp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
        tmp.replace(TABLE)
    errors=0
    with CACHE.open('a',encoding='utf-8') as log, cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(translate_batch,b):i for i,b in enumerate(batches)}
        for done,future in enumerate(cf.as_completed(futures),1):
            try:
                for source,target in future.result():
                    cache[source]=target;log.write(json.dumps(dict(source=source,target=target),ensure_ascii=False)+'\n')
                log.flush()
            except Exception as e:
                errors+=1; print('ERROR',futures[future],str(e),flush=True)
                if STOP.is_set():
                    for pending in futures:pending.cancel()
                    save();break
            if done%10==0 or done==len(futures):
                save();print(f'batches={done}/{len(futures)} cached={len(cache)} errors={errors}',flush=True)
    save()
if __name__=='__main__':main()
