"""Preserve current loading/subtitle fixes and right-align the three reading UIs."""
import json,re,struct
from pathlib import Path
from build_loading_ui import main as build_loading
ROOT=Path(__file__).resolve().parents[1]
TARGETS={42:('hint_desc','hint_caption','layer_name'),88:('hint_desc','hint_caption'),100:('hint_desc','hint_caption')}

def patch_record(body,record_id):
    data=bytearray(body)
    for name in TARGETS[record_id]:
        marker=b'\3'+name.encode()+b'\0type\0u32\0';assert data.count(marker)==1
        pos=data.index(marker);n=struct.unpack_from('<I',data,pos-4)[0];c=data[pos:pos+n]
        field=b'h_alignment\0u8\0';q=pos+c.index(field)+len(field)
        assert data[q] in [0,3];data[q]=1
        if name=='hint_caption':
            # Share the body column's right edge, including longer Arabic titles.
            source=b'\3hint_desc\0type\0u32\0';s=data.index(source);m=struct.unpack_from('<I',data,s-4)[0];desc=data[s:s+m]
            for f in ['position_x','size_x']:
                field=(f+'\0s32\0').encode();a=pos+c.index(field)+len(field);b=desc.index(field)+len(field)
                data[a:a+4]=desc[b:b+4]
    assert len(data)==len(body)
    return bytes(data)

def main():
    build_loading()
    path=ROOT/'06_build/stage/content/menu_handles_storage.bin';b=path.read_bytes();out=bytearray(b[:10]);pos=10;changed=[]
    for _ in range(struct.unpack_from('<I',b,6)[0]):
        i,n=struct.unpack_from('<II',b,pos);pos+=8;c=b[pos:pos+n];pos+=n
        if i in TARGETS:c=patch_record(c,i);changed.append(i)
        out+=struct.pack('<II',i,len(c))+c
    assert pos==len(b) and changed==sorted(TARGETS)
    path.write_bytes(out)
    report=dict(changed_records=changed,alignment='Right=1; formerly Justify=3 for prose',
        title_right_edge_matches_body=True,fonts_and_scroll_controls_preserved=True,runtime_tested=False)
    (ROOT/'08_qa/audit/diary_ui.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
