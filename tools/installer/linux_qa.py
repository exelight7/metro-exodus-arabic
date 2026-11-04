"""Private build dependencies + disposable headless Linux VM smoke test.

Uses official Debian libraries, Alpine kernel and QEMU. No OS installation,
privileged services, networking in the guest, or access to the real game.
"""
import base64,concurrent.futures,gzip,hashlib,io,json,lzma,os,re,shutil,stat,struct,subprocess,sys,tarfile,urllib.request
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[2];BUILD=ROOT/'06_build';CACHE=BUILD/'installer_downloads';QA=BUILD/'installer_linux_qa';QA.mkdir(exist_ok=True)
APPDIR=BUILD/'MetroArabic.AppDir';LIBS=APPDIR/'usr/lib';LIBS.mkdir(parents=True,exist_ok=True)
def fetch(url,name):
    p=CACHE/name
    if not p.exists():
        print('Downloading QA:',name,flush=True)
        with urllib.request.urlopen(url,timeout=180) as r,p.with_suffix(p.suffix+'.tmp').open('wb') as f:shutil.copyfileobj(r,f)
        p.with_suffix(p.suffix+'.tmp').replace(p)
    return p
def needed(path):
    try:
        with path.open('rb') as f:
            if f.read(4)!=b'\x7fELF':return []
            f.seek(0);e=ELFFile(f);s=e.get_section_by_name('.dynamic')
            return [t.needed for t in s.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if s else []
    except OSError:return []
def ar_data(data):
    assert data[:8]==b'!<arch>\n';pos=8
    while pos<len(data):
        h=data[pos:pos+60];size=int(h[48:58]);name=h[:16].decode().strip().rstrip('/');b=data[pos+60:pos+60+size]
        if name.startswith('data.tar'):return b
        pos+=60+size+(size%2)
    raise ValueError('No package data')
def package_tables():
    packages=fetch('https://deb.debian.org/debian/dists/bookworm/main/binary-amd64/Packages.xz','debian-bookworm-Packages.xz')
    table={}
    for block in lzma.decompress(packages.read_bytes()).decode().split('\n\n'):
        fields=dict(line.split(': ',1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:table[fields['Package']]=fields
    return table
def download_deb(package,table):
    info=table[package];p=fetch('https://deb.debian.org/debian/'+info['Filename'],info['Filename'].rsplit('/',1)[-1])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==info['SHA256'];return p
def deb_members(package,table):
    archive=download_deb(package,table)
    with tarfile.open(fileobj=io.BytesIO(ar_data(archive.read_bytes()))) as t:
        return [(m.name.lstrip('./'),m.mode,m.linkname if m.issym() or m.islnk() else None,t.extractfile(m).read() if m.isfile() else None) for m in t if not m.isdir()]
def libs():
    assert LIBS.resolve().is_relative_to(APPDIR.resolve()) and LIBS.name=='lib'
    shutil.rmtree(LIBS);LIBS.mkdir()
    table=package_tables();contents=fetch('https://deb.debian.org/debian/dists/bookworm/main/Contents-amd64.gz','debian-bookworm-Contents-amd64.gz')
    owners={}
    with gzip.open(contents,'rt',errors='replace') as f:
        for line in f:
            if '.so' not in line:continue
            fields=line.split()
            if len(fields)==2 and (fields[0].startswith(('usr/lib/x86_64-linux-gnu/','lib/x86_64-linux-gnu/')) or fields[0].count('/')==2 and fields[0].startswith('usr/lib/')) and '/debug/' not in fields[0]:
                owners.setdefault(fields[0].rsplit('/',1)[-1],fields[1].split(',')[0].rsplit('/',1)[-1])
    known={p.name:p for p in APPDIR.rglob('*.so*')};queue=[]
    for pattern in ['python/bin/python3.12','python/lib/libpython3.12.so.1.0','python/lib/python3.12/site-packages/PySide6/QtCore.abi3.so','python/lib/python3.12/site-packages/PySide6/QtGui.abi3.so','python/lib/python3.12/site-packages/PySide6/QtWidgets.abi3.so']:
        queue.append(APPDIR/pattern)
    queue.extend((APPDIR/'python/lib/python3.12/lib-dynload').glob('*.so'))
    queue.extend((APPDIR/'python/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms').glob('*.so'))
    base={'libc.so.6','libm.so.6','libpthread.so.0','libdl.so.2','librt.so.1','ld-linux-x86-64.so.2','libresolv.so.2','libutil.so.1'}
    done=set();packages=set();aliases=[]
    while queue:
        p=queue.pop()
        if str(p) in done:continue
        done.add(str(p))
        for name in needed(p):
            if name in base:continue
            if name not in known:
                package=owners.get(name)
                if not package:raise RuntimeError('No Debian owner for '+name+' required by '+str(p))
                if package in packages:raise RuntimeError('Missing library '+name+' in '+package)
                packages.add(package);members=deb_members(package,table);blobs={n:b for n,m,l,b in members if b is not None}
                for n,m,target,b in members:
                    if '.so' not in n or '/lib' not in '/'+n:continue
                    dest=LIBS/Path(n).name
                    if b is not None:dest.write_bytes(b);known[dest.name]=dest;queue.append(dest)
                    elif target is not None:aliases.append((dest.name,Path(target).name))
                license_dir=APPDIR/'licenses/Debian'/package;license_dir.mkdir(parents=True,exist_ok=True)
                for n,m,l,b in members:
                    if n.endswith('/copyright') and b is not None:(license_dir/'copyright').write_bytes(b)
                for a,b in aliases[:]:
                    if b in known:
                        # Copy aliases; each normal file is portable in the Windows staging tree.
                        dest=LIBS/a;shutil.copyfile(known[b],dest);known[a]=dest;aliases.remove((a,b))
            if name not in known:raise RuntimeError('Unresolved '+name)
            queue.append(known[name])
    manifest=dict(packages=sorted(packages),libraries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in LIBS.glob('*')})
    (QA/'bundled_libraries.json').write_text(json.dumps(manifest,indent=2));print('BUNDLED LINUX LIBRARIES',len(manifest['libraries']),flush=True)
def cpio(entries,dest):
    with dest.open('wb') as f:
        inode=0
        for name,mode,data in entries+[('TRAILER!!!',0,b'')]:
            inode+=1;n=name.encode()+b'\0';fields=[inode,mode,0,0,1,0,len(data),0,0,0,0,len(n),0]
            h=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields);f.write(h+n);f.write(b'\0'*((-(len(h)+len(n)))%4));f.write(data);f.write(b'\0'*(-len(data)%4))
def vm():
    # The entire guest filesystem is temporary and has no host shared folders.
    table=package_tables();kernel=fetch('https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/netboot-3.22.7/vmlinuz-virt','vmlinuz-virt-3.22.7')
    qemu=fetch('https://qemu.weilnetz.de/w64/qemu-w64-setup-20260811.exe','qemu-w64-20260811.exe')
    checks=fetch('https://qemu.weilnetz.de/w64/qemu-w64-setup-20260811.sha512','qemu-w64-20260811.sha512').read_text().split()[0]
    assert hashlib.sha512(qemu.read_bytes()).hexdigest()==checks
    qemudir=QA/'qemu'
    if not (qemudir/'qemu-system-x86_64.exe').exists():subprocess.run([r'C:\Program Files\7-Zip\7z.exe','x','-y',str(qemu),'-o'+str(qemudir)],check=True,stdout=subprocess.DEVNULL)
    entries=[(n,stat.S_IFDIR|0o755,b'') for n in ['bin','lib','lib64','lib/x86_64-linux-gnu','usr','usr/lib','usr/lib/x86_64-linux-gnu','proc','sys','dev','tmp','root','run','etc']]
    for package in ['busybox-static','libc6']:
        for n,m,target,b in deb_members(package,table):
            if package=='busybox-static' and not n.endswith('/busybox'):continue
            if package=='libc6' and not (n.startswith('lib/x86_64-linux-gnu/') and n.count('/')==2 or n.startswith('lib64/')):continue
            if b is not None:entries.append((n,stat.S_IFREG|m,b))
            elif target:entries.append((n,stat.S_IFLNK|0o777,target.encode()))
    for name in ['sh','mount','mkdir','dirname','poweroff','sleep','ln','chmod','cat']:
        entries.append(('bin/'+name,stat.S_IFLNK|0o777,b'busybox'))
    artifact=ROOT/'09_release/installer-review/Metro-Arabic-Installer-Proton-x86_64.AppImage'
    entries.append(('installer.AppImage',stat.S_IFREG|0o755,artifact.read_bytes()))
    init='''#!/bin/sh
export PATH=/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /tmp /root /run
export HOME=/root
export QT_QPA_PLATFORM=offscreen
export XDG_RUNTIME_DIR=/run
export LANG=C.UTF-8
chmod 700 /run
cd /tmp
echo LINUX_APPIMAGE_RUNTIME_START
/installer.AppImage --appimage-extract >/tmp/extract.log 2>&1
echo EXTRACT_EXIT:$?
export APPDIR=/tmp/squashfs-root
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$APPDIR/python/lib:$APPDIR/python/lib/python3.12/site-packages/PySide6/Qt/lib"
export PYTHONDONTWRITEBYTECODE=1
"$APPDIR/python/bin/python3.12" -I -c "import sys; sys.path.insert(0,'/tmp/squashfs-root/app'); import test_core,unittest; r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_core)); sys.exit(not r.wasSuccessful())"
echo CORE_TEST_EXIT:$?
/installer.AppImage --appimage-extract-and-run --screenshot /tmp/linux-installer.png --empty
echo UI_TEST_EXIT:$?
"$APPDIR/python/bin/python3.12" -I -c "from pathlib import Path; import base64; p=Path('/tmp/linux-installer.png'); print('LINUX_SCREENSHOT_BYTES',p.stat().st_size if p.exists() else 0); print('SCREENSHOT_BASE64_BEGIN'+base64.b64encode(p.read_bytes()).decode()+'SCREENSHOT_BASE64_END')"
echo LINUX_QA_DONE
poweroff -f
'''
    entries.append(('init',stat.S_IFREG|0o755,init.encode()));dest=QA/'initramfs.cpio';cpio(entries,dest)
    print('BOOTING ISOLATED LINUX',flush=True)
    with (QA/'serial.log').open('wb') as log:
        subprocess.run([str(qemudir/'qemu-system-x86_64.exe'),'-machine','pc','-accel','tcg','-cpu','max','-smp','1','-m','2048','-kernel',str(kernel),'-initrd',str(dest),'-append','console=ttyS0 rdinit=/init panic=-1 quiet noapic nolapic','-display','none','-serial','stdio','-monitor','none','-nic','none','-no-reboot'],stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
    result=(QA/'serial.log').read_text(errors='replace')
    capture=re.search('SCREENSHOT_BASE64_BEGIN([A-Za-z0-9+/=]+)SCREENSHOT_BASE64_END',result)
    if capture:(ROOT/'08_qa/render_tests/installer_linux.png').write_bytes(base64.b64decode(capture[1]))
    compact=re.sub('SCREENSHOT_BASE64_BEGIN.*?SCREENSHOT_BASE64_END','[screenshot saved to audit artifacts]',result,flags=re.S);print(compact[-12000:])
    assert all(s in result for s in ['EXTRACT_EXIT:0','CORE_TEST_EXIT:0','UI_TEST_EXIT:0','LINUX_QA_DONE']), 'Linux smoke test failed; inspect serial.log'
    assert capture, 'Linux UI screenshot missing'
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='vm':vm()
    else:libs()
