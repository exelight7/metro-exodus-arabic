import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROWS = [json.loads(x) for x in (BASE / 'input.jsonl').read_text(encoding='utf-8').splitlines()]

def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['show', 'commit', 'stats'])
parser.add_argument('start', type=int, nargs='?', default=0)
parser.add_argument('count', type=int, nargs='?', default=50)
parser.add_argument('--changes')
args = parser.parse_args()
if args.mode == 'show':
    for n in range(args.start, min(len(ROWS), args.start + args.count)):
        row = ROWS[n]
        print(f"[{n}] {row['id']}\nEN: {row['source']}\nAR: {row['target']}")
elif args.mode == 'commit':
    progress = json.loads((BASE / 'progress.json').read_text(encoding='utf-8'))
    if progress['next_index'] != args.start:
        raise ValueError('Only consecutive, previously unread ranges may be recorded')
    overrides = json.loads(Path(args.changes).read_text(encoding='utf-8')) if args.changes else {}
    stop = min(len(ROWS), args.start + args.count)
    batch = []
    for n in range(args.start, stop):
        row = ROWS[n]
        decision = overrides.pop(str(n), None)
        if decision is None:
            nontext = not row['source'].strip() or not any(c.isalpha() for c in row['source'])
            decision = {'decision': 'nontranslatable' if nontext else 'keep',
                        'reason': 'خانة فارغة أو رمز أو قيمة عددية أصلية.' if nontext else 'قورنت بالأصل والسياق المتاح؛ الصياغة الحالية سليمة ومناسبة.'}
        if decision['decision'] == 'change':
            assert decision['target'] != row['target'], (n, 'unchanged proposal')
            assert decision['target'].strip(), (n, 'empty proposal')
        batch.append({'id': row['id'], 'row': row['row'], **decision})
    if overrides:
        raise ValueError(f'Proposals outside batch: {list(overrides)}')
    with (BASE / 'decisions.jsonl').open('a', encoding='utf-8', newline='\n') as out:
        out.write(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in batch))
    progress.update(reviewed=stop, next_index=stop, complete=stop == len(ROWS))
    save_json(BASE / 'progress.json', progress)
    print(json.dumps(progress))
else:
    from collections import Counter
    print(Counter(x['id'].split('\\')[0].split('/')[0] for x in ROWS))
