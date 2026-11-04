"""Offline, version-locked Windows/Proton patch installer. Never launches a game."""
from __future__ import annotations
import contextlib, copy, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, time
from pathlib import Path
import bsdiff4
import lz4.block

ADMIN = '.metro_arabic'
INDEX = 'patch_04.vfx'
EXE = 'MetroExodus.exe'

class InstallError(Exception):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def safe_path(root: Path, name: str) -> Path:
    if name not in (INDEX,EXE) and not re.fullmatch(r'metro_arabic_[A-Za-z0-9_]+\.vfs0',name):
        raise InstallError('اسم ملف التعريب غير صالح.')
    p=root/name
    if p.is_symlink() or p.resolve().parent!=root.resolve():
        raise InstallError('المسار المحدد يحيل إلى ملفات خارج مجلد اللعبة.')
    return p

def admin_path(game: Path) -> Path:
    p=game/ADMIN
    if p.is_symlink() or p.resolve().parent!=game.resolve():
        raise InstallError('مجلد النسخة الاحتياطية غير صالح.')
    for name in ('backup','state.json','lock','original-index.bin','original-exe.bin'):
        if (p/name).is_symlink():raise InstallError('مجلد النسخة الاحتياطية يحتوي على رابط غير متوقع.')
    for name in ('original-index.bin','original-exe.bin'):
        if (p/'backup'/name).is_symlink():raise InstallError('ملف النسخة الاحتياطية يحيل إلى مسار غير متوقع.')
    return p

