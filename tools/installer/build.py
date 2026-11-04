"""Build a Windows EXE and a genuine Linux ELF + SquashFS AppImage on Windows.

No game is executed or modified. Linux runtime testing is a separate check.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tarfile,urllib.request,zipfile
import zstandard
ROOT=Path(__file__).resolve().parents[2];SOURCE=Path(__file__).resolve().parent
BUILD=ROOT/'06_build';CACHE=BUILD/'installer_downloads';OUT=ROOT/'09_release/installer-review';OUT.mkdir(exist_ok=True)
ASSETS=BUILD/'installer_assets';RESOURCES=BUILD/'installer_resources'
def run(args,**kw):
    print('RUN',*map(str,args[:3]),flush=True);return subprocess.run(list(map(str,args)),check=True,**kw)
def get(url,dest):
    if not dest.exists():
        with urllib.request.urlopen(url,timeout=120) as r,dest.open('wb') as f:shutil.copyfileobj(r,f)
    return dest
def msys(p):return '/'+p.drive[0].lower()+'/'+str(p.resolve()).replace('\\','/')[3:]
def windows(console=False):
    import PySide6
    # Keep the complete, matching vendor C++ runtime together. Depending on
    # whichever _1/_2 DLL happens to be in System32 can mix incompatible sets.
    binaries=[]
    for dll in Path(PySide6.__file__).parent.glob('*140*.dll'):binaries.extend(['--add-binary',str(dll)+';.'])
    env=os.environ.copy();system=Path(env.get('SystemRoot','C:/Windows'))
    env['PATH']=os.pathsep.join(map(str,[Path(PySide6.__file__).parent,Path(PySide6.__file__).parent.parent/'shiboken6',Path(sys.base_prefix),Path(sys.base_prefix)/'DLLs',system/'System32',system,system/'System32/Wbem']))
    # Reject unrelated PATH copies of Windows ICU/API-set DLL names (e.g.
    # Poppler's ICU with numbered exports). Qt requires the Windows ICU API.
    run([sys.executable,'-m','PyInstaller','--noconfirm',*(['--clean'] if console else []),'--noupx','--onefile','--console' if console else '--windowed','--name','Metro-Arabic-Installer-Windows','--icon',ASSETS/'icon.ico','--add-data',str(ASSETS)+';assets','--add-data',str(RESOURCES)+';resources',*binaries,'--distpath',BUILD/'installer_debug' if console else OUT,'--workpath',BUILD/'installer_pyinstaller','--specpath',BUILD/'installer_specs',SOURCE/'app.py'],cwd=ROOT,env=env,stdout=(BUILD/'installer_windows_build.log').open('w'),stderr=subprocess.STDOUT)
    toc=(BUILD/'installer_pyinstaller/Metro-Arabic-Installer-Windows/PKG-00.toc').read_text()
    assert 'poppler' not in toc.lower() and 'libheif' not in toc.lower(), 'Contaminated dependency search path'
    print('WINDOWS EXE READY',flush=True)
def linux():
    appdir=BUILD/'MetroArabic.AppDir';appdir.mkdir(exist_ok=True)
    modes={};links=[]
    # Materialize regular tar files; preserve Unix symlinks through SquashFS pseudo definitions.
    with tarfile.open(CACHE/'python-linux.tar.gz') as t:
        for m in t:
            if not (m.name.startswith('python/bin/') or m.name.startswith('python/lib/') or m.name.startswith('python/licenses/')):continue
            if '/__pycache__/' in m.name or '/site-packages/pip/' in m.name or '/test/' in m.name or '/tests/' in m.name:continue
            if m.name.endswith(('.a','.pyc','.pyo','.whl')):continue
            dest=appdir/m.name
            if m.isdir():dest.mkdir(parents=True,exist_ok=True)
            elif m.issym():links.append((m.name,m.linkname))
            elif m.isfile():
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists():
                    with t.extractfile(m) as f,dest.open('wb') as out:shutil.copyfileobj(f,out)
                if m.mode&0o111:modes[m.name]=0o755
    site=appdir/'python/lib/python3.12/site-packages';site.mkdir(exist_ok=True)
    for wheel in CACHE.glob('*.whl'):
        with zipfile.ZipFile(wheel) as z:
            for info in z.infolist():
                name=info.filename
                if name.endswith('/') or '/include/' in name or '/Qt/qml/' in name or '/Qt/translations/' in name:continue
                if '..' in Path(name).parts:raise ValueError('Unsafe wheel')
                dest=site/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info))
    app=appdir/'app';app.mkdir(exist_ok=True)
    for name in ('app.py','core.py','test_core.py'):shutil.copy2(SOURCE/name,app/name)
    shutil.copytree(ASSETS,app/'assets',dirs_exist_ok=True);shutil.copytree(RESOURCES,app/'resources',dirs_exist_ok=True)
    (app/'resources/build-inputs.json').unlink(missing_ok=True)
    (appdir/'AppRun').write_text('#!/bin/sh\nset -eu\nAPPDIR="${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"\nexport APPDIR\nexport PYTHONDONTWRITEBYTECODE=1\nexport PYTHONNOUSERSITE=1\nexport FONTCONFIG_FILE="$APPDIR/app/assets/fonts.conf"\nexport LD_LIBRARY_PATH="$APPDIR/usr/lib:$APPDIR/python/lib:$APPDIR/python/lib/python3.12/site-packages/PySide6/Qt/lib:${LD_LIBRARY_PATH:-}"\nexport QT_PLUGIN_PATH="$APPDIR/python/lib/python3.12/site-packages/PySide6/Qt/plugins"\nexport QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_PATH/platforms"\nunset PYTHONHOME PYTHONPATH\nexec "$APPDIR/python/bin/python3.12" -I "$APPDIR/app/app.py" "$@"\n',encoding='utf-8',newline='\n')
    # -I hides the script directory; explicitly add only our own source directory.
    entry=app/'app.py';text=entry.read_text(encoding='utf-8');text=text.replace('from core import Installer',"sys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom core import Installer");entry.write_text(text,encoding='utf-8')
    (appdir/'metro-arabic.desktop').write_text('[Desktop Entry]\nType=Application\nName=Metro Exodus Arabic Installer\nName[ar]=مثبت تعريب مترو إكسودس\nComment=Windows game via Proton only\nExec=AppRun\nIcon=metro-arabic\nCategories=Game;Utility;\nTerminal=false\n',encoding='utf-8',newline='\n')
    shutil.copy2(ASSETS/'icon.png',appdir/'metro-arabic.png');shutil.copy2(ASSETS/'icon.png',appdir/'.DirIcon')
    modes['AppRun']=0o755
    toolroot=CACHE/'squashfs-tools';tool=toolroot/'usr/bin/mksquashfs.exe'
    if not tool.exists():
        raw=zstandard.ZstdDecompressor().decompress((CACHE/'squashfs-tools.pkg.tar.zst').read_bytes(),max_output_size=10000000)
        tp=CACHE/'squashfs-tools.pkg.tar';tp.write_bytes(raw)
        with tarfile.open(tp) as t:t.extractall(toolroot,filter='data')
    # liblzo2 is not included with Git for Windows; keep build-only DLLs private.
    dll=tool.parent/'msys-lzo2-2.dll'
    if not dll.exists():
        import re,io
        with urllib.request.urlopen('https://packages.msys2.org/package/liblzo2') as r:page=r.read().decode()
        url=re.search(r'https://mirror.msys2.org/msys/x86_64/liblzo2-[^"<> ]+\.pkg\.tar\.zst',page).group()
        archive=get(url,CACHE/'liblzo2.pkg.tar.zst');raw=zstandard.ZstdDecompressor().decompress(archive.read_bytes(),max_output_size=5000000)
        with tarfile.open(fileobj=io.BytesIO(raw)) as t:dll.write_bytes(t.extractfile('usr/bin/msys-lzo2-2.dll').read())
    env=os.environ.copy();env['PATH']=str(tool.parent)+';C:\\Program Files\\Git\\usr\\bin;'+env['PATH']
    # All files default to 0644. Restore Unix execution bits and symlinks explicitly.
    pseudo=BUILD/'installer_squashfs.pseudo';lines=[]
    for name,mode in sorted(modes.items()):lines.append(f'{name} m {mode:o} 0 0')
    for name,target in links:
        if not (appdir/name).exists():lines.append(f'{name} s 777 0 0 {target}')
    pseudo.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    squash=BUILD/'installer.squashfs'
    run([tool,msys(appdir),msys(squash),'-noappend','-all-root','-no-xattrs','-comp','gzip','-b','1048576','-no-progress','-all-time','0','-root-mode','755','-pf',msys(pseudo)],env=env,stdout=(BUILD/'installer_squashfs.log').open('w'),stderr=subprocess.STDOUT)
    runtime=(CACHE/'runtime-x86_64').read_bytes();assert runtime[:4]==b'\x7fELF' and runtime[8:11]==b'AI\x02'
    artifact=OUT/'Metro-Arabic-Installer-Proton-x86_64.AppImage'
    with artifact.open('wb') as out:
        out.write(runtime)
        with squash.open('rb') as f:shutil.copyfileobj(f,out)
    run([tool.parent/'unsquashfs.exe','-s','-offset',str(len(runtime)),msys(artifact)],env=env,stdout=(BUILD/'installer_appimage_structure.log').open('w'),stderr=subprocess.STDOUT)
    (BUILD/'installer_appimage_metadata.json').write_text(json.dumps(dict(runtime_bytes=len(runtime),squashfs_bytes=squash.stat().st_size,artifact_bytes=artifact.stat().st_size,sha256=hashlib.sha256(artifact.read_bytes()).hexdigest()),indent=2))
    print('APPIMAGE READY',artifact,flush=True)
if __name__=='__main__':
    if len(sys.argv)<2 or sys.argv[1]=='windows':windows()
    elif sys.argv[1]=='windows-debug':windows(console=True)
    elif sys.argv[1]=='linux':linux()
