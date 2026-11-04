"""Shape and wrap logical Arabic against the game's actual bitmap advances.

Right alignment uses invisible, measurable spacer glyphs, not bidi control
characters that this engine ignores. Screen rectangles remain unchanged.
"""
import json,re,struct,zlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPACERS={chr(0xE100+i):1<<i for i in range(15)}
TAG=re.compile(r'<[^>]+>')
ICON=re.compile(r'<(?!(?:br|tab|time|ffx|ds_priority)(?:[>:]))[A-Za-z_][A-Za-z_0-9]*>')

def records(b):
    p=10
    for _ in range(struct.unpack_from('<I',b,6)[0]):
        idx,n=struct.unpack_from('<II',b,p);p+=8;yield idx,b[p:p+n];p+=n
    assert p==len(b)

def profiles():
    result={}
    raw=(ROOT/'02_extracted/steam_local/patch_04/content/menu_handles_storage.bin').read_bytes()
    for idx,body in records(raw):
        # Caption controls contain a real text rectangle and font, unlike
        # shader render_mode or anchoring fields, which must not be flipped.
        for m in re.finditer(rb'\x03([A-Za-z0-9_ -]{1,100})\0type\0u32\0....',body,re.S):
            start=m.start();crc,n=struct.unpack_from('<II',body,start-8)
            if crc!=zlib.crc32(m[1]) or start+n>len(body):continue
            control=body[start:start+n]
            def val(name,typ,fmt):
                q=control.index(name.encode()+b'\0'+typ.encode()+b'\0')+len(name)+len(typ)+2
                return struct.unpack_from('<'+fmt,control,q)[0]
            def string(name):
                mark=name.encode()+b'\0stringz\0';q=control.index(mark)+len(mark)
                return control[q:control.index(0,q)].decode()
            try:
                caption_pos=control.index(b'caption\0stringz\0')
                nested=re.search(rb'\x03[A-Za-z0-9_ -]{1,100}\0type\0u32\0',control[m.end()-m.start():caption_pos])
                if nested:continue
                w=val('size_x','s32','i')
                try:size=val('font_size','fp32','f')
                except ValueError:size=val('font_size','u16','H')
                font=string('font_name');key=string('caption')
            except (ValueError,struct.error):continue
            if font not in ('regular','menu','typewriter') or w<100 or not 8<=size<=80 or not key:continue
            profile=dict(font=font,width=w,size=size,menu=idx,control=m[1].decode())
            if key not in result or w/size<result[key]['width']/result[key]['size']:result[key]=profile
    return result

class NativeMeasurer:
    def __init__(self,advances,limit):self.advances=advances;self._limit=limit
    @property
    def limit(self):return self._limit
    def width(self,units):
        return sum((56 if ICON.fullmatch(u.text) else 0) if u.is_tag else sum(self.advances.get(c,0) for c in u.text) for u in units if not getattr(u,'is_state',False))

class RTLLayout:
    def __init__(self,shaper_class,options):
        self.metrics=json.loads((ROOT/'04_fonts/maps/native_advances.json').read_text())
        self.profiles=profiles();self.shaper_class=shaper_class;self.options=options
        self.cache={};self.audit={}
    def profile(self,key):
        p=self.profiles.get(key)
        if key.startswith(('m3_general_hint_','m3_dlc01_general_hint_','m3_dlc02_general_hint_')):
            p=self.profiles.get('m3_general_hint_73',p)
        if key.startswith('voices\\') and '_narration' in key:
            # Loading captions are assigned dynamically, not literally in menu.
            p=dict(font='regular',width=418,size=23,menu=67,control='hint_level_narrative')
        if key.startswith('voices\\') and not p:
            p=dict(font='regular',width=500,size=30,menu=51,control='subtitles')
        if key.startswith(('intro','dlc1_intro','dlc2_intro','dlc2_outro')) and not p:
            p=dict(font='regular',width=500,size=30,menu=51,control='subtitles')
        return p
    def render(self,key,logical,dialogue=False):
        p=self.profile(key)
        if dialogue and not p:p=dict(font='regular',width=500,size=30,menu=51,control='subtitles')
        if not p:
            if len(TAG.sub('',logical))<=80:return None
            # Conservative wrapping for prose whose native caption is assigned
            # at runtime and cannot be traced to a particular rectangle yet.
            cachekey=('generic_prose',600)
            if cachekey not in self.cache:
                self.cache[cachekey]=self.shaper_class(**self.options,
                    measurer=NativeMeasurer(self.metrics['regular']['advances'],600),wrap_sep='<br>')
            result=self.cache[cachekey].process(logical.replace('<tab>',''))
            self.audit[key]=dict(profile=None,native_limit=600,line_widths=[],right_alignment_unresolved=True)
            return result
        metric=self.metrics[p['font']]
        # Leave a margin for rasterization and resolution-dependent rounding.
        limit=math.floor((p['width']-12)*metric['line']/p['size'])
        cachekey=(p['font'],limit)
        if cachekey not in self.cache:
            self.cache[cachekey]=self.shaper_class(**self.options,
                measurer=NativeMeasurer(metric['advances'],limit),wrap_sep='<br>')
        # Native tab is an LTR indentation. Arabic indentation follows the right edge.
        rendered=self.cache[cachekey].process(logical.replace('<tab>',''))
        lines=rendered.split('<br>');out=[];widths=[]
        for line in lines:
            if not TAG.sub('',line).strip():out.append(line);continue
            width=sum(metric['advances'].get(c,0) for c in TAG.sub('',line))+56*len(ICON.findall(line))
            # Long unbreakable tokens are kept intact rather than losing content.
            gap=max(0,limit-width);padding=''.join(c for c,w in reversed(SPACERS.items()) if gap&w)
            out.append(padding+line);widths.append(width)
        self.audit[key]=dict(profile=p,native_limit=limit,line_widths=widths)
        return '<br>'.join(out)
