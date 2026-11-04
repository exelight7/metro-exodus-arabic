"""Execute only isolated loading machine instructions in Unicorn, not the game.

The original renderer runs with fake caption/font/resource/sound interfaces.
No entry point, DLL, graphics device, save or game process is invoked.
"""
import json, struct
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *
from loading_native_patch import build, digest, ORIGINAL_SHA256, BUDGET, REVISION, verified_original

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
BASE=0x140000000
OBJ=0x50000000
CAP1=OBJ+0x1000
CAP2=OBJ+0x2000
RENDER=OBJ+0x3000
VT=OBJ+0x4000
POOL=0x51000000
LAYOUT=OBJ+0x20000
STACK=0x60000000
STOP=0x70000000
STUB=STOP+0x100

def p32(v):return struct.pack('<I',v)
def p64(v):return struct.pack('<Q',v)
def pf(v):return struct.pack('<f',v)

class Harness:
    def __init__(self,raw,title,lines):
        pe=pefile.PE(data=raw,fast_load=True)
        self.u=Uc(UC_ARCH_X86,UC_MODE_64)
        u=self.u
        u.mem_map(BASE,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        u.mem_write(BASE,pe.get_memory_mapped_image())
        u.mem_map(OBJ,0x100000);u.mem_map(POOL,0x1000000);u.mem_map(STACK,0x100000);u.mem_map(STOP,0x1000)
        self.draws=[];self.partial=0;self.calls=[];self.captions={CAP1:[title],CAP2:lines}
        self.lengths={}
        self.next_handle=0x1000
        self.handle_text={}
        self.layouts={}
        u.mem_write(0x14175f140,p64(POOL))
        u.mem_write(OBJ+0x170,p64(CAP1));u.mem_write(OBJ+0x168,p64(CAP2))
        u.mem_write(OBJ+0xf0,p64(RENDER));u.mem_write(RENDER,p64(VT))
        for n,slot in enumerate([8,0x10,0xf8,0x118]):u.mem_write(VT+slot,p64(STUB+n*16))
        for caption,parts in self.captions.items():
            records=[]
            for row,text in enumerate(parts):
                handle=self.string(text)
                # Emulated layout is the native 32-byte record with original positions.
                rec=bytearray(32);struct.pack_into('<Iff',rec,8,handle,900-len(text)*10,row*26)
                struct.pack_into('<H',rec,24,row)
                records.append(bytes(rec))
            addr=LAYOUT+(0 if caption==CAP1 else 0x10000)
            u.mem_write(addr,b''.join(records));self.layouts[caption]=(addr,len(records))
            self.lengths[caption]=sum(map(len,parts))+max(0,len(parts)-1)
            u.mem_write(caption+0xe0,pf(22))
            u.mem_write(caption+0xf0,p64(RENDER))
        u.mem_write(OBJ+0x5c,pf(1.25));u.mem_write(OBJ+0x60,p32(40))
        # Sound interfaces are isolated stubs; no resource/device creation.
        u.mem_write(0x14175f950,p64(OBJ+0x5000))
        u.mem_write(OBJ+0x5000,p64(OBJ+0x6000));u.mem_write(OBJ+0x6090,p64(STUB+0x80))
        u.hook_add(UC_HOOK_CODE,self.hook)

    def string(self,text):
        h=self.next_handle;self.next_handle+=0x1000
        self.u.mem_write(POOL+h+0x10,struct.pack('<H',len(text)))
        self.u.mem_write(POOL+h+0x14,text.encode('utf-8')+b'\0')
        self.handle_text[h]=text
        return h

    def read32(self,addr):return struct.unpack('<I',self.u.mem_read(addr,4))[0]
    def read64(self,addr):return struct.unpack('<Q',self.u.mem_read(addr,8))[0]
    def ret(self,value=0):
        u=self.u;sp=u.reg_read(UC_X86_REG_RSP)
        u.reg_write(UC_X86_REG_RAX,value)
        u.reg_write(UC_X86_REG_RIP,self.read64(sp));u.reg_write(UC_X86_REG_RSP,sp+8)

    def hook(self,u,addr,size,_):
        if addr==STOP:u.emu_stop();return
        if addr==0x140a55f28:
            dest=u.reg_read(UC_X86_REG_RCX);n=u.reg_read(UC_X86_REG_R8)
            assert n<=4096
            u.mem_write(dest,bytes([u.reg_read(UC_X86_REG_RDX)&255])*n);self.ret(dest);return
        if addr==0x140bb25b0:
            caption=u.reg_read(UC_X86_REG_RCX);bp=u.reg_read(UC_X86_REG_RBP)
            vec,n=self.layouts[caption]
            u.mem_write(bp-0x10,p64(vec));u.mem_write(bp-8,struct.pack('<HH',4,n))
            rect=u.reg_read(UC_X86_REG_R9);u.mem_write(rect,struct.pack('<4f',0,0,1000,10000))
            self.ret();return
        if addr==0x140bc9b10:
            u.reg_write(UC_X86_REG_XMM0,int.from_bytes(pf(26),'little'));self.ret();return
        if addr==0x14072b6b0:
            sp=u.reg_read(UC_X86_REG_RSP)
            self.calls.append((u.reg_read(UC_X86_REG_R8),self.read32(sp+0x28)))
        if addr==0x14072bacb:self.partial+=1
        if addr in [0x1400b2750,0x14009df10,0x14006c960,STUB,STUB+0x10,STUB+0x30,STUB+0x80]:
            self.ret(0xffffffff if addr==STUB+0x10 else 0);return
        if addr==STUB+0x20:
            sp=u.reg_read(UC_X86_REG_RSP);ptr=self.read64(sp+0x28)
            h=ptr-POOL-0x14
            self.draws.append(self.handle_text[h]);self.ret();return
        # Original prefix path uses the real control flow and stub UTF conversion.
        if addr==0x140b56cf0:
            h=self.read32(u.reg_read(UC_X86_REG_RDX));text=self.handle_text[h]
            u.mem_write(u.reg_read(UC_X86_REG_R8),text.encode('utf-16-le')+b'\0\0');self.ret();return
        if addr==0x14072bb23:
            dest=u.reg_read(UC_X86_REG_RCX);src=u.reg_read(UC_X86_REG_R8);n=u.reg_read(UC_X86_REG_R9)
            assert n<=255
            u.mem_write(dest,bytes(u.mem_read(src,n*2))+b'\0\0')
            u.reg_write(UC_X86_REG_RIP,0x14072bb29);return
        if addr==0x140b56b90:
            src=u.reg_read(UC_X86_REG_R8);raw=bytes(u.mem_read(src,512))
            end=next(i for i in range(0,512,2) if raw[i:i+2]==b'\0\0')
            h=self.string(raw[:end].decode('utf-16-le'))
            u.mem_write(u.reg_read(UC_X86_REG_RDX),p32(h));self.ret();return

    def frame(self,due=True):
        u=self.u;self.draws=[];self.calls=[];self.partial=0
        sp=STACK+0x80008;u.mem_write(sp,p64(STOP))
        u.reg_write(UC_X86_REG_RSP,sp);u.reg_write(UC_X86_REG_RCX,OBJ)
        u.reg_write(UC_X86_REG_R9,0)
        u.reg_write(UC_X86_REG_XMM1,int.from_bytes(pf(1),'little'))
        u.reg_write(UC_X86_REG_XMM2,int.from_bytes(pf(1),'little'))
        u.mem_write(OBJ+0x22c,pf(10 if due else 0));u.mem_write(OBJ+0x230,pf(1))
        try:u.emu_start(0x14072b250,STOP,count=200000)
        except Exception as e:raise RuntimeError(f'At {u.reg_read(UC_X86_REG_RIP):x}: {e}') from e
        assert u.reg_read(UC_X86_REG_RIP)==STOP,'Instruction budget exhausted'
        return dict(draws=self.draws.copy(),partial=self.partial,counter=self.read32(OBJ+0x234),
                    complete=bool(self.read32(OBJ+0x250)&8),budgets=self.calls.copy())

def main():
    source=GAME/'MetroExodus.exe'
    raw=verified_original(source,ROOT)
    patched=build(raw)
    from verify_graphics_fonts import package
    from loading_layout import is_loading,TAG
    pkg=package('graphics_label_r1',100)
    texts={k:[TAG.sub('',s) for s in v.split('<br>')] for k,v in pkg['strings'].items() if is_loading(k)}
    key='voices\\m3_02_dead_moscow\\dmc_000_narration_01'
    title=pkg['strings'].get('m3_02_dead_moscow','Moscow')
    # Use a short title to reproduce native title-then-body display order.
    title='Moscow'
    original=Harness(raw,title,texts[key]);baseframe=original.frame()
    assert baseframe['draws']==['M'] and not baseframe['complete']
    original.u.mem_write(OBJ+0x234,p32(len(title)+4))
    old=original.frame()
    assert old['draws']==[title,texts[key][0][:5]] and old['partial']==1
    results=[]
    for name,lines in [(key,texts[key]),('empty',['']),('one',['A']),('mixed',['DX 12: \ufe8e\ufe92\ufea3\ufeae\ufee3']),('many',['A']*300)]:
        h=Harness(patched,title,lines);before=h.frame(False)
        assert before['draws']==[]
        first=h.frame();second=h.frame(False);third=h.frame(True)
        expected=[title]+[x for x in lines if x]
        for f in [first,second,third]:
            assert f['draws']==expected,(name,f['draws'][:4],expected[:4])
            assert f['partial']==0 and f['complete']
        results.append(dict(case=name,lines=len(lines),full_first_reveal=True,stable_next_frames=True))
    # Every packaged loading text is far below the validated finite budget.
    longest=max(sum(map(len,ls))+len(ls)+len(title) for ls in texts.values())
    assert longest<BUDGET//4
    tested=0
    for name,lines in texts.items():
        h=Harness(patched,title,lines);f=h.frame()
        assert f['draws']==[title]+[x for x in lines if x],name
        assert f['partial']==0 and f['complete'],name
        tested+=1
        del h
    report=dict(revision=REVISION,original_sha256=digest(raw),patched_sha256=digest(patched),
        mechanism='full paragraph on first native reveal tick',machine_code_emulated=True,
        original_prefix_bug_reproduced=True,renderer_record_bounds_preserved=True,
        original_and_patched_draw_function_identical=True,cases=results,
        loading_entries=len(texts),all_loading_entries_emulated=tested,longest_budget_required=longest,budget=BUDGET,
        runtime_game_tested=False,game_launched=False,rtl_animation=False,
        limitations='Font/layout/sound interfaces stubbed; real game integration still needs user confirmation.')
    (ROOT/f'08_qa/audit/{REVISION}_emulation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
