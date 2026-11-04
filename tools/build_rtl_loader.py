"""Remove the long LTR reveal delay without changing native code or narration.

The native typewriter has no demonstrated RTL option. A nonzero 1-ms interval
avoids division-by-zero risks; this is accelerated appearance, not RTL animation.
"""
import struct,json,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    raise RuntimeError('Accelerated loader experiment withdrawn. Use build_repair_ui.py to restore native timing.')
    source=ROOT/'02_extracted/steam_local/patch_04/content/scripts/loader_data.bin'
    b=bytearray(source.read_bytes());p=79
    assert struct.unpack_from('<II',b,p)==(zlib.crc32(b'typewriter'),25) and b[p+8]==4
    start=p+9
    assert struct.unpack_from('<I',b,start+12)[0]==40
    assert struct.unpack_from('<f',b,start+16)[0]==1.25
    struct.pack_into('<I',b,start+12,1);struct.pack_into('<f',b,start+16,1.0)
    (ROOT/'06_build/stage/content/scripts/loader_data.bin').write_bytes(b)
    (ROOT/'08_qa/audit/rtl_loader.json').write_text(json.dumps(dict(original_click_time_ms=40,click_time_ms=1,random_div=1.0,rtl_animation_supported=False,runtime_tested=False),indent=2))
    print('Native LTR typewriter interval 40 ms -> 1 ms; actual RTL animation is not supported by this patch')
if __name__=='__main__':main()
