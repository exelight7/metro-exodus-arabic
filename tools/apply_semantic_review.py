"""Apply individually reviewed source/target corrections; never auto-review drafts."""
import json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPEATED={
0:'<ffx:fear_strong>آآه!<ffx:neutral>',
1:'آآه!',
2:'<ffx:smile>هاهاها! <ffx:neutral>',
3:'<ffx:wonder>حسنًا، لا مانع لدي، فما دمنا نستطيع <ffx:smile>دائمًا التفاهم معك يا سام! <ffx:wide_smile>هاهاها! <ffx:smile_light>',
4:'<ffx:fear_strong>آآه!<ffx:neutral>',
5:'<ffx:smile>هاهاها! <ffx:neutral>',
6:'<ffx:anger_strong>آآه!',
7:'لحم طازج!',
8:'<ffx:anger>آآه!',
9:'<ffx:wide_smile>هاهاها! <ffx:neutral>',
10:'آه، اللعنة! ذلك الوغد هنا!',
11:'أين تختبئ؟ اخرج لنتحدث عن خلاص روحك، هاهاها!',
12:'أوووه... وصل أناس جدد... لحم طازج... وأنا مضطر للبقاء هنا... أوووه...',
13:'طعام!',
14:'أتحاول إخافتي أم ماذا؟ هاهاها!',
15:'<ffx:anger>آآه!',
16:'أمسكوا بهم!',
17:'اسمع أيها الأحمق! أهذه مؤخرتك التي تصدر كل تلك الجلبة؟ اكتم صوتها حتى آتي وأقطعك! هاهاها!',
18:'<ffx:fear_strong>آآه!<ffx:neutral>',
19:'<ffx:anger>آآه!',
20:'<ffx:wide_smile>هاهاها! اللعنة، لا بد أنهم منتشون بالمخدرات! <ffx:smile_light>',
21:'اسمع أيها الحقير، آمل أنك تحب الشواء! هاهاها!',
22:'آآه!',
23:'<ffx:anger>آآه! الحرية! <ffx:neutral>',
24:'سنأكلك الآن! هاهاها!',
25:'<ffx:smile>غوركو! <ffx:disgust>(يسعل) <ffx:neutral>',
26:'سيارة!',
27:'نعم، نعم، نعم...',
28:'لحم!',
29:'<ffx:anger>آآه!',
30:'<ffx:anger>آآه!',
31:'<ffx:fear>آآه!',
32:'آه، يا اللهب المقدس، أنقذني!',
33:'<ffx:smile>غوركو! <ffx:neutral>',
34:'<ffx:smile>مرحى!<ffx:neutral>',
35:'<ffx:smile_strong>هاهاها! <ffx:neutral>',
36:'وووه!',
37:'<ffx:smile>هاهاها!<ffx:neutral>',
38:'<ffx:anger>آآه!',
39:'<ffx:fear_strong>آآه!<ffx:neutral>',
40:'<ffx:anger>آآه!',
41:'<ffx:smile_strong>هاهاها! <ffx:neutral>',
42:'<ffx:smile>غوركو! <ffx:neutral>',
43:'<ffx:anger>آآه!',
44:'<ffx:fear_strong>آآه! إنه الدب! <ffx:neutral>',
45:'آآه!',
46:'آآه!',
47:'<ffx:fear_strong>آه، اللعنة! آه! <ffx:neutral>',
48:'<ffx:smile>غوركو! <ffx:neutral>'
}
EDITS={
'voices\\m3_ending\\end_glukh_03_03':'<ffx:smile>سيداتي... سادتي! <ffx:anger_light>بصفتي أرفع الضباط رتبة، أقترح <ffx:smile_light>أن نعهد بقيادة <ffx:smile>التنظيم إلى أرتيوم!',
'voices\\m3_05_winter\\win_010_idiot_breather_03_03':'<ffx:sadness_light>عندما وجهت تلك الصواريخ نحو المظلمين. <ffx:wonder_light>هل كان الهواء مريرًا آنذاك؟',
'voices\\m3_08_desert\\des_017_waytoterminal_29':'<ffx:sadness>كان عدد الأعداء أكبر مما توقعنا. <ffx:wonder>نحن داخل المجمع، لكن <ffx:sadness_light>غيول مفقودة. <ffx:anger_light>انتظروا إشارتنا. حوّل. <ffx:neutral>',
'voices\\m3_05_winter\\win_003_radiogameprogress_01':'<ffx:wonder>أتظن أن العثور على «الفلك» الذي تتحدث عنه <ffx:anger>سيصلح كل شيء؟ <ffx:anger_light>',
'voices\\m3_08_desert\\des_059_insideoilrig_15':'<ffx:anger_light>لا تتجول في كل مكان هكذا، اللعنة! <ffx:wonder_light>قد يرديك الرجال في أي لحظة، وأظن أن <ffx:smile_light>الزعيم لن يمانع حتى! <ffx:neutral>',
'voices\\m3_08_desert\\des_013_1_briefing_02_kresttalk_11':'<ffx:wonder>ونحتاج إلى كميات هائلة من الاثنين! <ffx:wonder_light>فأورورا تحول طنين من الماء إلى بخار كل ساعة، <ffx:sadness_light>واستهلاكها للوقود ليس هينًا أيضًا. <ffx:neutral>',
'voices\\m3_06_bridge\\bri_002_initialbriefing_12':'<ffx:wonder>أيمكنني مرافقة أرتيوم أيضًا؟ لأسانده؟ <ffx:wonder_light>',
'voices\\m3_dlc1\\dlc1_27_depot_railcar_ride_01_03':'اسمعوا يا رفاق! اركبوا! سنوصلكم إلى بروسبكت!',
'voices\\m3_12_valley\\val_004_alyoshalog_01':'<br><br>مرحبًا يا أرتيوم... أعرف أنك حي؛ لا شيء يستطيع القضاء عليك، فكيف بنهر صغير... لذا سأدخل في صلب الموضوع.<br>السكان المحليون بارعون، لم ألحظهم حتى أحاطوا بي وأمسكوني. لم أطلق النار، وكان ذلك قرارًا صائبًا؛ فقد أخذوني إلى معسكرهم فحسب... إنهم رجال لطفاء، حقًا... والفتيات أيضًا... خصوصًا الفتيات...<br>أخبرتني إحدى جنيات الغابة هذه بوجود مذياع في الكنيسة، فظننت أنني أستطيع الاتصال بأورورا...<br>لكن المذياع لا يعمل كما ينبغي، لذا سأذهب إلى السد... سأنتظرك هناك. <br>وأمر آخر... لن تصل إليه دون قارب، فابحث عن واحد. بالتوفيق!<br><br>',
'voices\\m3_08_desert\\des_016_9_2_breakingcamp_artyomreact_01_03':'<ffx:anger_light>هيا، بالله عليك، <ffx:wonder>نحن نتحدث عن أرتيوم! <ffx:smile>إنه رجل من فولاذ، اسمع وقع خطواته فحسب! <ffx:neutral>',
'voices\\m3_13_dead_city\\nvs_003_yermak_artyomgoodbye_01_02':'<ffx:wonder_light>ستصل أورورا إلى نقطة اللقاء في موعدها، <ffx:smile_light>يمكنك الاعتماد على ذلك. <ffx:neutral>',
'voices\\m3_13_dead_city\\nvs_008_intheshelter_whileartyomisbusy_02_01':'<ffx:fear_light>لا تنس تجهيز بعض المرشحات يا أرتيوم! <ffx:smile_light>لن يتاح لنا الوقت لذلك لاحقًا... <ffx:neutral>',
'voices\\m3_06_bridge\\bri_026_gasstation_bandits_talk_01_11':'<ffx:fear_light>إنه أمر مروع... جثث كثيرة نصف مأكولة تتدلى فوق الماء. <ffx:disgust>سألت أولئك المتعصبين عنها... واتضح أن سيلانتيوس هو المسؤول. حين صار زعيمًا أخذ يطعم <ffx:fear>تلك السمكة اللعينة جميع موتاهم! <ffx:fear_light>',
'voices\\m3_12_valley\\val_005_07_olgaextrachat_01_20':'<ffx:wonder>وليس لأن إيذاء الفتيات ممنوع فحسب؛ <ffx:smile_light>فالقتال العادل يظل قتالًا عادلًا... <ffx:wonder>الوحيد الذي هزمني في نزال عادل هو رومان، <ffx:smile_light>وحتى حينها تركت حول عينه كدمة ظل <ffx:smile>يحملها أسبوعًا كاملًا، هاها! هكذا كسبت احترامه.<ffx:neutral>',
'voices\\m3_13_dead_city\\nvs_001_initialbriefing_06_01':'<ffx:anger_light>سأتولى أنا وكريست وسام تفقد مبنى المعهد في أكاديمغورودوك. <ffx:smile_light>وسنزور متحف السكك الحديدية في الطريق. <ffx:wonder_light>قد نجد فيه شيئًا ينفع أورورا... <ffx:neutral>',
'voices\\m3_06_spring\\spr_007_princewake_20_02':'<ffx:disgust>حسنًا، لا أمل يرجى من إله سيلانتيوس... <ffx:smile>لكنني أظن أن ديوك سيحب فالهالا! <ffx:wonder_light>جنة يقضي فيها الأبطال الذين سقطوا الأبدية في الولائم والقتال... <ffx:sadness_light>مكان يليق بكل من فقدناهم...<ffx:neutral>',
'voices\\m3_08_desert\\des_013_1_briefing_02_kresttalk_04':'<ffx:wonder>وقد يفعلون ذلك فعلًا، <ffx:sadness>فأنا أظن أن غيول تحاول استخدامنا بيادق في لعبتها... <ffx:anger_light>تخلصنا من قطاع الطرق سيخدم خطتها تمامًا! <ffx:neutral>',
'voices\\m3_09_summer\\sum_007_tokarevworkshoptalk_01_08_dukealive':'<ffx:smile>هاها! حسنًا، <ffx:wonder_strong>لم يكن عليك غمر الشامبلر في الرمل! <ffx:smile>فهو ليس كلاش! <ffx:neutral>',
'voices\\m3_09_summer\\sum_007_tokarevworkshoptalk_01_14':'<ffx:sadness_light>نعم... على أي حال<ffx:smile_light>، لا تقلق بشأن الأسلحة يا أرتيوم؛ <ffx:wonder>سأجعلها كالجديدة <ffx:smile>بحلول محطتنا التالية، هاها! <ffx:neutral>',
'voices\\m3_08_desert\\des_013_briefing_02_17':'<ffx:anger_light>نحتاج إلى الماء لأورورا والطاقم، <ffx:sadness_light>كما ترون. فقد أصيب ستيبان وديوك وأليوشا بالجفاف بالفعل. <ffx:wonder_light>ونحتاج إلى الوقود أيضًا. <ffx:neutral>'
}
def main():
    path=ROOT/'03_translation/overrides_by_id.json';overrides=json.loads(path.read_text(encoding='utf-8'))
    candidates=json.loads((ROOT/'03_translation/review/repeated_glyph_candidates.json').read_text(encoding='utf-8'))
    assert len(candidates)==len(REPEATED)==49
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    source_edits={r['source']:REPEATED[i] for i,r in enumerate(candidates)}
    applied=[]
    for r in rows:
        if r['source'] in source_edits:overrides[r['id']]=source_edits[r['source']];applied.append(r['id'])
    assert set(EDITS)<={r['id'] for r in rows}
    overrides.update(EDITS)
    path.write_text(json.dumps(overrides,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'03_translation/review/semantic_review_receipt.json').write_text(json.dumps(dict(repeated_source_entries=applied,individual_sentence_keys=list(EDITS)),indent=2))
    print('Reviewed repetition entries',len(applied),'individual contextual corrections',len(EDITS))
if __name__=='__main__':main()
