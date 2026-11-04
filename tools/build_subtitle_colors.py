"""Build native white speech/orange name controls from the clean menu database.

No executable changes. The second control uses complementary glyph masks and
the same subtitle stream and geometry. In-engine behavior still needs a user
screenshot: static verification cannot prove native control subscription.
"""
import struct,zlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'02_extracted/steam_local/patch_04/content/menu_handles_storage.bin'

def color(body,name,rgba):
    marker=name.encode()+b'\0vec4i\0';assert body.count(marker)==1
    p=body.index(marker)+len(marker)
    return body[:p]+struct.pack('<4I',*rgba)+body[p+16:]

def patch_record(body):
    raise RuntimeError('Withdrawn after user screenshots showed missing dialogue. Use the single-control main().')
    # Locate the one subtitles child in utils.controls, preserving other menus.
    marker=b'controls\0array\0';p=body.index(marker)+len(marker)
    crc,n=struct.unpack_from('<II',body,p);start=p+8;end=start+n
    array=body[start:end];count_marker=b'controls\0count\0u32\0'
    count_pos=1+len(count_marker)
    assert array[0]==3 and array[1:count_pos]==count_marker
    assert struct.unpack_from('<I',array,count_pos)[0]==1
    child_pos=count_pos+4
    child_crc,child_size=struct.unpack_from('<II',array,child_pos)
    assert child_crc==zlib.crc32(b'subtitles')
    child=array[child_pos+8:child_pos+8+child_size]
    assert child_pos+8+child_size==len(array)
    white=(255,255,255,255);orange=(255,100,0,255)
    speech=color(color(child,'text_color',white),'deaf_color',white)
    names=color(color(child,'text_color',orange),'deaf_color',orange)
    # Give the overlay its own control identity and its own complementary font.
    base_marker=b'hide_base\0';base_name=b'name\0stringz\0subtitles\0'
    base_pos=names.index(base_marker)-9
    base_crc,base_size=struct.unpack_from('<II',names,base_pos)
    base=names[base_pos+8:base_pos+8+base_size]
    assert base.count(base_name)==1
    base=base.replace(base_name,b'name\0stringz\0subtitles_ar_names\0')
    names=names[:base_pos]+struct.pack('<II',base_crc,len(base))+base+names[base_pos+8+base_size:]
    font=b'text_font\0stringz\0regular\0';assert names.count(font)==1
    names=names.replace(font,b'text_font\0stringz\0ar_speaker\0')
    assert names.startswith(b'\x03subtitles\0')
    names=names.replace(b'\x03subtitles\0',b'\x03subtitles_ar_names\0',1)
    # Only the speech control paints the optional background.
    bg=b'color\0color, u32\0';assert names.count(bg)==1
    q=names.index(bg)+len(bg);names=names[:q]+bytes(4)+names[q+4:]
    array=array[:child_pos]+struct.pack('<II',child_crc,len(speech))+speech
    array+=struct.pack('<II',zlib.crc32(b'subtitles_ar_names'),len(names))+names
    array=bytearray(array);struct.pack_into('<I',array,count_pos,2)
    result=body[:p]+struct.pack('<II',crc,len(array))+array+body[end:]
    return result

def main():
    b=SOURCE.read_bytes();assert b[:6]==b'AVER\x07\0'
    count=struct.unpack_from('<I',b,6)[0];pos=10;out=bytearray(b[:10]);changed=[]
    for _ in range(count):
        idx,n=struct.unpack_from('<II',b,pos);pos+=8;body=b[pos:pos+n];pos+=n
        if b'persona_color\0vec4i\0' in body:
            assert body.startswith(b'utils\0')
            # User screenshots prove the two-control masked-font experiment
            # can leave only the names visible. Use the native single control
            # and a full font; keep every part of the subtitle visible.
            body=color(color(body,'text_color',(255,255,255,255)),'deaf_color',(255,255,255,255))
            changed.append(idx)
        out+=struct.pack('<II',idx,len(body))+body
    assert pos==len(b) and changed==[51]
    path=ROOT/'06_build/stage/content/menu_handles_storage.bin';path.write_bytes(out)
    report=dict(modified_records=changed,unrelated_menu_records_preserved=True,
        dialogue_rgba=[255,255,255,255],speaker_rgba=[255,255,255,255],
        method='single_native_subtitle_control_with_full_font',
        orange_speaker_color_pending=True,runtime_tested=False)
    (ROOT/'08_qa/audit/subtitle_colors.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