def atomic(path: Path, data: bytes):
    fd,tmp=tempfile.mkstemp(prefix='.metro-ar-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        if path.exists():os.chmod(tmp,stat.S_IMODE(path.stat().st_mode))
        else:os.chmod(tmp,0o644)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def save_state(game: Path,state: dict):
    p=admin_path(game);p.mkdir(exist_ok=True)
    atomic(p/'state.json',json.dumps(state,ensure_ascii=False,indent=2).encode())

def read_state(game: Path) -> dict|None:
    p=admin_path(game)/'state.json'
    if not p.exists():return None
    try:
        s=json.loads(p.read_text(encoding='utf-8'))
        if s.get('schema')!=1:raise ValueError()
        return s
    except (ValueError,OSError):raise InstallError('سجل التثبيت غير صالح. النسخة الاحتياطية محفوظة؛ لا تحذفها.')

def require_closed():
    if os.name=='nt':
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        try:r=subprocess.run(['tasklist','/FI','IMAGENAME eq MetroExodus.exe','/FO','CSV','/NH'],capture_output=True,creationflags=flags,check=True)
        except (OSError,subprocess.SubprocessError):raise InstallError('تعذر التأكد من إغلاق اللعبة. أغلقها ثم أعد المحاولة.')
        if b'metroexodus.exe' in r.stdout.lower():raise InstallError('أغلق Metro Exodus قبل التثبيت أو الاسترجاع.')
    elif Path('/proc').exists():
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name)==os.getpid():continue
            try:args=(p/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            if any(a.replace(b'\\',b'/').rsplit(b'/',1)[-1].lower()==b'metroexodus.exe' for a in args):
                raise InstallError('أغلق Metro Exodus في Steam أو Proton قبل المتابعة.')

@contextlib.contextmanager
def lock(game: Path):
    p=admin_path(game);p.mkdir(exist_ok=True)
    with (p/'lock').open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise InstallError('هناك عملية تثبيت أو استرجاع أخرى قيد العمل.')
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(f,fcntl.LOCK_UN)

def steam_libraries() -> list[Path]:
    homes=[]
    if os.name=='nt':
        with contextlib.suppress(OSError,ImportError):
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam') as k:homes.append(Path(winreg.QueryValueEx(k,'SteamPath')[0]))
        homes.extend([Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam'])
    else:homes.extend([Path.home()/'.local/share/Steam',Path.home()/'.steam/steam',Path.home()/'.var/app/com.valvesoftware.Steam/.local/share/Steam'])
    result=[]
    for root in homes:
        if root.exists():result.append(root)
        vdf=root/'steamapps/libraryfolders.vdf'
        if vdf.exists():
            text=vdf.read_text(encoding='utf-8',errors='replace')
            result.extend(Path(x.replace('\\\\','\\')) for x in re.findall(r'"path"\s+"([^"\n]+)"',text))
    return list(dict.fromkeys(p.resolve() for p in result if p.exists()))

def detect_games() -> list[Path]:
    result=[]
    for root in steam_libraries():
        for name in ['Metro Exodus']:
            p=root/'steamapps/common'/name
            if (p/EXE).is_file() and (p/INDEX).is_file():result.append(p)
    return result

def config_roots(game: Path) -> list[Path]:
    if os.name=='nt':return [Path.home()/'Saved Games/metro exodus',Path.home()/'Saved Games/Metro Exodus']
    root=game.parent.parent/'compatdata/412020/pfx/drive_c/users/steamuser/Saved Games'
    return [root/'metro exodus',root/'Metro Exodus']

def find_configs(game: Path) -> list[Path]:
    return list(dict.fromkeys(p.resolve() for r in config_roots(game) if r.exists() for p in r.rglob('user.cfg') if not p.is_symlink()))

def read_archive(game: Path,e: dict) -> bytes:
    name=e['archive']
    if '/' in name or '\\' in name or name in ('.','..'):raise InstallError('بيانات حزمة التعريب غير صالحة.')
    p=game/name
    if p.is_symlink() or p.resolve().parent!=game.resolve():raise InstallError('ملفات اللعبة تحيل إلى مسار خارج المجلد.')
    try:
        with p.open('rb') as f:f.seek(e['offset']);raw=f.read(e['csize'])
    except OSError:raise InstallError('ملف من ملفات اللعبة مفقود: '+name)
    if len(raw)!=e['csize']:raise InstallError('ملفات اللعبة ناقصة. تحقق من سلامتها في Steam.')
    if e['csize']==e['usize']:out=raw
    else:
        import struct
        pos=0;blocks=[];window=b''
        while pos<len(raw):
            if pos+8>len(raw):raise InstallError('ملف اللعبة المضغوط غير صالح.')
            n,u=struct.unpack_from('<II',raw,pos)
            if n<8 or pos+n>len(raw) or u>e['usize']:raise InstallError('ملف اللعبة المضغوط غير صالح.')
            b=lz4.block.decompress(raw[pos+8:pos+n],uncompressed_size=u,dict=window)
            blocks.append(b);window=(window+b)[-65536:];pos+=n
        out=b''.join(blocks)
    if len(out)!=e['usize'] or sha(out)!=e['sha256']:raise InstallError('إصدار ملفات اللعبة لا يطابق هذا التعريب. لم تتغير ملفاتك.')
    return out

class Installer:
    def __init__(self,resources: Path,progress=None):
        self.resources=resources
        self.profile=json.loads((resources/'profile.json').read_text(encoding='utf-8'))
        self.progress=progress or (lambda percent,message:None)
    def emit(self,n,msg):self.progress(n,msg)
    def resource(self,name):
        if name not in self.profile['resources']:raise InstallError('ملف تعريب غير معروف.')
        b=(self.resources/name).read_bytes()
        if sha(b)!=self.profile['resources'][name]:raise InstallError('حزمة التعريب غير سليمة. أعد استخراج التطبيق أو تنزيله.')
        return b
    def inspect(self,game: Path) -> dict:
        game=game.expanduser().resolve()
        if not game.is_dir():raise InstallError('اختر مجلد Metro Exodus أولا.')
        if not (game/EXE).is_file():
            if (game/'MetroExodus').exists():raise InstallError('هذه نسخة Linux الأصلية. التطبيق مخصص لنسخة Windows عبر Proton فقط.')
            raise InstallError('لم أعثر على MetroExodus.exe. اختر مجلد اللعبة الذي يحتوي عليه.')
        if not (game/INDEX).is_file():raise InstallError('ملف اللعبة patch_04.vfx مفقود.')
        with safe_path(game,EXE).open('rb') as f:magic=f.read(2)
        if magic!=b'MZ':raise InstallError('المثبت يدعم نسخة Windows، وعلى لينكس تشغيلها عبر Proton.')
        ih=file_sha(safe_path(game,INDEX));eh=file_sha(safe_path(game,EXE));p=self.profile
        if ih not in (p['original_index'],p['installed_index']) or eh not in (p['original_exe'],p['installed_exe']):
            raise InstallError('هذا الإصدار غير مدعوم أو توجد تعديلات أخرى. يلزم إصدار Steam المطابق؛ لم تتغير ملفاتك.')
        s=read_state(game)
        if s and s.get('status') in ('installing','restoring'):return dict(status='recovery',path=str(game),owned=True)
        installed=ih==p['installed_index']
        if installed:
            f=safe_path(game,p['payload_name'])
            if not f.is_file() or file_sha(f)!=p['installed_payload']:raise InstallError('فهرس التعريب موجود، لكن ملف التعريب مفقود أو تغير. استرجع نسختك الاحتياطية.')
        return dict(status='installed' if installed and eh==p['installed_exe'] else 'partial' if installed or eh==p['installed_exe'] else 'ready',path=str(game),owned=bool(s and s.get('status')=='installed'))
    def originals(self,game: Path):
        p=self.profile;index=safe_path(game,INDEX).read_bytes();exe=safe_path(game,EXE).read_bytes()
        if sha(index)==p['installed_index']:index=bsdiff4.patch(index,self.resource('index.reverse.bsdiff'))
        if sha(exe)==p['installed_exe']:
            offset=p['native_offset'];before=bytes.fromhex(p['native_before']);after=bytes.fromhex(p['native_after'])
            if exe[offset:offset+len(after)]!=after:raise InstallError('تعذر التحقق من إصلاح التحميل.')
            exe=exe[:offset]+before+exe[offset+len(after):]
        if sha(index)!=p['original_index'] or sha(exe)!=p['original_exe']:raise InstallError('تعذر التحقق من الملفات الأصلية.')
        return index,exe
    def verify(self,game: Path):
        info=self.inspect(game)
        self.emit(10,'التحقق من ملفات اللعبة')
        for i,e in enumerate(self.profile['base_assets']):
            read_archive(game,e);self.emit(15+int(70*(i+1)/len(self.profile['base_assets'])),'فحص '+str(i+1)+' / '+str(len(self.profile['base_assets'])))
        for name in self.profile['resources']:self.resource(name)
        self.emit(100,'اكتمل الفحص بنجاح')
        return info
    def install(self,game: Path,configure=True,configs=None,fault=None):
        game=game.expanduser().resolve();require_closed();self.inspect(game)
        p=self.profile;state=read_state(game)
        if state and state.get('status') in ('installing','restoring'):raise InstallError('توجد عملية متوقفة. استخدم استرجاع الأصل أولا.')
        self.emit(5,'التحقق من الحزمة وإصدار اللعبة')
        if shutil.disk_usage(game).free<p['required_free_bytes']:raise InstallError('لا توجد مساحة كافية للنسخة الاحتياطية والتثبيت.')
        original_index,original_exe=self.originals(game)
        base=[]
        for i,e in enumerate(p['base_assets']):
            base.append(read_archive(game,e));self.emit(8+int(27*(i+1)/len(p['base_assets'])),'التحقق من ملفات اللعبة الأصلية')
        payload=bsdiff4.patch(b''.join(base),self.resource('payload.bsdiff'))
        patched_index=bsdiff4.patch(original_index,self.resource('index.forward.bsdiff'))
        off=p['native_offset'];before=bytes.fromhex(p['native_before']);after=bytes.fromhex(p['native_after'])
        if original_exe[off:off+len(before)]!=before:raise InstallError('إصدار الملف التنفيذي غير مدعوم.')
        patched_exe=original_exe[:off]+after+original_exe[off+len(before):]
        if sha(payload)!=p['installed_payload'] or sha(patched_index)!=p['installed_index'] or sha(patched_exe)!=p['installed_exe']:
            raise InstallError('فشل التحقق من بناء التعريب. لم تتغير ملفات اللعبة.')
        with lock(game):
            require_closed();self.inspect(game)
            previous=copy.deepcopy(read_state(game))
            if previous and previous.get('status') in ('installing','restoring'):raise InstallError('توجد عملية متوقفة. استخدم استرجاع الأصل أولا.')
            before_index=safe_path(game,INDEX).read_bytes();before_exe=safe_path(game,EXE).read_bytes()
            payload_path=safe_path(game,p['payload_name']);created=not payload_path.exists()
            if payload_path.exists() and file_sha(payload_path)!=p['installed_payload']:raise InstallError('يوجد ملف آخر بالاسم نفسه. لن يستبدله التطبيق.')
            admin=admin_path(game);backup=admin/'backup';backup.mkdir(exist_ok=True)
            for name,data,h in [('original-index.bin',original_index,p['original_index']),('original-exe.bin',original_exe,p['original_exe'])]:
                out=backup/name
                if out.is_symlink():raise InstallError('مسار النسخة الاحتياطية غير صالح.')
                if out.exists():
                    if file_sha(out)!=h:raise InstallError('النسخة الاحتياطية الموجودة مختلفة. احتفظ بها ولا تستبدلها.')
                else:atomic(out,data)
            self.emit(45,'حفظ النسخة الاحتياطية الأصلية')
            active=previous if previous and previous.get('status')=='installed' else None
            state=dict(schema=1,revision=p['revision'],status='installing',created_payload=active.get('created_payload',created) if active else created,profiles=active.get('profiles',[]) if active else [],time=int(time.time()))
            save_state(game,state);changed_configs=[]
            try:
                atomic(payload_path,payload)
                if fault:fault('payload')
                self.emit(65,'تجهيز ملفات التعريب')
                atomic(safe_path(game,EXE),patched_exe)
                if fault:fault('exe')
                atomic(safe_path(game,INDEX),patched_index)
                if fault:fault('index')
                self.emit(85,'تفعيل التعريب وإصلاح نص التحميل')
                if configure:
                    paths=list(configs) if configs is not None else find_configs(game)
                    for cfg in paths:
                        cfg=Path(cfg)
                        if cfg.is_symlink():continue
                        raw=cfg.read_bytes();m=re.search(rb'(?m)^lang_text ([^\r\n]+)',raw)
                        if not m or m[1]==b'us':continue
                        prior=m[1].decode('ascii')
                        changed_configs.append((cfg,raw))
                        if not any(v['path']==str(cfg.resolve()) for v in state['profiles']):state['profiles'].append(dict(path=str(cfg.resolve()),original_language=prior))
                        save_state(game,state)
                        atomic(cfg,raw[:m.start(1)]+b'us'+raw[m.end(1):])
                        if fault:fault('config')
                state['status']='installed';save_state(game,state)
                if file_sha(safe_path(game,INDEX))!=p['installed_index'] or file_sha(safe_path(game,EXE))!=p['installed_exe'] or file_sha(payload_path)!=p['installed_payload']:raise InstallError('تعذر تأكيد اكتمال التثبيت.')
            except Exception:
                atomic(safe_path(game,EXE),before_exe);atomic(safe_path(game,INDEX),before_index)
                for cfg,raw in changed_configs:atomic(cfg,raw)
                if created and payload_path.exists() and file_sha(payload_path)==p['installed_payload']:payload_path.unlink()
                if previous:save_state(game,previous)
                else:state['status']='rolled_back';save_state(game,state)
                raise
        self.emit(100,'اكتمل تثبيت التعريب')
        return dict(status='installed',configured_profiles=len(state['profiles']))
    def restore(self,game: Path,config_allowlist=None):
        game=game.expanduser().resolve();require_closed();self.inspect(game);p=self.profile
        with lock(game):
            state=read_state(game)
            if not state or state.get('status') not in ('installed','installing','restoring') or state.get('revision')!=p['revision']:
                raise InstallError('لا توجد نسخة احتياطية أنشأها هذا التطبيق. استخدم أداة التثبيت السابقة لاسترجاع ملفاتها.')
            b=admin_path(game)/'backup';index=(b/'original-index.bin').read_bytes();exe=(b/'original-exe.bin').read_bytes()
            if sha(index)!=p['original_index'] or sha(exe)!=p['original_exe']:raise InstallError('تعذر التحقق من النسخة الاحتياطية؛ لن تتغير ملفات اللعبة.')
            payload=safe_path(game,p['payload_name'])
            if payload.exists() and file_sha(payload)!=p['installed_payload']:raise InstallError('تغير ملف التعريب بعد تثبيته؛ لن يستبدله التطبيق.')
            state['status']='restoring';save_state(game,state);self.emit(30,'استرجاع ملفات اللعبة الأصلية')
            atomic(safe_path(game,EXE),exe);atomic(safe_path(game,INDEX),index)
            allowed={p.resolve() for p in (config_allowlist if config_allowlist is not None else find_configs(game))}
            for profile in state['profiles']:
                cfg=Path(profile['path'])
                if cfg.is_symlink() or cfg.resolve() not in allowed or not cfg.exists():continue
                raw=cfg.read_bytes();m=re.search(rb'(?m)^lang_text ([^\r\n]+)',raw)
                if m and m[1]==b'us':atomic(cfg,raw[:m.start(1)]+profile['original_language'].encode('ascii')+raw[m.end(1):])
            if state.get('created_payload') and payload.exists():payload.unlink()
            state['status']='restored';save_state(game,state)
            if file_sha(game/INDEX)!=p['original_index'] or file_sha(game/EXE)!=p['original_exe']:raise InstallError('تعذر تأكيد الاسترجاع؛ النسخة الاحتياطية محفوظة.')
        self.emit(100,'استعيدت الملفات الأصلية بنجاح')
        return dict(status='restored')
