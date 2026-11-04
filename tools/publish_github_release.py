"""Publish only the explicitly authorized repository and reviewed release manifest.

Credentials stay in memory and come from Git Credential Manager or an existing
GitHub token environment variable. Never writes or prints a credential.
"""
from pathlib import Path
import argparse,base64,hashlib,http.client,json,mimetypes,os,re,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[1]
REPO='exelight7/metro-exodus-arabic';TAG='v0.1.0-beta.1'
CHECKOUT=ROOT/'06_build/github_publish';RELEASE=ROOT/'09_release'/TAG

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()

class GitHub:
    def __init__(self):
        self.token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            env=os.environ.copy();env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
            p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,env=env,timeout=30)
            fields=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
            self.token=fields.get('password')
        if not self.token:raise RuntimeError('No existing GitHub authentication available')
    def headers(self):return {'Accept':'application/vnd.github+json','Authorization':'Bearer '+self.token,'X-GitHub-Api-Version':'2026-03-10','User-Agent':'Metro-Exodus-Arabic-Release'}
    def api(self,path,data=None,method=None):
        assert path=='/user' or path.startswith('/repos/'+REPO+'/') or path=='/repos/'+REPO
        body=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
        headers=self.headers()
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request('https://api.github.com'+path,data=body,headers=headers,method=method or ('POST' if data is not None else 'GET'))
        try:
            with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            detail=json.loads(e.read().decode());raise RuntimeError(f'GitHub HTTP {e.code}: {detail.get("message","request failed")}') from None
    def git(self,*args):
        env=os.environ.copy();env['GIT_TERMINAL_PROMPT']='0';env['GCM_INTERACTIVE']='Never'
        # Child-only Git config avoids tokens in command lines, URLs and files.
        env['GIT_CONFIG_COUNT']='1';env['GIT_CONFIG_KEY_0']='http.https://github.com/.extraheader'
        env['GIT_CONFIG_VALUE_0']='Authorization: Basic '+base64.b64encode(('x-access-token:'+self.token).encode()).decode()
        r=subprocess.run(['git','-C',str(CHECKOUT),*args],env=env,text=True,capture_output=True,timeout=180)
        if r.returncode:raise RuntimeError('Git operation failed: '+r.stderr.replace(self.token,'[redacted]')[-1800:])
        return r.stdout.strip()
    def upload(self,release_id,path):
        size=path.stat().st_size;encoded=urllib.parse.urlencode({'name':path.name})
        con=http.client.HTTPSConnection('uploads.github.com',timeout=180)
        headers=self.headers();headers.update({'Content-Type':mimetypes.guess_type(path.name)[0] or 'application/octet-stream','Content-Length':str(size)})
        con.putrequest('POST',f'/repos/{REPO}/releases/{release_id}/assets?{encoded}')
        for k,v in headers.items():con.putheader(k,v)
        con.endheaders();sent=0;last=time.monotonic()
        print('Uploading',path.name,size,flush=True)
        with path.open('rb') as f:
            while b:=f.read(1024*1024):
                con.send(b);sent+=len(b)
                if time.monotonic()-last>12:print('Upload progress',path.name,round(sent/size*100),'%',flush=True);last=time.monotonic()
        r=con.getresponse();body=r.read();status=r.status;con.close()
        result=json.loads(body)
        if status!=201:raise RuntimeError('Asset upload failed: '+str(status)+' '+result.get('message',''))
        assert result['size']==size and result['state']=='uploaded'
        assert result.get('digest')=='sha256:'+digest(path), 'GitHub asset digest mismatch'
        return result

def info():
    g=GitHub();u=g.api('/user');repo=g.api('/repos/'+REPO);releases=g.api('/repos/'+REPO+'/releases?per_page=20')
    print(json.dumps(dict(login=u['login'],push=repo.get('permissions',{}).get('push'),default_branch=repo['default_branch'],releases=[dict(tag=r['tag_name'],draft=r['draft'],url=r['html_url']) for r in releases]),ensure_ascii=False))

