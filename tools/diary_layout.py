"""Metric Arabic layout for notes, the journal and the pause-menu advice pages."""
import json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TAG=re.compile('<[^>]+>')
NOTE=re.compile(r'^m3_(?!loader).*_diary_\d')

def profile(key):
    if NOTE.match(key) and not key.endswith('_name'):return 'note'
    if key.startswith('m3_dia_') and not key.endswith('_title'):return 'journal'
    if key.startswith('m3_pause_menu_hint') and not key.endswith(('_name','_title')):return 'advice'
    return None

class DiaryMeasurer:
    def __init__(self,metrics,width,size):
        self.advances=metrics['advances']
        self.limit=math.floor((width-24)*metrics['line']/size)
    def width(self,units):
        return sum(sum(self.advances[c] for c in u.text) for u in units if not u.is_tag and not getattr(u,'is_state',False))

class DiaryLayout:
    def __init__(self,shaper,options):
        metrics=json.loads((ROOT/'04_fonts/maps/diary_advances.json').read_text(encoding='utf-8'))
        self.measurers={k:DiaryMeasurer(metrics[f],w,s) for k,f,w,s in [('note','regular',650,24),('journal','typewriter',415,18),('advice','regular',650,24)]}
        self.shapers={k:shaper(**options,measurer=m,wrap_sep='<br>') for k,m in self.measurers.items()}
        self.audit={}
    def render(self,key,text):
        kind=profile(key);assert kind
        # Tabs are native LTR indentation instructions. Never reorder a sentence
        # across one: remove them BEFORE shaping the complete logical paragraph.
        clean=text.replace('<tab>',' ')
        clean=re.sub(r'[ \t]+',' ',clean)
        clean=re.sub(r'\s*(<br>)\s*',r'\1',clean)
        clean=re.sub(r'(?:<br>){3,}','<br><br>',clean)
        clean=re.sub(r'^(?:<br>)+|(?:<br>)+$','',clean).strip()
        out=self.shapers[kind].process(clean)
        widths=[sum(self.measurers[kind].advances[c] for c in TAG.sub('',line)) for line in out.split('<br>')]
        assert all(w<=self.measurers[kind].limit for w in widths),(key,max(widths),self.measurers[kind].limit)
        assert '<tab>' not in out and not re.search(' {2,}',TAG.sub('',out)),key
        self.audit[key]=dict(profile=kind,line_widths=widths,limit=self.measurers[kind].limit)
        return out
