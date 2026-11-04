"""Real delta/EXE transaction, but only in a private temporary fixture."""
from pathlib import Path
from unittest.mock import patch
import copy,json,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from core import Installer,sha,file_sha,read_archive,INDEX,EXE
import loading_native_patch

def main():
    live=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
    source=ROOT/'06_build/installer_resources';profile=json.loads((source/'profile.json').read_text())
    live_files=[live/INDEX,live/EXE,*sorted(live.glob('metro_arabic_*.vfs0'))]
    before={p.name:file_sha(p) for p in live_files}
    with tempfile.TemporaryDirectory(prefix='installer-real-fixture-',dir=ROOT/'06_build') as temp:
        private=Path(temp).resolve();assert private.is_relative_to((ROOT/'06_build').resolve())
        game=private/'game';game.mkdir();resources=private/'resources';shutil.copytree(source,resources)
        # Compact original archive fixture. Source assets are read from live VFS
        # files but no live file is linked, written, renamed or removed.
        p=copy.deepcopy(profile);archive=game/'fixture.vfs0'
        with archive.open('wb') as f:
            for e in p['base_assets']:
                raw=read_archive(live,e);offset=f.tell();f.write(raw)
                e.update(archive=archive.name,offset=offset,csize=len(raw),usize=len(raw))
        (resources/'profile.json').write_text(json.dumps(p))
        (game/INDEX).write_bytes((ROOT/'01_original/steam_local'/INDEX).read_bytes())
        (game/EXE).write_bytes(loading_native_patch.verified_original(live/EXE,ROOT))
        engine=Installer(resources)
        with patch('core.require_closed'):
            engine.install(game,configs=[])
            assert file_sha(game/INDEX)==profile['installed_index']
            assert file_sha(game/EXE)==profile['installed_exe']
            assert file_sha(game/profile['payload_name'])==profile['installed_payload']
            engine.install(game,configs=[])
            engine.restore(game,config_allowlist=[])
            assert file_sha(game/INDEX)==profile['original_index']
            assert file_sha(game/EXE)==profile['original_exe']
            assert not (game/profile['payload_name']).exists()
    after={p.name:file_sha(p) for p in live_files};assert before==after
    report=dict(real_asset_install_reinstall_restore=True,live_game_unchanged=True,live_files_verified=len(before),live_sha256=after,game_started=False)
    (ROOT/'08_qa/audit/installer_real_transaction.json').write_text(json.dumps(report,indent=2))
    print('REAL DELTA INSTALL / REINSTALL / RESTORE PASSED; LIVE FILES UNCHANGED:',len(before))
if __name__=='__main__':main()
