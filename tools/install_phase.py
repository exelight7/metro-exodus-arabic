"""Install cumulative localization milestones with a verified, atomic index switch."""
import argparse,datetime,hashlib,json,os,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_json(path,data):
    temp=path.with_suffix('.writing.json');temp.write_text(json.dumps(data,indent=2));os.replace(temp,path)

def configure_language():
    import re
    receipt=ROOT/'00_admin/phase_install_receipt.json';state=json.loads(receipt.read_text())
    assert not state.get('uninstalled')
    settings=state.setdefault('text_language_settings',[])
    existing={s['path'] for s in settings}
    folder=Path.home()/'Saved Games/Metro Exodus'
    for cfg in folder.rglob('user.cfg'):
        original=cfg.read_bytes();match=re.search(rb'(?m)^lang_text ([^\r\n]+)',original)
        if not match or match.group(1)==b'us':continue
        assert str(cfg) not in existing,'Language settings were changed after configuration'
        backup=ROOT/'backups'/('pre_text_language_'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True);shutil.copy2(cfg,backup/'user.cfg')
        updated=original[:match.start(1)]+b'us'+original[match.end(1):]
        cfg.write_bytes(updated);assert cfg.read_bytes()==updated
        settings.append(dict(path=str(cfg),backup=str(backup/'user.cfg'),original_language=match.group(1).decode('ascii'),installed_language='us',installed_sha256=digest(cfg)))
    save_json(receipt,state);print('Configured text to the patched US language; voice settings unchanged')
def install(percent,game=DEFAULT_GAME,state_root=ROOT,patch_directory=None):
    game=Path(game);state_root=Path(state_root)
    patch=Path(patch_directory) if patch_directory else ROOT/f'07_patch/phases/{percent}'
    manifest=json.loads((patch/'manifest.json').read_text())
    assert manifest['phase']==percent
    for name,expected in manifest['files'].items():assert digest(patch/name)==expected,name
    admin=state_root/'00_admin';admin.mkdir(parents=True,exist_ok=True)
    receipt=admin/'phase_install_receipt.json'
    state=json.loads(receipt.read_text()) if receipt.exists() else None
    current=digest(game/'patch_04.vfx')
    if state and not state.get('uninstalled'):
        assert current==state['index_sha256'],'Installed index was changed by another operation'
        for name,h in state['payloads'].items():assert digest(game/name)==h,name
    else:
        assert current==manifest['original_index_sha256'],'Game version does not match the clean original'
        state=dict(original_sha256=current,history=[],payloads={})
    if current==manifest['files']['patch_04.vfx']:
        print('Already installed phase',percent);return state
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime('%Y%m%d-%H%M%S-%f')
    backup=state_root/'backups'/f'pre_phase_{percent}_{stamp}';backup.mkdir(parents=True)
    shutil.copy2(game/'patch_04.vfx',backup/'patch_04.vfx')
    assert digest(backup/'patch_04.vfx')==current
    (backup/'SHA256SUMS').write_text(current+'  patch_04.vfx\n')
    if not state['history']:state['clean_backup']=str(backup/'patch_04.vfx')
    payload=next(n for n in manifest['files'] if n!='patch_04.vfx')
    destination=game/payload
    if destination.exists():assert digest(destination)==manifest['files'][payload],'Unrecognized payload already exists'
    else:shutil.copy2(patch/payload,destination)
    assert digest(destination)==manifest['files'][payload]
    temp=game/'patch_04.vfx.arabic_staging'
    assert not temp.exists(),'Index staging file already exists'
    shutil.copy2(patch/'patch_04.vfx',temp)
    assert digest(temp)==manifest['files']['patch_04.vfx']
    try:
        os.replace(temp,game/'patch_04.vfx')
        assert digest(game/'patch_04.vfx')==manifest['files']['patch_04.vfx']
    except Exception:
        if digest(game/'patch_04.vfx')!=current:shutil.copy2(backup/'patch_04.vfx',game/'patch_04.vfx')
        raise
    state.update(phase=percent,revision=manifest.get('revision',''),index_sha256=manifest['files']['patch_04.vfx'],game_dir=str(game),uninstalled=False,game_started=False)
    state['payloads'][payload]=manifest['files'][payload]
    state['history'].append(dict(phase=percent,revision=manifest.get('revision',''),backup=str(backup),timestamp=stamp,index_sha256=state['index_sha256']))
    save_json(receipt,state)
    print('INSTALLED phase',percent,'verified index + payload; original backup:',state['clean_backup'],flush=True)
    return state

def uninstall(game=DEFAULT_GAME,state_root=ROOT):
    game=Path(game);receipt=Path(state_root)/'00_admin/phase_install_receipt.json';state=json.loads(receipt.read_text())
    assert not state.get('uninstalled')
    assert digest(game/'patch_04.vfx')==state['index_sha256']
    for name,h in state['payloads'].items():assert digest(game/name)==h,name
    clean=Path(state['clean_backup']);assert digest(clean)==state['original_sha256']
    # The separately version-locked loading repair must also restore on uninstall.
    from install_loading_native import restore as restore_loading_native
    restore_loading_native(game,state_root)
    temp=game/'patch_04.vfx.arabic_restore';assert not temp.exists()
    shutil.copy2(clean,temp);os.replace(temp,game/'patch_04.vfx')
    assert digest(game/'patch_04.vfx')==state['original_sha256']
    for name in state['payloads']:(game/name).unlink()
    import re
    for item in state.get('text_language_settings',[]):
        cfg=Path(item['path']);data=cfg.read_bytes()
        match=re.search(rb'(?m)^lang_text ([^\r\n]+)',data)
        if match and match.group(1)==b'us':
            # Preserve any unrelated settings updated since installation.
            cfg.write_bytes(data[:match.start(1)]+item['original_language'].encode()+data[match.end(1):])
    state['uninstalled']=True;save_json(receipt,state);print('RESTORED clean original')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',type=int,choices=[25,50,75,100]);parser.add_argument('--uninstall',action='store_true');parser.add_argument('--configure-language',action='store_true')
    parser.add_argument('--patch-directory',type=Path)
    args=parser.parse_args()
    running=subprocess.run(['tasklist','/FI','IMAGENAME eq MetroExodus.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True).stdout
    assert 'metroexodus.exe' not in running.lower(),'Close the running game before installation'
    if args.uninstall:uninstall()
    elif args.configure_language:configure_language()
    elif args.phase:install(args.phase,patch_directory=args.patch_directory)
    else:parser.error('Specify --phase or --uninstall')
