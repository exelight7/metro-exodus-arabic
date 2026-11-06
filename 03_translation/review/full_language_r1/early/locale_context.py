import json,pathlib,sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,r'USER_HOME\.codex\skills\foura-dialogue\scripts')
from foura_dialogue import LNG
p=pathlib.Path(__file__).parent
rows=[json.loads(s) for s in (p/'input.jsonl').read_text(encoding='utf-8').splitlines()]
lang=sys.argv[1]
loc=LNG((pathlib.Path(r'WORKSPACE\MetroExodus_AR\02_extracted\steam_local\patch_04\content\localization')/f'stable_{lang}.lng').read_bytes()).texts
for s in sys.argv[2:]:
 i=int(s);r=rows[i]
 print(f"[{i}] {r['id']}\nEN {r['source']}\nAR {r['target']}\n{lang.upper()} {loc.get(r['id'],'<missing>')}")
