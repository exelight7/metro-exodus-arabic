"""Loading-only metric wrapping before bidi. No invisible padding or reveal edits."""
import json,re,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TAG=re.compile('<[^>]+>')
def is_loading(key):
    return (key.startswith('voices\\') and bool(re.search(r'\\[^\\]*_000_(?:narration|loadscreen)',key))) or key.startswith(('m3_loader_diary_','dlc1_000_narration_text_loadscreen','m3_general_hint_','m3_dlc01_general_hint_','m3_dlc02_general_hint_')) or key=='m3_06_bri_chapter_desc'
class LoadingMeasurer:
    def __init__(self,metrics,width=418,size=22):
        self.advances=metrics['advances']
        self.limit=math.floor((width-12)*metrics['line']/size)
    def width(self,units):
        return sum(0 if u.is_tag else sum(self.advances[c] for c in u.text) for u in units if not getattr(u,'is_state',False))
class LoadingLayout:
    def __init__(self,shaper_class,options):
        metrics=json.loads((ROOT/'04_fonts/maps/loading_advances.json').read_text())
        self.measurer=LoadingMeasurer(metrics)
        self.shaper=shaper_class(**options,measurer=self.measurer,wrap_sep='<br>')
        self.audit={}
    def render(self,key,text):
        # Native tab indents the left edge; remove it from Arabic prose only.
        clean=text.replace('<tab>','')
        clean=re.sub(r'(?:<br>\s*){2,}','<br>',clean)
        clean=re.sub(r'(?:<br>\s*)+$','',clean)
        visual=self.shaper.process(clean)
        widths=[sum(self.measurer.advances[c] for c in TAG.sub('',line)) for line in visual.split('<br>')]
        assert all(w<=self.measurer.limit for w in widths),(key,max(widths),self.measurer.limit)
        self.audit[key]=dict(line_widths=widths,limit=self.measurer.limit)
        return visual
