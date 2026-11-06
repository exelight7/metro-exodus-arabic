import json,pathlib
p=pathlib.Path('WORKSPACE/MetroExodus_AR/03_translation/review/full_language_r1/combat')
ds=[json.loads(s) for s in (p/'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
amend={3467:('ما الذي يصدر تلك القرقعة هناك بحق الجحيم؟','تصحيح صيغة اسم الصوت والمطابقة.'),4874:('آه، كفى نباحًا، ستجذب السمكة، تبارك اسمه!','إبقاء ضمير لقب السمكة كما ورد his في المرجع الإنجليزي.'),5471:('أيها الحقير... آه... أيها الشرير، فلتذهب إلى الجحيم! أنا... لن أدعك... تفلت بفعلتك...','الأصل الروسي Это тебе так... Не пройдет يحسم التهديد بألا يفلت بفعلته؛ تصحيح العبارة المشوهة دون تغيير معناها.')}
for i,(t,reason) in amend.items(): ds[i].update(decision='change',target=t,reason=reason)
(p/'decisions.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in ds),encoding='utf-8')
for f in p.glob('batch*.json'):
    b=json.loads(f.read_text(encoding='utf-8-sig'))
    changed=False
    for i,(t,reason) in amend.items():
        if b['start']<=i<b['end']: b.setdefault('changes',{})[str(i)]={'decision':'change','target':t,'reason':reason}; changed=True
    if changed: f.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Amended',list(amend))