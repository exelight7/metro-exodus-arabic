from pathlib import Path
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
