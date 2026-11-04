"""Conservative whole-word spelling fixes; leave context-dependent hamza for review."""
import re,json
from pathlib import Path
CONTEXT_PATH=Path(__file__).resolve().parents[1]/'03_translation/spelling_context.json'
CONTEXT=json.loads(CONTEXT_PATH.read_text(encoding='utf-8')) if CONTEXT_PATH.exists() else {}
RULES={'هاذا':'هذا','هاذه':'هذه','لاكن':'لكن','لاكنه':'لكنه','اللذي':'الذي','اللتي':'التي','ذالك':'ذلك',
 'مسؤل':'مسؤول','مسؤلية':'مسؤولية','الاعدادات':'الإعدادات','اعدادات':'إعدادات',
 'الى':'إلى','والى':'وإلى','بالاضافة':'بالإضافة','الان':'الآن','والان':'والآن','ايضا':'أيضًا',
 'إستخدام':'استخدام','الإستخدام':'الاستخدام','إستعمال':'استعمال','إستعادة':'استعادة','إستمرار':'استمرار',
 'إنتظر':'انتظر','إسمعوا':'اسمعوا','إنتهى':'انتهى','شيئ':'شيء','انت':'أنت',
 'انا':'أنا','انتم':'أنتم','اه':'آه','اوه':'أوه','اذا':'إذا','اهلا':'أهلًا','الاشياء':'الأشياء',
 'اعلانات':'إعلانات','انذار':'إنذار','امرك':'أمرك','اكرههم':'أكرههم','احمق':'أحمق',
 'ابرام':'إبرام','اصلا':'أصلًا','ارتيوم':'أرتيوم','ايفانوف':'إيفانوف','اهدأوا':'اهدؤوا',
 'اخيرا':'أخيرًا','اخيراً':'أخيرًا','استطيع':'أستطيع','اخبرني':'أخبرني','اظهر':'أظهر',
 'ارسله':'أرسله','اطلاق':'إطلاق','اصلاحه':'إصلاحه','اخمادها':'إخمادها'}
PATTERN=re.compile(r'(?<![\u0621-\u065f])(?:'+'|'.join(map(re.escape,RULES))+r')(?![\u0621-\u065f])')
def correct_spelling(key,text):
 if 'credits' in key or any(w in key.lower() for w in ['legal','eula','license']):return text
 def segment(p):
  p=PATTERN.sub(lambda m:RULES[m[0]],p)
  for before,after in CONTEXT.get(key,{}).items():
   p=re.sub(r'(?<![\u0621-\u065f])'+re.escape(before)+r'(?![\u0621-\u065f])',after,p)
  return p
 return ''.join(p if p.startswith('<') else segment(p) for p in re.split('(<[^>]*>)',text))
