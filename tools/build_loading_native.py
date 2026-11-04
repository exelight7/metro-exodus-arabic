"""Build a tiny version-locked patch recipe, not a redistributed game executable."""
import json
from pathlib import Path
from loading_native_patch import *

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')

def main():
    raw=verified_original(GAME/'MetroExodus.exe',ROOT);changed=build(raw)
    evidence=json.loads((ROOT/f'08_qa/audit/{REVISION}_emulation.json').read_text())
    assert evidence['patched_sha256']==digest(changed)
    assert evidence['all_loading_entries_emulated']==evidence['loading_entries']
    out=ROOT/'07_patch/native'/REVISION;out.mkdir(parents=True,exist_ok=True)
    manifest=dict(revision=REVISION,original_sha256=ORIGINAL_SHA256,patched_sha256=digest(changed),
        file='MetroExodus.exe',offset=OFFSET,rva=hex(RVA),before=BEFORE.hex(),after=AFTER.hex(),
        span_bytes=len(AFTER),changed_bytes=sum(a!=b for a,b in zip(BEFORE,AFTER)),
        companion_revision='graphics_label_r1',mechanism='Complete loading text at first reveal tick',
        game_entry_point_run=False,runtime_game_tested=False,rtl_animation=False,
        verification='08_qa/audit/loading_complete_r1_emulation.json')
    dest=out/'manifest.json'
    if dest.exists():assert json.loads(dest.read_text())==manifest,'Use a new revision for different payload'
    else:dest.write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
