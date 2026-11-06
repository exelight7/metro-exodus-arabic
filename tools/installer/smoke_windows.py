"""Launch the packaged installer in screenshot/review mode; no game changes."""
from pathlib import Path
import hashlib,json,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def main():
    exe=ROOT/'09_release/installer-review/Metro-Arabic-Installer-Windows.exe'
    png=ROOT/'08_qa/render_tests/installer_windows_exe.png';png.unlink(missing_ok=True)
    result=subprocess.run([str(exe),'--screenshot',str(png),'--empty'],capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,repr(result.stderr[-3000:])
    with Image.open(png) as im:
        assert im.size==(1160,750)
        orange=sum(1 for r,g,b in im.convert('RGB').get_flattened_data() if r>190 and 85<g<195 and b<110)
        # The install button is correctly disabled before a folder is verified.
        # Theme verification must not assume that it has an enabled orange fill.
        assert orange>800
        assert sum(1 for r,g,b in im.convert('RGB').get_flattened_data() if max(r,g,b)<80)>500000
    report=dict(exit_code=result.returncode,packaged_exe_started=True,review_mode=True,screenshot=str(png.relative_to(ROOT)),width=1160,height=750,exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),game_started=False)
    (ROOT/'08_qa/audit/installer_windows_smoke.json').write_text(json.dumps(report,indent=2))
    print('PACKAGED WINDOWS EXE SMOKE PASSED')
if __name__=='__main__':main()
