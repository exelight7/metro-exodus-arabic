"""Reviewed remaining mixed-language speech; preserve original foreign-language flavor."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TARGETS={
0:'<ffx:smile_light>ولا ندم مريرًا لدينا، لا ندم! <ffx:neutral>',
1:'كوستيان، سيلا يتحدث... أوغاد الغابة يتحركون! مزقوا رجالنا وسيطروا على الطريق! وصل أليكس الملقب بالعظمة ورجاله إلى معسكرهم من الجانب الآخر للغابة... لم ينج منهم أحد.',
2:'إنه حي، حمدًا للهِب المقدس! إنه هنا! ذلك الوغد في مكان ما هنا! يجب أن نعثر عليه!',
3:'إد، سام يتحدث مجددًا. كل شيء جاهز، أعدت تسليح جميع الفخاخ!',
4:'آه، أيها الكلب المسعور!',
5:'ذلك الوغد هناك في الأسفل!',
6:'استماعك إلى هذا التسجيل يعني أن اهتمامك باللعبة دفعك إلى خوضها مرة أخرى. إذًا، لم تذهب جهود فريق 4A Games هباءً.',
7:'<ffx:anger>أنت... أتقتل السيد؟! <ffx:disgust>لن تضحك الآن! <ffx:anger>سيعاقبك اللهب! <ffx:smile>فاللهب يعاقب كل من يؤذي السيد! <ffx:neutral>',
8:'<ffx:wonder>بيز سيزغي كيم إيكينين دي <ffx:fear>بيلميدي بولادي؟ شيك! <ffx:neutral>',
9:'<ffx:disgust>يا إلهي... <ffx:anger>أنتم جميعًا جبناء! إنه دخيل، عدو! <ffx:neutral>',
10:'<ffx:wonder>لم نعد نعرف أي الأمور أسوأ؛ <ffx:fear>فلم يعد أحد من رحلة إلى بيت السمكة منذ شهر! <ffx:neutral>',
11:'<ffx:wonder_light>سأدخل في صلب الموضوع: كدت <ffx:sadness_light>أطلق عليه تلك الساحرة المجنونة... <ffx:disgust_light>كان يفترض أن تقتله، <ffx:wonder_light>وقد أعددت كل شيء؛ <ffx:wonder>خطوة، ثم أخرى، وأحقق مرادي، أتفهم؟ <ffx:neutral>',
12:'ما بك؟! آه، إنه حي... اسمعوا! ذلك الوغد هنا، لقد أفقد رجلنا وعيه! لنمسك به ونقدمه قربانًا للهِب المقدس!',
13:'<ffx:anger_light>التنظيم يعاني نقصًا في الرجال بعد معركة D6، وأنت ترحل! <ffx:sadness>الناس بحاجة إليك، وأنت تطارد هوسك الأناني! <ffx:anger_light>',
14:'<ffx:anger_light>أتحاول قتلي من شدة القلق؟ <ffx:fear>ماذا لو لم تعد من السطح في المرة المقبلة؟ <ffx:neutral>',
15:'لضمان الصمت اللاسلكي، <ffx:disgust_light>أُنشئ نظام «الدرع»: <ffx:wonder_light>شبكة من أجهزة التشويش اللاسلكي تغطي موسكو وضواحيها.',
16:'<ffx:smile>لسنا وقادي نار، ولسنا نجارين... <ffx:neutral>',
17:'<ffx:anger>موندا بيرودين أفتوكوليك! <ffx:neutral>',
18:'ماذا؟ أظن أن هناك وغدًا في الأعلى!',
19:'تضم مرحلة التايغا شخصيات محايدة غير قابلة للعب أكثر من أي موقع آخر في إكسودس، وتساعدنا قصصها في رسم صورة المجتمع المحلي.',
20:'<ffx:anger>انتبهوا! تاغي دا، بول بوليب تابيلادو! <ffx:neutral>',
21:'هذا ما كنت أحتاجه!',
22:'<ffx:anger>ألاو كوداي عظيم، ألاو كوداي حكيم، ألاو كوداي قوي!<ffx:neutral>',
23:'<ffx:anger>أأنت أعمى أم ماذا، اللعنة؟ <ffx:disgust>أصلح هذا القرف! أصلحه أيها الوغد، اللعنة عليك! <ffx:neutral>',
24:'<ffx:disgust>أيها الكلب الغبي اللعين! لا تجيد سوى النباح... <ffx:wonder_light>ربما تصلح لصنع قبعة جيدة... <ffx:anger>قبعة جميلة! وحين أصنعها ستصمت! <ffx:neutral>',
25:'لكن هذا يثير التساؤل... لماذا قررت كل هذه القوارب الوصول دفعة واحدة؟ لقد تشكل طابور، بحق السماء!',
26:'<ffx:smile_light>بل نحن عمال تركيب في الأعالي، نعم! <ffx:neutral>',
27:'<ffx:disgust>القوي يفترس الضعيف دائمًا... <ffx:sadness>في موسكو: النازيون والهانزا والحمر... <ffx:wonder>وفي الفولغا كان <ffx:disgust>سيلانتيوس، وهنا <ffx:anger>أتباع عبادة النار... <ffx:neutral>',
28:'<ffx:wonder>الغنائم؟ إن كنت تبحث عن غنائم فاسأل رجال منصة الحفر... <ffx:smile>وبالطبع، لن أمانع الحصول على نصيبي منها... <ffx:neutral>',
29:'<ffx:smile>شكرًا جزيلًا يا أخي! <ffx:neutral>',
30:'<ffx:smile>شكرًا جزيلًا على المساعدة يا صديقي! <ffx:wonder>سأنزل السلم الآن، انتظر لحظة! <ffx:neutral>',
31:'<ffx:anger>أنت، اسمع! أحضر الطعام الآن! <ffx:disgust>أحضر الطعام، اللعنة عليك! <ffx:neutral>',
32:'كان النموذج الأولي لمرحلة التايغا أول مرحلة في إكسودس اختبرنا فيها جميع تقنياتنا الجديدة.',
33:'آه... همم. [يسحب الهواء بين أسنانه]',
34:'<ffx:disgust>بلا فائدة! لن يأتي أحد، فلا أحد غبي! <ffx:sadness>نقف هنا طوال اليوم... بلا فائدة! <ffx:neutral>',
35:'هاه؟ أي أوباش يصدرون تلك الأصوات؟',
36:'<ffx:wonder>أي جهاز تشويش؟ إنها إحدى محطات الأرصاد الجوية التابعة للهانزا... <ffx:wonder_light>',
37:'ومعلومة طريفة أخرى: حتى الآن لم يتفق المطورون على اسم واحد لهذا الموقع؛ فنستخدم أسماء المزرعة وحظيرة الخنازير وزريبة الأبقار وحظيرة الماشية والسقيفة بالتبادل.',
38:'شحنة السماد غادرت، ومن المتوقع وصولها بعد يومين. هل تلقيت الرسالة؟',
39:'في الأعلى! ذلك الوغد هناك!',
40:'مغسلة القطارات هي أول موقع ظهر فيه فصيل قطاع الطرق في إكسودس.',
41:'<ffx:anger>لماذا تقف شاردًا هكذا، اللعنة؟ <ffx:disgust>ابق يقظًا أيها الوغد! <ffx:neutral>',
42:'<ffx:wonder>آه، سيقطع سيدي رأسي على أي حال، <ffx:smile>لكنني سأكون قد شبعت حينها! جيد! <ffx:neutral>',
43:'<ffx:smile_light>ومن الأعالي نبعث إليكم التحيات! <ffx:neutral>',
44:'<ffx:wonder>إذًا، المكتوب هو إس... برطة؟ <ffx:anger>ما زلت لا أفهم معناه! <ffx:neutral>',
45:'ذلك الوغد في الأعلى!',
46:'غاية في السهولة، هاها!',
47:'لن تفلت!',
48:'<ffx:anger_light>لا تمر عبر البوابة، بل اذهب <ffx:wonder_light>عبر قبو السجن حيث <ffx:disgust_light>يحتجز موناي بايلر العبيد. <ffx:neutral>',
49:'كانت هذه المواجهة أول ما نفذناه في إكسودس لاختبار تفاعل الشخصيات غير القابلة للعب مع تصرفات اللاعب بحسب السياق.',
50:'<ffx:fear>شكرًا جزيلًا أيها السيد العظيم! أنت لا <ffx:smile_light>تقتل العبد الصالح أبدًا! <ffx:fear>شكرًا جزيلًا! <ffx:neutral>'
}
def main():
    source=ROOT/'03_translation/review/latin_voice_after_terms.json'
    rows=json.loads(source.read_text(encoding='utf-8'));assert len(rows)==len(TARGETS)==51
    path=ROOT/'03_translation/overrides_by_id.json';overrides=json.loads(path.read_text(encoding='utf-8'))
    for i,r in enumerate(rows):overrides[r['id']]=TARGETS[i]
    path.write_text(json.dumps(overrides,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'03_translation/review/residual_voice_review_receipt.json').write_text(json.dumps(dict(reviewed_keys=[r['id'] for r in rows],original_foreign_speech_transliterated_keys=[rows[i]['id'] for i in [8,17,20]],intentionally_retained_company_name='4A Games'),indent=2))
    print('Reviewed 51 mixed-language voice entries; original foreign speech retained in Arabic transcription in 3 entries')
if __name__=='__main__':main()