def publish():
    g=GitHub();manifest=json.loads((RELEASE/'publish-manifest.json').read_text(encoding='utf-8'))
    assert manifest['repository']==REPO and manifest['tag']==TAG and manifest['publication_authorized']
    for name,h in manifest['assets'].items():
        p=RELEASE/name;assert p.parent==RELEASE and digest(p)==h
    assert g.api('/repos/'+REPO).get('permissions',{}).get('push'), 'GitHub credential lacks write access'
    assert not any(r['tag_name']==TAG for r in g.api('/repos/'+REPO+'/releases?per_page=100')), 'Release tag already exists; inspect rather than replace'
    assert not g.git('ls-remote','--tags','origin','refs/tags/'+TAG), 'Tag already exists'
    branch=g.git('branch','--show-current');assert branch=='main'
    g.git('fetch','origin','main');assert g.git('rev-parse','HEAD')==g.git('rev-parse','origin/main'), 'Remote branch changed; review before publishing'
    g.git('config','user.name','exelight7');g.git('config','user.email','183371784+exelight7@users.noreply.github.com')
    roots=['README.md','.gitignore','CHANGELOG.md','installer','translations','docs','assets']
    if TAG=='v0.2.0-beta.1':roots+=['.gitattributes','AGENTS.md','project.json','requirements-project.txt','03_translation','04_fonts','05_media','08_qa','project_seed','tools','skills']
    g.git('add','--',*roots)
    staged=g.git('diff','--cached','--name-only').splitlines();assert staged
    allowed=tuple(n+'/' for n in roots if (CHECKOUT/n).is_dir())
    assert all(n in roots or n.startswith(allowed) for n in staged)
    assert not any(n.lower().endswith(('.exe','.vfs0','.vfx','.appimage','.dll','.pyd')) for n in staged)
    title='Publish full authoring project and 4A dialogue Skill/toolkit' if TAG=='v0.2.0-beta.1' else 'Publish Arabic patch sources and Windows/Proton installer beta'
    g.git('commit','-m',title)
    commit=g.git('rev-parse','HEAD');print('Publishing source commit',commit,flush=True)
    g.git('push','origin','main')
    g.git('tag','-a',TAG,'-m',title)
    g.git('push','origin','refs/tags/'+TAG)
    body=(RELEASE/'RELEASE_NOTES_AR.md').read_text(encoding='utf-8')
    release=g.api('/repos/'+REPO+'/releases',dict(tag_name=TAG,target_commitish=commit,name='تعريب Metro Exodus — '+TAG,body=body,draft=True,prerelease=True,make_latest='false'))
    receipt=dict(repository=REPO,tag=TAG,commit=commit,release_id=release['id'],url=release['html_url'],draft=True,assets=[])
    receipt_path=ROOT/'00_admin'/('github_release_receipt.json' if TAG=='v0.1.0-beta.1' else 'github_release_receipt_'+TAG+'.json');receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in manifest['assets']:
        asset=g.upload(release['id'],RELEASE/name)
        receipt['assets'].append({k:asset[k] for k in ['id','name','size','digest','browser_download_url']})
        receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Verified asset',name,flush=True)
    # All content and assets exist and have matching server hashes before publication.
    result=g.api('/repos/'+REPO+'/releases/'+str(release['id']),dict(draft=False,prerelease=True,make_latest='false'),method='PATCH')
    assert not result['draft'] and result['prerelease'] and len(result['assets'])==len(manifest['assets'])
    receipt.update(draft=False,published_at=result['published_at'],published=True)
    receipt['url']=result['html_url']
    receipt['assets']=[{k:a[k] for k in ['id','name','size','digest','browser_download_url']} for a in result['assets']]
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PUBLISHED',result['html_url'],flush=True)

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publish',action='store_true');parser.add_argument('--tag',default=TAG,choices=['v0.1.0-beta.1','v0.2.0-beta.1']);args=parser.parse_args()
    TAG=args.tag;RELEASE=ROOT/'09_release'/TAG
    if args.publish:publish()
    else:info()
