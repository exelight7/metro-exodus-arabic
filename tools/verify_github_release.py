"""Verify the publicly visible release and downloads without authentication."""
from pathlib import Path
import argparse,hashlib,io,json,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1];REPO='exelight7/metro-exodus-arabic';TAG='v0.1.0-beta.1'
def public(path):
    req=urllib.request.Request('https://api.github.com/repos/'+REPO+path,headers={'Accept':'application/vnd.github+json','User-Agent':'Metro-Arabic-Public-Verification','X-GitHub-Api-Version':'2026-03-10'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def main():
    manifest=json.loads((ROOT/'09_release'/TAG/'publish-manifest.json').read_text(encoding='utf-8'))
    data=public('/releases/tags/'+TAG);assert data['tag_name']==TAG and not data['draft'] and data['prerelease']
    assets={a['name']:a for a in data['assets']};assert set(assets)==set(manifest['assets'])
    for name,h in manifest['assets'].items():
        a=assets[name];local=ROOT/'09_release'/TAG/name
        assert a['state']=='uploaded' and a['size']==local.stat().st_size and a['digest']=='sha256:'+h
        assert '/releases/download/'+TAG+'/' in a['browser_download_url']
    # Exercise an actual public download, including GitHub's asset redirects.
    url=assets['INSTALLATION_AR.md']['browser_download_url']
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Metro-Arabic-Public-Verification'}),timeout=60) as r:guide=r.read()
    assert hashlib.sha256(guide).hexdigest()==manifest['assets']['INSTALLATION_AR.md']
    skill_verified=False
    if 'FourA-Dialogue-Skill.zip' in assets:
        with urllib.request.urlopen(urllib.request.Request(assets['FourA-Dialogue-Skill.zip']['browser_download_url'],headers={'User-Agent':'Metro-Arabic-Public-Verification'}),timeout=60) as r:skill=r.read()
        assert hashlib.sha256(skill).hexdigest()==manifest['assets']['FourA-Dialogue-Skill.zip']
        with zipfile.ZipFile(io.BytesIO(skill)) as z:
            assert z.testzip() is None and 'foura-dialogue/SKILL.md' in z.namelist() and 'foura-dialogue/scripts/foura_dialogue.py' in z.namelist()
        skill_verified=True
    ref=public('/git/ref/tags/'+TAG);obj=ref['object']
    commit=public('/git/tags/'+obj['sha'])['object']['sha'] if obj['type']=='tag' else obj['sha']
    receipt_path=ROOT/'00_admin'/('github_release_receipt.json' if TAG=='v0.1.0-beta.1' else 'github_release_receipt_'+TAG+'.json');receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    assert receipt['commit']==commit
    receipt.update(url=data['html_url'],published=True,draft=False,published_at=data['published_at'],publicly_verified=True)
    receipt['assets']=[{k:a[k] for k in ['id','name','size','digest','browser_download_url']} for a in data['assets']]
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(url=data['html_url'],tag=TAG,commit=commit,public_release=True,prerelease=data['prerelease'],asset_count=len(assets),all_server_digests_match=True,public_guide_download_verified=True,public_skill_download_verified=skill_verified,assets=receipt['assets'])
    (ROOT/'08_qa/audit'/('github_publication_verified.json' if TAG=='v0.1.0-beta.1' else 'github_publication_verified_'+TAG+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(url=report['url'],public=True,assets=len(assets),digests_verified=True,download_verified=True)))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tag',default=TAG,choices=['v0.1.0-beta.1','v0.2.0-beta.1']);TAG=parser.parse_args().tag;main()
