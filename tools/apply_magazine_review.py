"""Reviewed weapon magazine UI, keyed by original source and scoped to this UI."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
names={
'3-SHOT CYLINDER':'أسطوانة من 3 طلقات','BIG TANK':'خزان كبير','QUADRANT-TYPE MAGAZINE':'مخزن رباعي الشكل',
'EXTENDED MAGAZINE':'مخزن موسع','SMALL MAGAZINE':'مخزن صغير','HIGH CAPACITY MAGAZINE':'مخزن كبير السعة',
'SINGLE COLUMN MAGAZINE':'مخزن أحادي الصف','SMALL TANK':'خزان صغير','ROTOR MAGAZINE':'مخزن دوار',
'NO MAGAZINE':'بلا مخزن','HORIZONTAL MAGAZINE':'مخزن أفقي','STANDARD MAGAZINE':'مخزن قياسي',
'STAGGERED MAGAZINE':'مخزن مزدوج الصف','HELICAL MAGAZINE':'مخزن حلزوني','MAGAZINE':'مخزن الذخيرة',
'6-SHOT CYLINDER':'أسطوانة من 6 طلقات','STANDARD TANK':'خزان قياسي','EXTENDED TANK':'خزان موسع',
'8-SHOT CYLINDER':'أسطوانة من 8 طلقات','6-SHOT DOUBLE-ACTION CYLINDER':'أسطوانة مزدوجة الفعل من 6 طلقات',
'FIXED CYLINDER':'أسطوانة ثابتة','MEDIUM MAGAZINE':'مخزن متوسط','TUBE MAGAZINE':'مخزن أنبوبي',
'SMALL CYLINDER':'أسطوانة صغيرة','BOX MAGAZINE':'مخزن صندوقي','SHOTGUN MAGAZINE':'مخزن بندقية خرطوش'}
descriptions={
'huge_vyhlop':'مخزن ضخم يتسع لـ60 طلقة.',
'revolver_std_da':'أسطوانة من 6 حجرات بآلية مزدوجة الفعل تزيد معدل إطلاق المسدس الدوار بدرجة كبيرة.',
'shotgun_drum_3':'نسخة أصغر من أسطوانة بندقية الخرطوش. تتسع لثلاث طلقات فقط، لكن يمكن استبدالها بسرعة بأخرى.',
'revolver_small':'أسطوانة من 3 حجرات بآلية أحادية الفعل. ليست الخيار الأفضل، لكنها أفضل من لا شيء.',
'big':'مخزن كبير يتسع لما يصل إلى 45 طلقة. ثقيل نسبيًا.',
'kolya_big':'مخزن كبير يتسع لـ16 طلقة، ووزنه ثقيل بوضوح.',
'043_huge':'يتسع المخزن الموسع لما يصل إلى 15 طلقة. وعند استخدامه مع آلية نصف آلية، يزيد معدل الإطلاق بدرجة كبيرة على حساب الدقة والضرر الملحق بالهدف.',
'ubludok_small':'مخزن صغير يتسع لـ15 طلقة. أخف الخيارات المتاحة.',
'kolya_huge':'مخزن ضخم يتسع لما يصل إلى 32 طلقة. هو الأثقل، وقد يؤثر على ثبات التصويب.',
'sammy_small':'مخزن صغير صُمم خصيصًا لهذه البندقية. يحسن سهولة استخدامها ودقتها بتعديل توازنها، ويتسع لما يصل إلى 11 طلقة عادية أو حارقة.',
'':'مخزن قياسي يتسع لـ30 طلقة.',
'sammy_std':'مخزن قياسي صُمم خصيصًا لهذه البندقية، ويتسع لما يصل إلى 30 طلقة عادية أو حارقة.',
'revolver_std_sa':'أسطوانة من 6 حجرات بآلية أحادية الفعل. التصميم الكلاسيكي للمسدس سداسي الطلقات.',
'flame_big':'طفاية حريق معدنية أعيد تجهيزها لتخزين كمية كبيرة من الوقود، لكنها تجعل قاذف اللهب أثقل وأكبر حجمًا بكثير.',
'helsing_std':'أثقل من المخزن الصغير، لكنه يتسع لـ3 سهام.',
'ubludok_huge':'مخزن يتسع لما يصل إلى 100 طلقة. هو الأثقل، وقد يؤثر على ثبات التصويب.',
'043_small':'التصميم المعتاد للبنادق القديمة: طلقة واحدة فقط في حجرة الإطلاق.',
'flame_std':'ثلاثة خزانات بلاستيكية لطفايات حريق موصولة على التوالي، توفر كمية الوقود المثالية لقاذف لهب محمول.',
'shotgun_box_10':'مخزن كبير لبندقية الخرطوش يتسع لـ10 طلقات.',
'kolya_small':'مخزن صغير يتسع لـ8 طلقات. أخف الخيارات المتاحة.',
'makeshift_std':'مخزن أسطواني يتسع لـ18 كرة فولاذية أو 6 كبسولات.',
'ubludok_big':'مخزن كبير يتسع لـ50 طلقة، وثقيل نسبيًا.',
'revolver_big':'أسطوانة من 8 حجرات بآلية مزدوجة الفعل. لعلها أفضل أسطوانة يمكنك العثور عليها في عالم ما بعد الحرب.',
'helsing_big':'مخزن أسطواني كبير يتسع لما يصل إلى 6 سهام، ووزنه أثقل بوضوح.',
'gatling_small':'مخزن رباعي الشكل يتسع لما يصل إلى 75 طلقة، ويشغل حيزًا أقل بكثير من المخازن القرصية.',
'makeshift_small':'مخزن صغير مرتجل الصنع يتسع لما يصل إلى 9 كرات فولاذية أو 3 كبسولات.',
'043_big':'مخزن موسع يتسع لـ10 طلقات مرتبة في صفين متداخلين. تتيح آلية الترباس مستقيم السحب تلقيم الطلقة وإطلاقها مع إبقاء الهدف تحت المراقبة عبر المنظار.',
'huge':'مخزن ضخم يتسع لـ75 طلقة. أثقل الخيارات المتاحة.',
'ubludok_std':'مخزن قياسي يتسع لما يصل إلى 30 طلقة.',
'043':'مخزن أحادي الصف يتسع لـ5 طلقات. تتيح آلية الترباس مستقيم السحب تلقيم الطلقة وإطلاقها مع إبقاء الهدف تحت المراقبة عبر المنظار.',
'shotgun_belt':'مخزن صندوقي يتسع لـ20 طلقة. يمكن فصله عن السلاح واستبداله بآخر، لكن ذلك يستغرق وقتًا.',
'flame_small':'خزان صغير وخفيف مأخوذ من موقد محمول، يحتوي على كمية قليلة من الوقود.',
'small':'مخزن صغير يتسع لـ20 طلقة، خفيف وصغير الحجم.',
'helsing_small':'أبسط المخازن وأخفها، يحمل سهمًا واحدًا فوق القوس.',
'sammy_huge':'مخزن ضخم صُمم خصيصًا لهذه البندقية. قد يؤثر وزنه على ثبات التصويب ودقته، لكنه يتسع لما يصل إلى 100 طلقة عادية أو حارقة.',
'makeshift_ext':'نسخة موسعة من المخزن الأنبوبي، تتسع لـ27 كرة فولاذية أو 9 كبسولات.',
'helsing_huge':'مخزن أسطواني ضخم يتسع لـ8 سهام. أثقل بكثير من بقية المخازن، لكنه يقلل الحاجة إلى إعادة التلقيم.',
'flame_huge':'يجعل الخزان الموسع قاذف اللهب ثقيلًا جدًا وصعب الاستخدام، لكنه يوفر احتياطيًا هائلًا من الوقود.',
'shotgun_drum_6':'حامل يتسع لست طلقات خرطوش، ويوفر أفضل سرعة تلقيم ومعدل إطلاق يمكن أن تحققهما بندقية خرطوش.',
'makeshift_huge':'مخزن حلزوني يستخدم لولبًا دوارًا لحمل ما يصل إلى 36 كرة فولاذية أو 12 كبسولة.'}
rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
path=ROOT/'03_translation/overrides_by_id.json';overrides=json.loads(path.read_text(encoding='utf-8'));edits=[]
for r in rows:
    key=r['id'];prefix='menu_customize_magazine'
    if not key.startswith(prefix):continue
    if key.endswith('_name'):target=names[r['source']]
    elif key.endswith('_dsc'):target=descriptions[key[len(prefix):-4].lstrip('_')]
    else:raise ValueError(key)
    overrides[key]=target;edits.append({'id':key,'source':r['source'],'target':target})
path.write_text(json.dumps(overrides,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'03_translation/review/magazine_review_receipt.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'reviewed_magazine_entries':len(edits)}))
