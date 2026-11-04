"""Collect redistribution notices without redistributing build tools."""
from pathlib import Path
import importlib.metadata,json,shutil,sys,urllib.request
ROOT=Path(__file__).resolve().parents[2];ASSETS=ROOT/'06_build/installer_assets';OUT=ASSETS/'licenses';OUT.mkdir(exist_ok=True)
def main():
    for name in ['PySide6-Essentials','shiboken6','bsdiff4','lz4','PyInstaller']:
        dist=importlib.metadata.distribution(name)
        for file in dist.files:
            if 'licenses/' in str(file).lower():
                src=dist.locate_file(file);dest=OUT/name/Path(file).name;dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',OUT/'Python-LICENSE.txt')
    shutil.copy2(ASSETS/'OFL.txt',OUT/'NotoSansArabic-OFL.txt')
    from linux_qa import deb_members,package_tables
    for n,m,l,b in deb_members('base-files',package_tables()):
        if 'usr/share/common-licenses/' in n and b is not None:(OUT/Path(n).name).write_bytes(b)
    for name,url in [('AppImage-runtime-LICENSE','https://raw.githubusercontent.com/AppImage/type2-runtime/main/LICENSE')]:
        dest=OUT/name
        if not dest.exists():
            with urllib.request.urlopen(url,timeout=60) as r:dest.write_bytes(r.read())
    notice='''Third-party components

Qt / PySide6 / Shiboken6 6.12.0: LGPL v3 / GPL v3 options and applicable exceptions.
Unmodified sources: https://code.qt.io/cgit/qt/qtbase.git/?h=v6.12.0
Bindings source: https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.12.0
Source archives: https://download.qt.io/official_releases/qt/6.12/6.12.0/
Use the LGPL option for the applicable libraries in this application. The installer
does not restrict replacement or debugging of those libraries. Application source,
resources and rebuild instructions accompany the review delivery.

Python 3.12: PSF license; Linux build by astral-sh/python-build-standalone.
https://github.com/astral-sh/python-build-standalone
bsdiff4 1.4.1 and LZ4 4.4.5: BSD licenses in the accompanying notices.
Noto Sans Arabic: SIL Open Font License 1.1 (font and license included).
Windows bootstrap: PyInstaller (GPL with bootloader exception).
AppImage runtime: https://github.com/AppImage/type2-runtime (license included).
Linux shared libraries: unmodified Debian 12 packages. Their copyright and
license texts are included under licenses/Debian inside the AppImage and delivery.
Exact binary versions and hashes are recorded in build-metadata.json.
Corresponding Debian sources: https://sources.debian.org/ (package names in metadata).
GNU runtime library exceptions are reproduced in the package copyright notices.

Metro Exodus is the property of its respective owners. This is an unofficial
localization installer. It redistributes binary differences rather than whole
original game archives or a game executable. No official affiliation is implied.
'''
    (ASSETS/'THIRD-PARTY-NOTICES.txt').write_text(notice,encoding='utf-8')
    print('Notices collected',flush=True)
if __name__=='__main__':main()
