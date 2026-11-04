"""Exercise repair/install, refusal of unknown files, and combined uninstall offline."""
import datetime,json,shutil
from pathlib import Path
from install_loading_native import install,restore
from loading_native_patch import build,digest,ORIGINAL_SHA256,REVISION,verified_original
from install_phase import uninstall

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')

def main():
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    fixture=ROOT/'06_build'/f'loading_install_{stamp}'
    game=fixture/'game';admin=fixture/'00_admin';back=fixture/'backups/clean'
    for p in [game,admin,back]:p.mkdir(parents=True,exist_ok=False)
    raw=verified_original(GAME/'MetroExodus.exe',ROOT)
    (game/'MetroExodus.exe').write_bytes(raw)
    pkg=ROOT/'07_patch/phases/100_graphics_label_r1'
    manifest=json.loads((pkg/'manifest.json').read_text())
    for n in manifest['files']:shutil.copy2(pkg/n,game/n)
    live=json.loads((ROOT/'00_admin/phase_install_receipt.json').read_text())
    shutil.copy2(live['clean_backup'],back/'patch_04.vfx')
    local=dict(revision='graphics_label_r1',uninstalled=False,
        index_sha256=manifest['files']['patch_04.vfx'],original_sha256=manifest['original_index_sha256'],
        clean_backup=str(back/'patch_04.vfx'),payloads={n:h for n,h in manifest['files'].items() if n!='patch_04.vfx'})
    (admin/'phase_install_receipt.json').write_text(json.dumps(local))
    state=install(game,fixture)
    assert (game/'MetroExodus.exe').read_bytes()==build(raw)
    assert install(game,fixture)==state
    restore(game,fixture);assert (game/'MetroExodus.exe').read_bytes()==raw
    restore(game,fixture)
    # Unknown binaries must be refused, never overwritten.
    modified=bytearray(raw);modified[-1]^=1;(game/'MetroExodus.exe').write_bytes(modified)
    refused=False
    try:install(game,fixture)
    except AssertionError:refused=True
    assert refused and (game/'MetroExodus.exe').read_bytes()==modified
    (game/'MetroExodus.exe').write_bytes(raw)
    install(game,fixture)
    uninstall(game,fixture)
    assert (game/'MetroExodus.exe').read_bytes()==raw
    assert digest((game/'patch_04.vfx').read_bytes())==local['original_sha256']
    assert all(not (game/n).exists() for n in local['payloads'])
    report=dict(revision=REVISION,fixture=str(fixture),install_exact=True,install_idempotent=True,
        restore_byte_identical=True,unknown_version_refused=True,combined_uninstall_restores_exe_and_index=True,
        game_started=False)
    (ROOT/f'08_qa/audit/{REVISION}_install_test.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
