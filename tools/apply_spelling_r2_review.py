"""Reviewed short contexts discovered while checking missing hamza and imperatives."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
x=json.loads((ROOT/'03_translation/review/spelling_r2_contexts.json').read_text(encoding='utf-8'))
EDITS={
1:'<ffx:sadness>انتبهي إلى أسلوبك أيتها الشابة!<ffx:smile_light>افعلي مثل ذلك الشاب: استيقظ منذ وقت طويل،<ffx:wonder_light>لكنه يستمع إلى كلام الحكماء بهدوء!',
2:'نعم، ارمِ المزيد من القذارة أيها القرد اللعين! هاهاها!',
3:'<ffx:disgust>ألقِ هذه القذارة خارجًا!<ffx:anger>ألقِ بها بعيدًا!<ffx:neutral>',
5:'أطلق النار على اللعين! أطلق عليه النار، إنه يبتعد بالقارب!',
6:'<ffx:disgust_light>ميخا، ابقَ مع يرماك.<ffx:neutral>',
7:'<ffx:anger>تكرر الكلام كأسطوانة مشروخة! أي امتحان؟ وأي معلم؟<ffx:wonder_strong>ما هذا بحق الجحيم؟<ffx:neutral>',
8:'ارمِ بندقيتك في المرة القادمة، أيها الغبي اللعين!',
9:'ابقَ مكانك فحسب، ما فائدة الركض هكذا...',
10:'أحتاج إلى استراحة أيضًا. يا لها من قطع حديد تؤلم الجسد! لكن عليّ الحذر من البقاء طويلًا...',
11:'نعم يا سيدي! أستطيع!',
12:'<ffx:sadness>نعم... حسنًا،<ffx:anger_light>افعل شيئًا حيال ذلك إذن،<ffx:smile_light>وإلا فستتلقى توبيخًا شديدًا!<ffx:neutral>',
13:'ها! ارمِ واحدة أخرى، فلن تصيبني حتى لو ألصقت حذائي بالأرض!',
14:'مت أيها المسخ!',15:'ارمِ المزيد من القذارة أيها الأحمق، لعلني أطاردها عندئذ، هاهاها!',
16:'<ffx:smile>أظن أنك والعقيد ستنجحان! لذا...<ffx:wonder>افعلا ما يجب عليكما فحسب، و<ffx:smile>سيكون كل شيء على ما يرام!<ffx:neutral>',
18:'أفّ... يا للقرف...',
19:'<ffx:anger>قواعد؟! أي قواعد؟!<ffx:disgust>أنتم تطلقون النار على الناس كالكلاب! أنتم...<ffx:neutral>',
20:'نعم، نعم، ارمِ المزيد... سأعثر عليك قريبًا، وسنرى ماذا سترمي حينها...',
21:'اقضوا على ذلك اللعين! أطلقوا النار على الزجاج الأمامي!',
22:'هل كسرت شيئًا للتو؟! أصلحه! هيا، تحرك!',23:'آه... لقد انتهى الأمر أخيرًا...',
25:'ارمِ علبة أخرى، لعلها تشتت انتباهي!',26:'أطلق النار على الزجاج الأمامي! الزجاج الأمامي!',
27:'ارمِ نفسك من فوق جرف في المرة القادمة!',
30:'أخبرني أنت! إلى أين تأخذ ذلك القطار، هاه؟ في نزهة فحسب؟!',
31:'ميلر هنا. إيديوت، أعطني تقريرًا عن الوضع.',
32:'أيها الكلب... أظهر نفسك، هيا...',
35:'<ffx:fear_strong>آآآه! إنها خطيئة، خطيئة! أطفئها!<ffx:fear_light>',
38:'قالوا لي أن أبقى هنا... أبقى وأنتظر... وما فائدة الانتظار؟ لن يعطوني أي لحم... لا لحم، لا لحم أبدًا...',
39:'مت أيها المسخ!',40:'هيا! أطلق النار على اللعين!',
41:'أخطأت بتلك السكين! ارمِ أخرى، لعلها تصيب، هاها!',42:'مت يا ابن العاهرة!',
43:'<ffx:disgust>إذًا، تخفي سلاحك؟ أتريد تعذيبي؟<ffx:disgust_strong>افعل أسوأ ما عندك، لست خائفًا!<ffx:neutral>',
45:'ماذا؟! آه، فهمت! أتظن أنك تجيد رمي السكاكين أيها الكلب؟ حسنًا، هيا، حاول مرة أخرى!',
46:'<ffx:anger_light>اضغط على دواسة الوقود إلى النهاية!',
47:'ارمِ قطعة براز في المرة القادمة أيها القرد المجنون!',
49:'تبًا، أمريكي آخر... حقًا، يا لها من مصادفة!',
50:'<ffx:fear>آه، ماذا أفعل الآن؟ ماذا أفعل... ومن هذا؟ هل أرسله غليبا؟ ألعل بوبر يأخذ المال لنفسه؟<ffx:sadness>أوه، ماذا أفعل الآن... ماذا أفعل...',
51:'<ffx:disgust_light>هيا، ارمِها!<ffx:neutral>',
52:'أي شيطان...؟',53:'مت أيها الوحش!',54:'الموت للزنادقة! أطلقوا النار عليهم!'}
p=ROOT/'03_translation/overrides_by_id.json';byid=json.loads(p.read_text(encoding='utf-8'));receipt=[]
for i,target in EDITS.items():
 r=x[i];assert sorted(re.findall('<[^>]+>',r['source']))==sorted(re.findall('<[^>]+>',target)),(i,r['source'])
 byid[r['id']]=target;receipt.append({'id':r['id'],'source':r['source'],'before':r['target'],'target':target})
# This incomplete threat had been mistranslated as an unrelated sexual statement.
rows=json.loads((ROOT/'03_translation/review/spelling_r2_baseline.json').read_text(encoding='utf-8'))
for r in rows:
 if r['id']=='voices\\universal_m3\\factions\\bandit_1\\uber_alert\\uber_alert_threat_switch_03':
  assert r['source']=="I'm gonna fucking..."
  target='سوف... تبًا...';byid[r['id']]=target;receipt.append({'id':r['id'],'source':r['source'],'before':r['target'],'target':target})
p.write_text(json.dumps(byid,ensure_ascii=False,indent=2),encoding='utf-8')
context_path=ROOT/'03_translation/spelling_context.json'
context=json.loads(context_path.read_text(encoding='utf-8'))
context.setdefault(x[44]['id'],{})['اي']='أي'
context_path.write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'03_translation/review/spelling_r2_context_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'reviewed_short_entries':len(receipt)}))
