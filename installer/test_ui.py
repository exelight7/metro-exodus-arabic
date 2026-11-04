"""Exercise real Qt worker threads and controls on a synthetic game only."""
import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from test_core import InstallerTests
import app
from core import read_state

class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def setUp(self):
        self.fixture=InstallerTests();self.fixture.setUp()
        self.old=app.RESOURCES;app.RESOURCES=self.fixture.resources
        self.patches=[patch('app.detect_games',return_value=[]),patch('core.require_closed'),patch('core.find_configs',return_value=[])]
        for p in self.patches:p.start()
        self.window=app.Window();self.window.show();self.window.path.setText(str(self.fixture.game))
    def tearDown(self):
        self.wait();self.window.close();self.qt.processEvents();app.RESOURCES=self.old
        for p in reversed(self.patches):p.stop()
        self.fixture.doCleanups()
    def wait(self):
        limit=time.monotonic()+15
        while self.window.busy and time.monotonic()<limit:self.qt.processEvents();time.sleep(.01)
        self.assertFalse(self.window.busy,'Qt worker did not complete')
    def confirm(self):
        for w in QApplication.topLevelWidgets():
            if isinstance(w,QMessageBox):w.buttons()[0].click()
    def test_install_restore_buttons_and_threads(self):
        w=self.window;w.inspect();self.assertTrue(w.busy);self.assertFalse(w.path.isEnabled());self.wait()
        self.assertTrue(w.install_btn.isEnabled());self.assertFalse(w.restore_btn.isEnabled())
        QTimer.singleShot(50,self.confirm);w.request('install');self.wait()
        self.assertEqual(read_state(self.fixture.game)['status'],'installed');self.assertTrue(w.restore_btn.isEnabled())
        QTimer.singleShot(50,self.confirm);w.request('restore');self.wait()
        self.fixture.assert_original();self.assertFalse(w.restore_btn.isEnabled());self.assertTrue(w.path.isEnabled())
    def test_unknown_version_disables_mutation(self):
        (self.fixture.game/'MetroExodus.exe').write_bytes(b'MZunknown')
        w=self.window;w.inspect();self.wait();self.assertFalse(w.install_btn.isEnabled());self.assertFalse(w.restore_btn.isEnabled())
        self.assertTrue(w.browse.isEnabled());self.assertIn('غير مدعوم',w.status_body.text())
    def test_failed_transaction_keeps_restore_available(self):
        w=self.window;w.inspect();self.wait()
        QTimer.singleShot(50,self.confirm);w.request('install');self.wait()
        with patch('core.Installer.restore',side_effect=PermissionError('fixture')):
            QTimer.singleShot(50,self.confirm);w.request('restore');self.wait()
        self.assertTrue(w.restore_btn.isEnabled());self.assertIn('الكتابة',w.status_body.text())
if __name__=='__main__':unittest.main(verbosity=2)
