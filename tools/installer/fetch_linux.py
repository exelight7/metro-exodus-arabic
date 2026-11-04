"""Fetch pinned official Linux runtime, wheels and SquashFS build tools."""
import concurrent.futures,hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];CACHE=ROOT/'06_build/installer_downloads';CACHE.mkdir(exist_ok=True)
def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Metro-Arabic-Installer-Build'}),timeout=90) as r:return json.load(r)
def fetch(pair):
    name,url=pair;dest=CACHE/name
    if not dest.exists():
        print('Downloading:',name,flush=True)
        temp=dest.with_suffix(dest.suffix+'.download')
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Metro-Arabic-Installer-Build'}),timeout=180) as r,temp.open('wb') as f:
            while b:=r.read(1024*1024):f.write(b)
        temp.replace(dest)
    print('Cached:',name,dest.stat().st_size,flush=True)
    return dict(file=name,url=url,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
def main():
    urls=[('python-linux.tar.gz','https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.12.16%2B20261026-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz'),('squashfs-tools.pkg.tar.zst','https://mirror.msys2.org/msys/x86_64/squashfs-tools-4.7.5-1-x86_64.pkg.tar.zst'),('runtime-x86_64','https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64')]
    # Pin the exact Linux wheels and hashes provided by PyPI.
    for package,version in [('PySide6-Essentials','6.12.0'),('shiboken6','6.12.0'),('bsdiff4','1.4.1'),('lz4','4.4.5')]:
        data=get_json(f'https://pypi.org/pypi/{package}/{version}/json')
        candidates=[u for u in data['urls'] if u['filename'].endswith('.whl') and 'x86_64' in u['filename'] and 'manylinux' in u['filename'] and ('cp312' in u['filename'] or 'cp310-abi3' in u['filename'])]
        if not candidates:raise RuntimeError('No compatible wheel for '+package)
        u=sorted(candidates,key=lambda x:x['filename'])[0];urls.append((u['filename'],u['url']))
        print('Linux wheel:',u['filename'],'official SHA256',u['digests']['sha256'],flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:manifest=list(ex.map(fetch,urls))
    for item in manifest:
        if item['file'].endswith('.whl'):
            package=item['file'].split('-')[0];data=get_json(f'https://pypi.org/pypi/{package}/json')
            match=next(u for u in data['urls'] if u['filename']==item['file'])
            assert match['digests']['sha256']==item['sha256']
    (CACHE/'sources.json').write_text(json.dumps(manifest,indent=2))
    print('DOWNLOADS VERIFIED',flush=True)
if __name__=='__main__':main()
