"""Transactions exercised exclusively in temporary synthetic game folders."""
import copy,json,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bsdiff4,lz4.block
from core import Installer,InstallError,INDEX,EXE,ADMIN,sha,read_state,save_state,lock,read_archive

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='metro-installer-test-');self.root=Path(self.temp.name)
        self.game=self.root/'SteamLibrary/steamapps/common/Metro Exodus';self.game.mkdir(parents=True)
        self.resources=self.root/'resources';self.resources.mkdir()
        self.original_index=b'original VFX test fixture';self.installed_index=b'Arabic VFX test fixture'
        self.original_exe=b'MZ'+b'0'*30+b'BEFORE'+b'Z'*32;self.installed_exe=self.original_exe[:32]+b'AFTER!'+self.original_exe[38:]
        self.base=b'original decoded asset\n'*48;self.payload=b'Arabic decoded asset\n'*62
        (self.game/INDEX).write_bytes(self.original_index);(self.game/EXE).write_bytes(self.original_exe)
        (self.game/'content.vfs0').write_bytes(b'xxxx'+self.base)
        self.cfg=self.root/'saved/user.cfg';self.cfg.parent.mkdir();self.cfg.write_bytes(b'lang_sound ru\r\nlang_text fr\r\nvolume 0.5\r\n')
        deltas={'index.forward.bsdiff':bsdiff4.diff(self.original_index,self.installed_index),'index.reverse.bsdiff':bsdiff4.diff(self.installed_index,self.original_index),'payload.bsdiff':bsdiff4.diff(self.base,self.payload)}
        for n,b in deltas.items():(self.resources/n).write_bytes(b)
        self.p=dict(schema=1,revision='fixture',payload_name='metro_arabic_fixture.vfs0',original_index=sha(self.original_index),installed_index=sha(self.installed_index),original_exe=sha(self.original_exe),installed_exe=sha(self.installed_exe),installed_payload=sha(self.payload),native_offset=32,native_before=b'BEFORE'.hex(),native_after=b'AFTER!'.hex(),required_free_bytes=10000,resources={n:sha(b) for n,b in deltas.items()},base_assets=[dict(archive='content.vfs0',offset=4,csize=len(self.base),usize=len(self.base),sha256=sha(self.base))])
        (self.resources/'profile.json').write_text(json.dumps(self.p));self.engine=Installer(self.resources)
        self.closed=patch('core.require_closed');self.closed.start();self.addCleanup(self.closed.stop)
        self.addCleanup(self.temp.cleanup)
    def install(self,**kw):return self.engine.install(self.game,configs=[self.cfg],**kw)
    def restore(self):return self.engine.restore(self.game,config_allowlist=[self.cfg])
    def assert_original(self):
        self.assertEqual((self.game/INDEX).read_bytes(),self.original_index);self.assertEqual((self.game/EXE).read_bytes(),self.original_exe)
    def test_install_and_restore(self):
        self.assertEqual(self.engine.inspect(self.game)['status'],'ready');self.install()
        self.assertEqual(self.engine.verify(self.game)['status'],'installed')
        self.assertIn(b'lang_text us',self.cfg.read_bytes());self.assertIn(b'lang_sound ru',self.cfg.read_bytes())
        self.restore();self.assert_original();self.assertIn(b'lang_text fr',self.cfg.read_bytes());self.assertFalse((self.game/self.p['payload_name']).exists())
    def test_reinstall_idempotent(self):
        self.install();original_backup=(self.game/ADMIN/'backup/original-exe.bin').read_bytes();self.install()
        self.assertEqual((self.game/ADMIN/'backup/original-exe.bin').read_bytes(),original_backup);self.restore();self.assert_original()
    def test_install_after_restore(self):
        self.install();self.restore();self.install();self.restore();self.assert_original();self.assertFalse((self.game/self.p['payload_name']).exists())
    def test_user_settings_preserved_on_restore(self):
        self.install();self.cfg.write_bytes(self.cfg.read_bytes().replace(b'volume 0.5',b'volume 0.9'))
        self.restore();self.assertIn(b'volume 0.9',self.cfg.read_bytes());self.assertIn(b'lang_text fr',self.cfg.read_bytes())
    def test_language_changed_by_user_preserved(self):
        self.install();self.cfg.write_bytes(self.cfg.read_bytes().replace(b'lang_text us',b'lang_text de'))
        self.restore();self.assertIn(b'lang_text de',self.cfg.read_bytes())
    def test_config_option_off(self):
        raw=self.cfg.read_bytes();self.install(configure=False);self.assertEqual(self.cfg.read_bytes(),raw)
    def test_rollback_each_mutation(self):
        for step in ['payload','exe','index','config']:
            with self.subTest(step=step):
                before=self.cfg.read_bytes()
                def fail(at):
                    if at==step:raise OSError('simulated write failure')
                with self.assertRaises(OSError):self.install(fault=fail)
                self.assert_original();self.assertEqual(self.cfg.read_bytes(),before);self.assertFalse((self.game/self.p['payload_name']).exists())
    def test_failed_reinstall_retains_restore_receipt(self):
        self.install();receipt=copy.deepcopy(read_state(self.game))
        def fail(at):
            if at=='index':raise OSError('simulated')
        with self.assertRaises(OSError):self.install(fault=fail)
        self.assertEqual(read_state(self.game),receipt);self.assertEqual(self.engine.inspect(self.game)['status'],'installed');self.restore();self.assert_original()
    def test_unknown_game_refused(self):
        (self.game/EXE).write_bytes(b'MZunsupported');
        with self.assertRaises(InstallError):self.install()
        self.assertEqual((self.game/INDEX).read_bytes(),self.original_index);self.assertFalse((self.game/ADMIN).exists())
    def test_native_linux_refused(self):
        (self.game/EXE).unlink();(self.game/'MetroExodus').write_bytes(b'\x7fELF')
        with self.assertRaisesRegex(InstallError,'Linux'):self.engine.inspect(self.game)
    def test_corrupt_delta_refused_before_write(self):
        (self.resources/'payload.bsdiff').write_bytes(b'invalid')
        with self.assertRaises(InstallError):self.install()
        self.assert_original();self.assertFalse((self.game/ADMIN).exists())
    def test_changed_base_refused(self):
        (self.game/'content.vfs0').write_bytes(b'xxxx'+b'?'*len(self.base))
        with self.assertRaises(InstallError):self.install()
        self.assert_original()
    def test_conflicting_payload_not_overwritten(self):
        payload=self.game/self.p['payload_name'];payload.write_bytes(b'unrelated')
        with self.assertRaises(InstallError):self.install()
        self.assert_original();self.assertEqual(payload.read_bytes(),b'unrelated')
    def test_existing_external_patch_can_be_adopted(self):
        (self.game/INDEX).write_bytes(self.installed_index);(self.game/EXE).write_bytes(self.installed_exe)
        (self.game/self.p['payload_name']).write_bytes(self.payload);self.install();self.assertFalse(read_state(self.game)['created_payload'])
        self.restore();self.assert_original();self.assertTrue((self.game/self.p['payload_name']).exists())
        self.install();self.restore();self.assertTrue((self.game/self.p['payload_name']).exists())
    def test_crash_recovery(self):
        self.install();s=read_state(self.game);s['status']='installing';save_state(self.game,s)
        (self.game/self.p['payload_name']).unlink();self.assertEqual(self.engine.inspect(self.game)['status'],'recovery')
        self.restore();self.assert_original()
    def test_corrupt_backup_not_restored(self):
        self.install();(self.game/ADMIN/'backup/original-exe.bin').write_bytes(b'wrong')
        with self.assertRaises(InstallError):self.restore()
        self.assertEqual((self.game/EXE).read_bytes(),self.installed_exe)
    def test_concurrent_lock_refused(self):
        with lock(self.game):
            with self.assertRaises(InstallError):
                with lock(self.game):pass
    def test_config_restore_allowlist(self):
        self.install();s=read_state(self.game);outside=self.root/'unrelated.cfg';outside.write_bytes(b'lang_text us\n');s['profiles'].append(dict(path=str(outside),original_language='ru'));save_state(self.game,s)
        self.restore();self.assertEqual(outside.read_bytes(),b'lang_text us\n')
    def test_lz4_block_dictionary(self):
        blocks=[b'a synthetic original asset '*1500,b'a synthetic original asset '*1000];raw=b'';window=b''
        for b in blocks:
            c=lz4.block.compress(b,store_size=False,dict=window);raw+=struct.pack('<II',len(c)+8,len(b))+c;window=(window+b)[-65536:]
        (self.game/'compressed.vfs0').write_bytes(raw);whole=b''.join(blocks)
        e=dict(archive='compressed.vfs0',offset=0,csize=len(raw),usize=len(whole),sha256=sha(whole));self.assertEqual(read_archive(self.game,e),whole)
    def test_game_not_running_required(self):
        self.closed.stop()
        with patch('core.require_closed',side_effect=InstallError('close game')):
            with self.assertRaises(InstallError):self.install()
        self.closed.start();self.assert_original()

if __name__=='__main__':unittest.main(verbosity=2)
