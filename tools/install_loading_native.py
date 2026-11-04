"""Install/restore the narrowly version-locked, offline-verified loading repair."""
import argparse,datetime,json,os,shutil,stat,subprocess
from pathlib import Path
from loading_native_patch import build,digest,ORIGINAL_SHA256,OFFSET,BEFORE,AFTER,REVISION

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')

def save(path,value):
    temp=path.with_suffix('.writing.json')
    assert not temp.exists()
    temp.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(temp,path)

def ensure_closed():
    p=subprocess.run(['tasklist','/FI','IMAGENAME eq MetroExodus.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
    assert 'metroexodus.exe' not in p.stdout.lower(),'Close Metro Exodus before installing/restoring'

def replace_checked(destination,data):
    temp=destination.with_suffix('.arabic_loading_staging')
    assert not temp.exists()
    shutil.copy2(destination,temp);temp.chmod(stat.S_IREAD|stat.S_IWRITE)
    temp.write_bytes(data)
    assert digest(temp.read_bytes())==digest(data)
    os.replace(temp,destination)
    assert destination.read_bytes()==data

def install(game=GAME,state_root=ROOT):
    ensure_closed()
    game=Path(game);state_root=Path(state_root);exe=game/'MetroExodus.exe'
    receipt=state_root/'00_admin/loading_native_receipt.json'
    raw=exe.read_bytes()
    if receipt.exists():
        state=json.loads(receipt.read_text())
        if not state.get('restored'):
            assert digest(raw)==state['installed_sha256'],'Executable changed after repair'
            return state
    report=json.loads((ROOT/f'08_qa/audit/{REVISION}_emulation.json').read_text())
    assert report['original_prefix_bug_reproduced'] and report['machine_code_emulated']
    assert report['all_loading_entries_emulated']==report['loading_entries']
    patched=build(raw);assert digest(patched)==report['patched_sha256']
    # Require the exact companion localization layout that was checked.
    local=json.loads((state_root/'00_admin/phase_install_receipt.json').read_text())
    assert not local.get('uninstalled') and local['revision'] in ('graphics_label_r1','diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1')
    assert digest((game/'patch_04.vfx').read_bytes())==local['index_sha256']
    for name,h in local['payloads'].items():assert digest((game/name).read_bytes())==h
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=state_root/'backups'/f'pre_{REVISION}_{stamp}'
    backup.mkdir(parents=True);shutil.copy2(exe,backup/exe.name)
    assert digest((backup/exe.name).read_bytes())==ORIGINAL_SHA256
    (backup/exe.name).chmod(stat.S_IREAD)
    (backup/'SHA256SUMS').write_text(ORIGINAL_SHA256+'  MetroExodus.exe\n')
    state=dict(revision=REVISION,game_dir=str(game),backup=str(backup/exe.name),
        original_sha256=ORIGINAL_SHA256,installed_sha256=digest(patched),offset=OFFSET,
        before=BEFORE.hex(),after=AFTER.hex(),span_bytes=len(AFTER),
        companion_revision=local['revision'],runtime_game_tested=False,restored=False)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    # Save recovery information before changing the executable.
    state['installation_pending']=True;save(receipt,state)
    try:replace_checked(exe,patched)
    except Exception:
        if exe.read_bytes()!=raw:replace_checked(exe,raw)
        state['restored']=True;state['installation_pending']=False;save(receipt,state)
        raise
    state['installation_pending']=False;save(receipt,state)
    print('Installed verified loading completion repair; original backed up; game NOT launched')
    return state

def restore(game=GAME,state_root=ROOT):
    ensure_closed()
    game=Path(game);state_root=Path(state_root)
    receipt=state_root/'00_admin/loading_native_receipt.json'
    if not receipt.exists():return
    state=json.loads(receipt.read_text());exe=game/'MetroExodus.exe'
    if state.get('restored'):return
    raw=exe.read_bytes();current=digest(raw)
    assert current in [state['installed_sha256'],state['original_sha256']],'Unknown executable; refusing overwrite'
    original=Path(state['backup']).read_bytes();assert digest(original)==ORIGINAL_SHA256
    if current!=ORIGINAL_SHA256:replace_checked(exe,original)
    assert digest(exe.read_bytes())==ORIGINAL_SHA256
    state['restored']=True;state['installation_pending']=False;save(receipt,state)
    print('Restored byte-identical original executable')

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--install',action='store_true');g.add_argument('--restore',action='store_true')
    a=p.parse_args()
    install() if a.install else restore()
