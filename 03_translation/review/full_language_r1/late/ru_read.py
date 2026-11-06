import pathlib,sys
sys.dont_write_bytecode=True
sys.path.insert(0,r'USER_HOME/.codex/skills/foura-dialogue/scripts')
from foura_dialogue import LNG
from review_io import ROWS
ru=LNG(pathlib.Path(r'WORKSPACE/MetroExodus_AR/02_extracted/steam_local/patch_04/content/localization/stable_ru.lng').read_bytes()).texts
for v in sys.argv[1:]:
    i=int(v);x=ROWS[i]
    print(i,x['id'],'\nEN',x['source'],'\nAR',x['target'],'\nRU',ru.get(x['id'],'MISSING'))
