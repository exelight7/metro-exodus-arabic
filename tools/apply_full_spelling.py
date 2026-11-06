"""Apply the conservative spelling pass to every row; preserve translation status."""
from pathlib import Path
import collections,csv,hashlib,json,shutil,sys
from arabic_spelling import correct_spelling,FULL
ROOT=Path(__file__).resolve().parents[1]

def main():
    table=ROOT/'03_translation/tables/game.csv'
    backup=ROOT/'03_translation/review/spelling_full_baseline.csv'
    if backup.exists():
        if '--refresh' not in sys.argv:raise ValueError('Review baseline already exists; inspect before rerunning.')
        previous=json.loads((ROOT/'08_qa/audit/spelling_full_r1.json').read_text(encoding='utf-8'))
        assert hashlib.sha256(table.read_bytes()).hexdigest()==previous['target_sha256'],'Table changed since this review'
    else:shutil.copy2(table,backup)
    with backup.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    import re
    protected=re.compile(r'<[^>]+>|\{[^}]+\}|%\d*\$?[sdif]|\\[nrt]')
    changes=[]
    for row in rows:
        before=row['target'];after=correct_spelling(row['id'],before)
        assert collections.Counter(protected.findall(before))==collections.Counter(protected.findall(after)),row['id']
        assert correct_spelling(row['id'],after)==after,row['id']
        if before!=after:
            changes.append(dict(id=row['id'],source=row['source'],before=before,after=after,
                                kind='context' if row['id'] in FULL else 'spelling_or_spacing'))
            row['target']=after
    with table.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    report=dict(revision='spelling_full_r1',rows_scanned=len(rows),changed_rows=len(changes),
                original_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                target_sha256=hashlib.sha256(table.read_bytes()).hexdigest(),
                protected_formats_preserved=True,translation_statuses_preserved=True,
                manual_full_prose_review=False,game_launched=False,live_game_written=False,changes=changes)
    (ROOT/'08_qa/audit/spelling_full_r1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
if __name__=='__main__':main()
