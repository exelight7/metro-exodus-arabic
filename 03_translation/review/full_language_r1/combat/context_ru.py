import json,pathlib,sys
sys.path.insert(0,'USER_HOME/.codex/skills/foura-dialogue/scripts')
from foura_dialogue import LNG
root=pathlib.Path(__file__).resolve().parent
rows=[json.loads(s) for s in (root/'input.jsonl').read_text(encoding='utf-8').splitlines()]
ru=LNG(pathlib.Path('WORKSPACE/MetroExodus_AR/02_extracted/steam_local/patch_04/content/localization/stable_ru.lng').read_bytes()).texts
indices=[int(s) for s in sys.argv[1:]]
if not indices:
    ds=[json.loads(s) for s in (root/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
    indices=[i for i,d in enumerate(ds) if d['decision']=='needs_context']
for i in indices:
    r=rows[i]
    print(str(i)+' '+r['id']+'\nEN '+r['source']+'\nAR '+r['target']+'\nRU '+ru.get(r['id'],'MISSING'))