"""Combine root-reviewed suggestions; never edits the installed package or source CSV."""
import csv,json,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows={r['id']:r for r in csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig'))}
    context={};receipt=[]
    for name in ['notes','equipment','dialogue','names']:
        p=ROOT/f'03_translation/review/comprehensive_r3_{name}_suggested.json'
        for r in json.loads(p.read_text(encoding='utf-8')):
            key=r['id'];assert key not in context,key
            assert rows[key]['source']==r['source'] and rows[key]['target']==r['before'],key
            context[key]=r['target'];receipt.append(dict(id=key,category=name,source=r['source'],before=r['before'],target=r['target'],reason=r['reason']))
    for name in ['achievements','misc']:
        d=json.loads((ROOT/f'03_translation/comprehensive_r3_{name}.json').read_text(encoding='utf-8'))
        for key,target in d.items():
            assert key not in context,key
            context[key]=target;receipt.append(dict(id=key,category=name,source=rows[key]['source'],before=rows[key]['target'],target=target,reason='Complete English/Arabic source-context review by root.'))
    # Root corrections after independently reading the suggestions and source.
    key='m3_13_nvs_diary_6_dsc'
    context[key]=context[key].replace('كنت جالسا هناك في الأسفل منذ وصول التحذير، بينما أمضيت كل ذلك الوقت','لقد بقيت أنت هناك في الأسفل منذ وصول التحذير، بينما أمضيت أنا كل ذلك الوقت')
    key='m3_12_val_diary_23_dsc'
    context[key]=context[key].replace('ما يكفي لشهر واحد (1)','ما يكفي لشهر واحد')
    key='m3_dia_equip_charger_intro'
    context[key]=context[key].replace('وهي لا تحتفظ بالشحن إلا أفضل بقليل مما يحتفظ دلو بلا قاع بالماء','ولا تفوق قدرتها على الاحتفاظ بالشحن قدرة دلو بلا قاع على الاحتفاظ بالماء إلا قليلا')
    for key in ['$med_dsc','menu_item_medkit_desc']:
        context[key]=context[key].replace('مواد للوقاية من آثار','مواد لمواجهة آثار')
    for key,target in context.items():
        assert collections.Counter(re.findall('<[^>]+>',target))==collections.Counter(re.findall('<[^>]+>',rows[key]['source'])),key
    for r in receipt:r['target']=context[r['id']]
    (ROOT/'03_translation/comprehensive_r3_context.json').write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'03_translation/review/comprehensive_r3_approved.json').write_text(json.dumps(dict(root_reviewed=True,reviewed_entries=len(receipt),changes=receipt,number_in_words_exception={'m3_12_val_diary_23_dsc':'Source 1 mo -> لشهر واحد, identical quantity.'}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(context_entries=len(context),reviewed_by_group=dict(collections.Counter(r['category'] for r in receipt)))))
if __name__=='__main__':main()
