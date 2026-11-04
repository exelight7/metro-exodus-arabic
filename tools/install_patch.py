"""Install/uninstall this private experimental patch without starting Metro."""
import json,hashlib,shutil,datetime,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATCH=ROOT/'07_patch'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((PATCH/'manifest.json').read_text());game=Path(manifest['game_dir'])
    receipt=ROOT/'00_admin/install_receipt.json'
    if '--uninstall' in sys.argv:
        state=json.loads(receipt.read_text());backup=Path(state['backup'])
        for name,expected in manifest['files'].items():
            assert digest(game/name)==expected,'Installed file changed: '+name
        shutil.copy2(backup/'patch_04.vfx',game/'patch_04.vfx')
        extra=game/'metro_arabic.vfs0'
        if (backup/extra.name).exists():shutil.copy2(backup/extra.name,extra)
        else:extra.unlink()
        state['uninstalled']=True;receipt.write_text(json.dumps(state,indent=2));print('Original files restored. Game was not started.');return
    assert '--allow-draft' in sys.argv or not manifest['untranslated_entries'],'Incomplete draft: installation requires an explicit --allow-draft choice'
    for name,expected in manifest['files'].items():assert digest(PATCH/name)==expected
    current=digest(game/'patch_04.vfx')
    if current==manifest['files']['patch_04.vfx']:
        assert digest(game/'metro_arabic.vfs0')==manifest['files']['metro_arabic.vfs0'];print('Already installed.');return
    assert current==manifest['original_index_sha256'],'Game version changed; refusing to overwrite'
    backup=ROOT/'backups'/('pre_install_'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
    for name in manifest['files']:
        p=game/name
        if p.exists():shutil.copy2(p,backup/name)
    (backup/'SHA256SUMS').write_text('\n'.join(digest(p)+'  '+p.name for p in backup.iterdir() if p.is_file()))
    # The data is ready before the index starts referring to it.
    shutil.copy2(PATCH/'metro_arabic.vfs0',game/'metro_arabic.vfs0')
    try:shutil.copy2(PATCH/'patch_04.vfx',game/'patch_04.vfx')
    except Exception:
        if not (backup/'metro_arabic.vfs0').exists():(game/'metro_arabic.vfs0').unlink(missing_ok=True)
        raise
    for name,expected in manifest['files'].items():assert digest(game/name)==expected
    receipt.write_text(json.dumps(dict(backup=str(backup),manifest=manifest,game_started=False),indent=2))
    print('Installed and verified. Backup:',backup,'Game was not started.')
if __name__=='__main__':main()
