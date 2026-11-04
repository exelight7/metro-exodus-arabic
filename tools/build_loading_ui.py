"""Use native right alignment for loading text; preserve clean typewriter config."""
import json,re,struct
from pathlib import Path
from build_repair_ui import main as repair_ui
ROOT=Path(__file__).resolve().parents[1]
CONTROLS=['hint_level_narrative','hint_random','hint_random_dlc1','hint_random_dlc2']
def patch_record(body):
    data=bytearray(body)
    for name in CONTROLS:
        marker=b'\x03'+name.encode()+b'\0type\0u32\0';assert data.count(marker)==1
        p=data.index(marker);n=struct.unpack_from('<I',data,p-4)[0];child=data[p:p+n]
        field=b'h_alignment\0u8\0';q=p+child.index(field)+len(field)
        assert data[q]==3
        # Native enum table: Left=0, Right=1, Center=2, Justify=3.
        data[q]=1
        for size_field in ['font_size','font_sym_size','font_symt_size']:
            field=(size_field+'\0fp32\0').encode();q=p+child.index(field)+len(field)
            assert struct.unpack_from('<f',data,q)[0]==23
            struct.pack_into('<f',data,q,22)
    assert len(data)==len(body)
    return bytes(data)
def main():
    repair_ui()
    path=ROOT/'06_build/stage/content/menu_handles_storage.bin';raw=path.read_bytes();out=bytearray(raw[:10]);pos=10
    for _ in range(struct.unpack_from('<I',raw,6)[0]):
        idx,n=struct.unpack_from('<II',raw,pos);pos+=8;body=raw[pos:pos+n];pos+=n
        if idx==67:body=patch_record(body)
        out+=struct.pack('<II',idx,len(body))+body
    assert pos==len(raw) and len(out)==len(raw)
    path.write_bytes(out)
    report=dict(controls=CONTROLS,old_alignment='justify',new_alignment='native_right',alignment_value=1,
        font_size=22,invisible_padding=False,loader_timing_unchanged=True,rtl_typewriter_fixed=False,runtime_tested=False)
    (ROOT/'08_qa/audit/loading_ui.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
