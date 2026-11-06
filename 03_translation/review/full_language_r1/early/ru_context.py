import json,pathlib,sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,r'USER_HOME\.codex\skills\foura-dialogue\scripts')
from foura_dialogue import LNG
p=pathlib.Path(__file__).parent
rows=[json.loads(s) for s in (p/'input.jsonl').read_text(encoding='utf-8').splitlines()]
ru=LNG(pathlib.Path(r'WORKSPACE\MetroExodus_AR\02_extracted\steam_local\patch_04\content\localization\stable_ru.lng').read_bytes()).texts
if sys.argv[1:] == ['needs']:
 ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
 ix=[i for i,d in enumerate(ds) if d['decision']=='needs_context']
else:ix=[int(i) for i in sys.argv[1:]]
for i in ix:
 r=rows[i]
 print(f"[{i}] {r['id']}\nEN {r['source']}\nAR {r['target']}\nRU {ru.get(r['id'],'<missing>')}")
