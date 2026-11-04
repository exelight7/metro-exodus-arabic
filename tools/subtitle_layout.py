"""Logical-first Arabic subtitles: timed boundaries, wrapping and speaker order."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/vendor/game-arabization'))
from ar_shape import Shaper,Measurer
from loading_layout import LoadingLayout,is_loading
from diary_layout import DiaryLayout,profile as diary_profile
from input_spacing import normalize_input_spacing
TIME=re.compile(r'(<time=\d+>)')
TAG=re.compile(r'<[^>]+>')

class GameRenderer:
    def __init__(self):
        overrides=json.loads((ROOT/'03_translation/overrides_by_id.json').read_text(encoding='utf-8'))
        records=json.loads((ROOT/'02_extracted/steam_local/dramatis_records.json').read_text())
        self.actors={records['strings'][v[2]] for v in records['records']} - {''}
        self.names={key:overrides[key].strip().rstrip(':').strip() for key in self.actors}
        self.speakers=json.loads((ROOT/'02_extracted/steam_local/speaker_map.json').read_text())
        options=dict(mode='visual',base='rtl',harakat='strip',normalize_persian=True,newline_tokens=['\n','<br>'])
        self.plain=Shaper(**options)
        self.dialogue=Shaper(**options,measurer=Measurer(chars=60),wrap_sep='<br>')
        self.prose=Shaper(**options,measurer=Measurer(chars=60),wrap_sep='<br>')
        self.description=Shaper(**options,measurer=Measurer(chars=35),wrap_sep='<br>')
        self.loading=LoadingLayout(Shaper,options)
        self.diary=DiaryLayout(Shaper,options)
        self.stats=dict(integrated_speaker_entries=0,timed_entries=0)

    def render(self,key,text):
        text=normalize_input_spacing(key,text)
        # Empty native prefix labels prevent the engine from adding a second
        # LTR name before a line whose name is now included in its RTL layout.
        if key in self.actors:return ''
        if is_loading(key) and not TIME.search(text):
            return self.loading.render(key,text) if re.search('[\u0600-\u06ff]',text) else text
        if diary_profile(key) and not TIME.search(text):
            return self.diary.render(key,text) if re.search('[\u0600-\u06ff]',text) else text
        persona=self.speakers.get(key,'') if not key.endswith('_deaf') else ''
        name=self.names.get(persona,'')
        if name:self.stats['integrated_speaker_entries']+=1
        is_dialogue=key.startswith('voices\\') or bool(TIME.search(text))
        is_description=key.startswith(('standard_mode_dsc','ranger_mode_dsc','$game_difficulty')) and len(text)>80
        shaper=self.dialogue if is_dialogue else self.description if is_description else self.prose if len(TAG.sub('',text))>80 else self.plain
        parts=TIME.split(text)
        if len(parts)>1:self.stats['timed_entries']+=1
        result=[]
        for part in parts:
            if TIME.fullmatch(part) or not TAG.sub('',part).strip():result.append(part);continue
            logical=part
            if is_dialogue:
                logical=re.sub(r'\s*(<(?:ffx:|ds_priority:)[^>]+>)\s*',r' \1 ',logical)
                if name:logical=name+':   '+logical.lstrip()
            if re.search('[\u0600-\u06ff]',logical):
                visual=shaper.process(logical)
            else:visual=logical
            result.append(visual)
        rendered=''.join(result)
        assert TIME.findall(rendered)==TIME.findall(text),key
        return rendered
