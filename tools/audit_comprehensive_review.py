"""Broad candidate inventory; flags are review leads, never automatic corrections."""
import csv,json,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def category(key):
    if key.startswith('voices\\'):return 'dialogue'
    if 'task' in key:return 'tasks'
    if any(s in key for s in ['diary','m3_dia_','journal']):return 'notes_and_journal'
    if 'hint' in key or 'tutorial' in key:return 'hints'
    if any(s in key for s in ['ammo','wpn','customize','gatling','weapon']):return 'equipment'
    if 'credits' in key or any(s in key for s in ['eula','legal','copyright','license']):return 'credits_and_legal'
    return 'interface_and_other'
def main():
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    patterns={
        'photography':r'التصوير',
        'literal_down':r'العدو أسفل',
        'dialect':r'كده|تفتكر|عايز|مش عارف|يا عم|دلوقتي|عشان',
        'order_aurora':r'الأمر|الشفق',
        'literal_sex':r'يمارس الجنس|الجنس مع|اللعنة معي',
        'literal_prose':r'العيون المؤلمة|صيد الفطر|أستطيع إدارة|حصلت على الجشع|كنت بالخارج',
        'equipment_phonetics':r'كرواتش|كراوتش|ميدكيت|ستيلث|كرافتينغ|شوتجن|سنايبر|ريلود|توجل|فيلتر',
    }
    counts={};allhits=[]
    for name,pattern in patterns.items():
        hits=[dict(id=r['id'],source=r['source'],target=r['target'],category=category(r['id'])) for r in rows if re.search(pattern,r['target']) and category(r['id'])!='credits_and_legal']
        counts[name]=len(hits)
        allhits.extend(dict(check=name,**r) for r in hits)
    report=dict(rows_scanned=len(rows),categories=dict(collections.Counter(category(r['id']) for r in rows)),candidate_counts=counts,
        scope='Pattern inventory across every extracted row, not proof of complete manual proofreading.',candidates=allhits)
    (ROOT/'08_qa/audit/comprehensive_candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='candidates'}))
if __name__=='__main__':main()
