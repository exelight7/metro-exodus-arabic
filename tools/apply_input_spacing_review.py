"""Add a readable ordinary-space gap on both sides of the skip button."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=ROOT/'03_translation/overrides_by_id.json';d=json.loads(p.read_text(encoding='utf-8'))
    for key,tag in [('video_skip_hint','<menu_ok>'),('video_skip_hint_cstm','<xpad_x>'),('video_skip_hint_xbox','<xpad_x>')]:
        d[key]='اضغط على  '+tag+'  للتخطي'
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Reviewed skip spacing: keyboard, custom controller and Xbox; dynamic bindings preserved')
if __name__=='__main__':main()
