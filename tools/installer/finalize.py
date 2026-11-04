"""Assemble review delivery, source archive, notices and recorded checks."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=ROOT/'09_release/installer-review';BUILD=ROOT/'06_build';ASSETS=BUILD/'installer_assets';RESOURCES=BUILD/'installer_resources'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    win=json.loads((ROOT/'08_qa/audit/installer_windows_smoke.json').read_text())
    assert win['exe_sha256']==sha(OUT/'Metro-Arabic-Installer-Windows.exe')
    linuxlog=(BUILD/'installer_linux_qa/serial.log').read_text(errors='replace')
    assert all(s in linuxlog for s in ['CORE_TEST_EXIT:0','UI_TEST_EXIT:0','LINUX_QA_DONE'])
    shutil.copy2(HERE/'README.md',OUT/'اقرأني - التثبيت وProton.md')
    shutil.copy2(ROOT/'08_qa/render_tests/installer_windows_exe.png',OUT/'معاينة-المثبت.png')
    shutil.copytree(ASSETS/'licenses',OUT/'licenses',dirs_exist_ok=True)
    shutil.copytree(BUILD/'MetroArabic.AppDir/licenses/Debian',OUT/'licenses/Debian',dirs_exist_ok=True)
    shutil.copy2(ASSETS/'THIRD-PARTY-NOTICES.txt',OUT/'THIRD-PARTY-NOTICES.txt')
    requirements='PySide6-Essentials==6.12.0\nbsdiff4==1.4.1\nlz4==4.4.5\npyinstaller==6.22.3\n'
    rebuild='''from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parent
args=[sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--windowed','--name','Metro-Arabic-Installer','--add-data',str(ROOT/'assets')+os.pathsep+'assets','--add-data',str(ROOT/'resources')+os.pathsep+'resources']
if os.name=='nt':
    import PySide6
    args+=['--icon',str(ROOT/'assets/icon.ico')]
    for dll in Path(PySide6.__file__).parent.glob('*140*.dll'):args+=['--add-binary',str(dll)+os.pathsep+'.']
env=os.environ.copy()
if os.name=='nt':
    system=Path(env.get('SystemRoot','C:/Windows'))
    env['PATH']=os.pathsep.join(map(str,[Path(PySide6.__file__).parent,Path(PySide6.__file__).parent.parent/'shiboken6',Path(sys.base_prefix),Path(sys.base_prefix)/'DLLs',system/'System32',system,system/'System32/Wbem']))
subprocess.run(args+[str(ROOT/'app.py')],cwd=ROOT,env=env,check=True)
'''
    readme='''Installer application source — review edition

This archive includes the application, offline patch differences, font, resources,
tests, dependency notices, and development/build helpers. It does not include a
game executable or complete game archives. The UI is pending owner approval.

To run or modify this application using replaceable Qt libraries:
  python -m venv .venv
  .venv/Scripts/python -m pip install -r requirements.txt   (Windows)
  .venv/Scripts/python app.py --review
  .venv/Scripts/python rebuild.py
On Linux, replace .venv/Scripts/python with .venv/bin/python.

The rebuild helper creates a native executable using PyInstaller. The exact
Windows-hosted AppImage assembly scripts and dependency inventory are under
development/ and build-metadata.json in the delivery. Those development helpers
refer to the parent project's original layout; prepare.py is for the project
maintainer's verified originals only. Application execution needs only the
included assets/ and resources/ directories and the pinned runtime packages.

Qt/PySide6/Shiboken libraries are unmodified LGPL components; replacing compatible
libraries or debugging modifications to them is not restricted by this installer.
The matching Qt/PySide source URLs and complete licenses are in the notices.
Third-party notices remain applicable to their respective code and assets.
'''
    source=OUT/'Metro-Arabic-Installer-Source.zip'
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as z:
        for n in ['app.py','core.py','test_core.py','test_ui.py']:z.write(HERE/n,n)
        z.writestr('requirements.txt',requirements);z.writestr('rebuild.py',rebuild);z.writestr('REBUILD.txt',readme)
        for folder,prefix in [(ASSETS,'assets'),(RESOURCES,'resources')]:
            for p in folder.rglob('*'):
                if p.is_file() and p.name!='build-inputs.json':z.write(p,prefix+'/'+p.relative_to(folder).as_posix())
        for p in HERE.glob('*.py'):z.write(p,'development/'+p.name)
        z.write(HERE/'requirements-build.txt','development/requirements-build.txt')
        z.write(HERE/'requirements.txt','development/requirements.txt')
        z.write(HERE/'README.md','README-ar.md')
    artifacts=[OUT/'Metro-Arabic-Installer-Windows.exe',OUT/'Metro-Arabic-Installer-Proton-x86_64.AppImage',source]
    deb=json.loads((BUILD/'installer_linux_qa/bundled_libraries.json').read_text())
    metadata=dict(installer_version='0.1.0-review',patch_revision='final_review_r1',native_revision='loading_complete_r1',design_approval_pending=True,artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in artifacts},dependencies=json.loads((BUILD/'installer_downloads/sources.json').read_text()),linux_libraries=deb,qa=dict(windows_backend_cases=20,windows_qt_ui_cases=3,windows_exe_smoke=True,linux_backend_cases=20,linux_appimage_extract_and_run=True,linux_gui='Qt offscreen screenshot inside isolated QEMU x86_64 Linux/glibc2.36',real_delta_install_reinstall_restore=True,live_game_files_verified_unchanged=26,game_started=False,steam_deck_runtime_tested=False,in_game_visual_tested=False))
    (OUT/'build-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'08_qa/audit/installer_review.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    checks='\n'.join(sha(p)+'  '+p.name for p in artifacts)+'\n'
    (OUT/'SHA256SUMS.txt').write_text(checks)
    print(json.dumps(metadata['artifacts'],indent=2))
if __name__=='__main__':main()
