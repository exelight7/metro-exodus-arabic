"""Independent full install/uninstall of diary assets and loading companion."""
import datetime,json
from pathlib import Path
from install_phase import install,uninstall,digest
from install_loading_native import install as install_native
from loading_native_patch import verified_original,ORIGINAL_SHA256
ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')

def main():
    fixture=ROOT/'06_build'/('diary_install_'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    game=fixture/'game';game.mkdir(parents=True,exist_ok=False)
    original=(ROOT/'01_original/steam_local/patch_04.vfx').read_bytes()
    (game/'patch_04.vfx').write_bytes(original)
    clean_exe=verified_original(GAME/'MetroExodus.exe',ROOT);(game/'MetroExodus.exe').write_bytes(clean_exe)
    state=install(100,game,fixture,ROOT/'07_patch/phases/100_diary_r1')
    assert state['revision']=='diary_r1'
    native=install_native(game,fixture)
    assert digest(game/'MetroExodus.exe')==native['installed_sha256']
    assert install(100,game,fixture,ROOT/'07_patch/phases/100_diary_r1')==state
    uninstall(game,fixture)
    assert (game/'patch_04.vfx').read_bytes()==original
    assert (game/'MetroExodus.exe').read_bytes()==clean_exe
    assert all(not (game/n).exists() for n in state['payloads'])
    report=dict(fixture=str(fixture),revision='diary_r1',independent_asset_install=True,
        native_companion_compatible=True,repeat_install_idempotent=True,
        combined_uninstall_restores_original_exe_and_index=True,game_launched=False)
    (ROOT/'08_qa/audit/diary_r1_install_restore.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
