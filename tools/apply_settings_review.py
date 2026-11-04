"""Canonical settings labels; exact source matches only in user-interface keys."""
import csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LABELS={
'OPTIONS':'الإعدادات','SETTINGS':'الإعدادات','GAME OPTIONS':'إعدادات اللعب','VIDEO':'الرسوميات','SOUND':'الصوت','CONTROLS':'التحكم',
'ACCESSIBILITY':'إمكانية الوصول','LANGUAGE':'اللغة','TEXT LANGUAGE':'لغة النصوص','VOICE LANGUAGE':'لغة الحوار',
'MASTER VOLUME':'مستوى الصوت العام','MUSIC VOLUME':'مستوى الموسيقى','VOICE VOLUME':'مستوى صوت الحوار',
'RESOLUTION':'دقة العرض','ASPECT RATIO':'نسبة الأبعاد','QUALITY':'جودة الرسوم','GAMMA':'تصحيح غاما','MOTION BLUR':'ضبابية الحركة',
'TEXTURE FILTERING':'ترشيح الخامات','COLOR SPACE':'نطاق الألوان','HDR EXPOSURE':'تعريض HDR',
'HDR':'HDR','SRGB':'sRGB','SRGB LIMITED':'sRGB Limited','REC.709':'Rec.709','SSAO+IBL':'SSAO+IBL','Raytraced AO+GI':'Raytraced AO+GI',
'VSYNC':'VSync','DIRECTX':'DirectX','DIRECTX 11 OPTIONS':'إعدادات DirectX 11','NVIDIA RTX':'NVIDIA RTX',
'RAY TRACING':'Ray Tracing','HAIRWORKS':'HairWorks','ADVANCED PHYSX':'Advanced PhysX','TESSELLATION':'Tessellation',
'SHADING RATE':'Shading Rate','DLSS':'DLSS','SSAA':'SSAA','AF 4X':'AF 4X','AF 16X':'AF 16X',
'LOW':'منخفض','MEDIUM':'متوسط','HIGH':'مرتفع','ULTRA':'Ultra','EXTREME':'Extreme','NORMAL':'عادي','AUTO':'تلقائي',
'ON':'تشغيل','OFF':'إيقاف','SMALL':'صغير','BIG':'كبير','FULL':'كامل','HALF':'نصف','WEAK':'ضعيف','STRONG':'قوي',
'SUBTITLES':'الترجمة النصية','SUBTITLE SPEAKER':'إظهار اسم المتحدث','SUBTITLE SIZE':'حجم الترجمة النصية',
'SUBTITLE BACKGROUND':'خلفية الترجمة النصية','SUBTITLES FOR HEARING IMPAIRED':'وصف الأصوات لضعاف السمع',
'SIGN SUBTITLES':'ترجمة اللافتات','NO TINNITUS SOUNDS':'إيقاف أصوات الطنين','CROSSHAIR':'علامة التصويب','AIM ASSIST':'مساعدة التصويب',
'AIM SENSITIVITY':'حساسية التصويب','SENSITIVITY':'الحساسية','INVERT Y AXIS':'عكس المحور الرأسي','VIBRATION':'الاهتزاز',
'KEYBOARD':'لوحة المفاتيح','MOUSE':'الفأرة','CONTROLLER':'يد التحكم','WIRELESS CONTROLLER':'يد تحكم لاسلكية',
'PRESET':'إعداد مسبق','LAYOUT':'تخطيط الأزرار','CUSTOM':'مخصص','AUTO DETECT':'اكتشاف تلقائي',
'MOTION CONTROLS SETTINGS':'إعدادات التحكم بالحركة','MOTION CONTROLS SENSITIVITY':'حساسية التحكم بالحركة',
'MOTION CONTROLS AIMING':'التصويب بالتحكم بالحركة','INVERT MOTION CONTROLS (X-AXIS)':'عكس التحكم بالحركة (المحور X)',
'INVERT MOTION CONTROLS (Y-AXIS)':'عكس التحكم بالحركة (المحور Y)',
'DIFFICULTY':'مستوى الصعوبة','READER':'القصة','EASY':'سهل','HARDCORE':'صعب','RANGER HARDCORE':'رينجر فائق الصعوبة',
'RANGER':'رينجر','Iron Mode':'وضع الرجل الحديدي','NEW GAME':'لعبة جديدة','NEW GAME PLUS':'لعبة جديدة+',
'USE DEFAULTS':'استعادة الإعدادات الافتراضية','CONFIRM':'تأكيد','CANCEL':'إلغاء','ACCEPT':'موافقة','BACK':'رجوع','SELECT':'اختيار',
'CONTINUE':'متابعة','CONTINUE GAME':'متابعة اللعبة','RESUME GAME':'متابعة اللعبة','QUIT GAME':'الخروج من اللعبة',
'QUIT TO MAIN MENU':'العودة إلى القائمة الرئيسية','LOAD GAME':'تحميل لعبة','LOAD LAST CHECKPOINT':'تحميل آخر نقطة حفظ',
'LEFT':'يسار','RIGHT':'يمين','JOURNAL':'اليوميات','INVENTORY':'المعدات','LIGHTER':'الولاعة','FIRE':'إطلاق النار','AIM':'التصويب',
'RELOAD':'إعادة التلقيم','MELEE ATTACK':'هجوم قريب','MEDKIT':'حقيبة إسعافات','GAS MASK':'قناع الغاز',
'SPRINT':'الركض السريع','CROUCH':'الانحناء','CROUCH TOGGLE':'تبديل الانحناء','WALK':'المشي','WALK TOGGLE':'تبديل المشي',
'SPRINT TOGGLE':'تبديل الركض السريع','RUN TOGGLE':'تبديل الركض','JUMP':'القفز','FORWARD':'للأمام','BACKWARD':'للخلف',
'STRAFE RIGHT':'التحرك يمينًا','STRAFE LEFT':'التحرك يسارًا','NEXT WEAPON':'السلاح التالي','PREV WEAPON':'السلاح السابق',
'SWAP FILTER':'تبديل المرشح','LIGHT':'المصباح','TIME':'الوقت','USE / INTERACT':'استخدام / تفاعل',
'CHARGER (HOLD)':'الشاحن (ضغط مطول)','LIGHT / CHARGER (HOLD)':'المصباح / الشاحن (ضغط مطول)',
'WEAPONS INVENTORY (HOLD)':'قائمة الأسلحة (ضغط مطول)','EQUIPMENT INVENTORY (HOLD)':'قائمة المعدات (ضغط مطول)',
'SECONDARY INVENTORY(HOLD)':'قائمة المعدات الثانوية (ضغط مطول)','INVENTORY (HOLD)':'المعدات (ضغط مطول)',
'SWAP FILTER / GAS MASK (HOLD)':'تبديل المرشح / قناع الغاز (ضغط مطول)','GAS MASK (HOLD)':'قناع الغاز (ضغط مطول)',
'TIME / HOLSTER (HOLD)':'الوقت / إخفاء السلاح (ضغط مطول)','HOLSTER (HOLD)':'إخفاء السلاح (ضغط مطول)',
'PHOTO MODE (HOLD)':'وضع التصوير (ضغط مطول)','BACKPACK (HOLD)':'حقيبة الظهر (ضغط مطول)',
'RELOAD / INTERACT / PUMP (HOLD)':'إعادة التلقيم / التفاعل / الضخ (ضغط مطول)','THROW SECONDARY':'رمي سلاح ثانوي',
'HOLD':'ضغط مطول','TAP':'ضغط متكرر','PRESS':'ضغطة واحدة','QTE CONTROL':'طريقة الضغط في الأحداث السريعة',
'Italian':'الإيطالية','ITALIAN':'الإيطالية','GERMAN':'الألمانية','PS4':'PS4','XBOX':'Xbox','LMB':'LMB','RMB':'RMB','MMB':'MMB',
'SR. COMMUNICATIONS MANAGER':'كبير مديري الاتصالات'}
SPECIAL={
'$load_last_checkpoint_date':'تحميل آخر نقطة حفظ (منذ <autosave_date> دقيقة)',
'$quit_game_3d':'<menu_back> الخروج من اللعبة',
'$loading_progress':'جارٍ التحميل...<load_progress>%',
'$lang_sound_downloaded':'تتوفر لغة حوار جديدة. هل تريد اختيارها؟',
'$game_difficulty_mutator_armored_mode':'أعداء مدرعون',
'$game_difficulty_mutator_grenadier_mode':'رماة القنابل',
'$game_difficulty_mutator_tough_creatures':'مخلوقات أشد قوة',
'$game_difficulty_mutator_no_weapon_mode':'بلا تعديلات للأسلحة',
'$game_difficulty_mutator_developers_comments':'تعليقات المطورين',
'$game_difficulty_mutator_sneaky_combat_behaviour':'سلوك مخادع',
'$god_mode':'وضع الحصانة',
'$move_xbox_rstick':'RS', '$move_xbox_lstick':'LS',
'$photo_mode_hide_ui_pc':'R',
'menu_category_wpn_barrel':'السبطانة','menu_category_wpn_scope':'المنظار',
'menu_category_wpn_magazine':'مخزن الذخيرة','menu_category_wpn_butt':'الأخمص والقبضة',
'menu_category_wpn_forearm':'واقي اليد','menu_category_wpn_additional':'ملحق جانبي',
'menu_category_craft_devices':'صناعة المعدات','menu_category_craft_ammunition':'صناعة الذخيرة',
'menu_trade_category_craft':'الصناعة','menu_hint_craft':'صناعة','menu_hint_salvage':'تفكيك',
'menu_item_medkit_name':'حقيبة إسعافات','menu_ex_survival':'حقيبة إسعافات',
'menu_ammo_arrow_name':'سهم القوس','menu_ammo_arrow_desc':'وصف سهم القوس',
'menu_item_throwing_knife_name':'سكين رمي','menu_ammo_shotgun_name':'ذخيرة الخرطوش',
'$custom_menu_attach_xbox':'تركيب <menu_buy>','$custom_menu_detach_xbox':'إزالة <menu_buy>'}
def main():
 rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
 path=ROOT/'03_translation/overrides_by_id.json';edits=json.loads(path.read_text(encoding='utf-8'));receipt=[]
 for r in rows:
  k=r['id'];source=r['source'].strip();target=SPECIAL.get(k)
  eligible=(k.startswith('$') and not any(w in k for w in ['credits','wpn_','hint','_name','_desc','_dsc','dbg','photomode'])) or k.startswith(('$ctrl_','$gp_')) or k=='options_video_hairworks'
  if target is None and eligible:target={s.casefold():v for s,v in LABELS.items()}.get(source.casefold())
  if target is None:continue
  assert sorted(re.findall('<[^>]*>',target))==sorted(re.findall('<[^>]*>',r['source'])),k
  edits[k]=target;receipt.append({'id':k,'source':r['source'],'before':r['target'],'target':target})
 path.write_text(json.dumps(edits,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'03_translation/review/settings_review_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'03_translation/settings_glossary.json').write_text(json.dumps(LABELS,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'reviewed_settings_and_controls':len(receipt),'changed_entries':sum(r['before']!=r['target'] for r in receipt)}))
if __name__=='__main__':main()
