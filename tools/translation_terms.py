"""Normalize reviewed terminology in speech without marking sentences reviewed."""
import json,re
from formal_terms import formal_terms
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
terms=json.loads((ROOT/'03_translation/voice_terms.json').read_text(encoding='utf-8'))
names=json.loads((ROOT/'03_translation/speaker_names.json').read_text(encoding='utf-8'))
for name in ['ANNA','IDIOT','DUKE','DAMIR','ALYOSHA','KATYA','MILLER','SAM','TOKAREV','KREST','YERMAK','NASTYA','STEPAN','KIRILL','ARTYOM','BOURBON','KHAN','EUGENE','OLGA','SILANTIUS','GIUL','SAUL','TOM','KLIM','KORZH','KHLEBNIKOV','PETROVITCH']:
    terms[name]=names[name]
terms.pop('Kep',None)
terms.update({'THE TWO COLONELS':'العقيدان',"SAM'S STORY":'قصة سام','SAM’S STORY':'قصة سام',
    'Ranger Hardcore':'رينجر الصعب','New Game Plus':'لعبة جديدة+', 'New Game':'لعبة جديدة',
    'Spartan Order':'التنظيم الإسبرطي','Spartan':'إسبرطي','Survival':'البقاء','Taiga':'التايغا',
    'Medkits':'حقائب الإسعافات','Medkit':'حقيبة الإسعافات','Universal Detector':'الكاشف الشامل',
    'Kalash':'كلاش','Bastard':'النذل','Nosalis':'النوساليس','Crew':'الطاقم','Bukhanka':'بوخانكا',
    'SPIDERBUG':'العنكبوت المتحول','DLC':'الإضافات','HUD':'واجهة المعلومات',
    'Flame':'اللهب','Surface':'السطح','Shield':'الدرع','Hansa':'الهانزا','Silantuis':'سيلانتيوس',
    'Exodus':'إكسودس','Ashot':'أشوت','Helsing':'هيلسنغ','Bulldog':'بولدوغ','Sammy':'سامي',
    'Stallion':'ستاليون','Lolife':'لولايف','Nagant':'ناغان','Blind One':'الأعمى','Batwing':'باتوينغ',
    'Baldie':'الأصلع','Misha':'ميشا','VOKHA':'فوخا','Solnechniy':'سولنيتشني','VDNKh':'فيدينخا',
    'Alexeyevskaya':'أليكسييفسكايا','Rizhskaya':'ريجسكايا','Chyornyj':'تشورني','PEREPLETCHIK':'بيريبليتشيك',
    'Yuri':'يوري','Andrei':'أندريه','Voloshkovski':'فولوشكوفسكي','Zhelezniak':'جيليزنياك','Bondarenko':'بوندارينكو',
    'Seryi':'سيري','Zhora':'جورا','Tolik':'توليك','Doc':'الطبيب','Cat':'القط','Nose':'الأنف',
    'Lumber Mill':'المنشرة','Night Hunters':'صيادو الليل','Fire Depot':'مركز الإطفاء',
    'Armory':'مخزن الأسلحة','Special Detail':'المفرزة الخاصة','Bear Trap':'مصيدة الدب','Paladins':'المحاربون',
    'Flamethrower':'قاذف اللهب','Comms':'الاتصالات','Ciprofloxacin':'سيبروفلوكساسين','Amoxicillin':'أموكسيسيلين',
    'Ranger':'رينجر','Radioprotector':'العقار الواقي من الإشعاع',
    'The Twocollones':'العقيدان','Spartatain':'الإسبرطي','Svarog Oil':'سفاروج أويل',
    'The Tower':'البرج','Tower':'البرج','Valve':'فالف','MLL':'مترو لاست لايت',
    'RIGHT TO DRIVE':'الحق في القيادة','Sandbox':'العوالم المفتوحة'})
terms={k.casefold():v for k,v in terms.items()}
pattern=re.compile(r'(?<![A-Za-z])(?:'+'|'.join(re.escape(k) for k in sorted(terms,key=len,reverse=True))+r')(?![A-Za-z])',re.I)
def normalize_terms(key,source,target):
    if 'credits' in key or any(w in key.lower() for w in ['eula','license','legal','copyright']):return target
    if not key.startswith('voices\\') and re.search(r'\bOptions\b',source):
        target=target.replace('قائمة الخيارات','قائمة الإعدادات').replace('الخيارات -','الإعدادات -')
    parts=re.split(r'(<[^>]+>)',target)
    target=''.join(p if p.startswith('<') else pattern.sub(lambda m:terms[m[0].casefold()],p) for p in parts)
    target=re.sub(r'\bThe\s+(?=[\u0600-\u06ff])','',target)
    target=re.sub(r"(?<=[\u0600-\u06ff])['’][sS]\b",'',target)
    if key.startswith('menu_customize_stock'):target=target.replace('المخزون','الأخمص').replace('مخزون','أخمص')
    if re.search(r'\bAurora\b',source):target=target.replace('الشفق القطبي','أورورا')
    if re.search(r'\bAurora\b',source) and not re.search(r'\bship\b',source,re.I):target=target.replace('السفينة أورورا','قطار أورورا')
    if re.search(r'\bAkademgorodok\b',source):target=target.replace('أكاديمجورودوك','أكاديمغورودوك')
    for name,variants,canonical in [('Alyosha',['أليشا','اليوشا'],'أليوشا'),('Yermak',['إيرماك'],'يرماك'),('Miller',['ميللر'],'ميلر'),('Krest',['الصليب'],'كريست')]:
        if re.search(r'\b'+name+r'\b',source):
            for variant in variants:target=target.replace(variant,canonical)
    if re.search(r'(?:the|Spartan) Order',source):target=target.replace('النظام','التنظيم').replace('الطلب','التنظيم')
    if re.search(r'green stuff',source,re.I):target=target.replace('الأشياء الخضراء','المادة الخضراء')
    if re.search(r'radioprotector',source,re.I):target=target.replace('واقي الراديو','العقار الواقي من الإشعاع')
    if key.startswith('voices\\'):
        if re.search(r'Kep rakmet',source,re.I):
            target=target.replace('كيب راكميت','شكرًا جزيلًا').replace('كيب ركمت','شكرًا جزيلًا')
        if re.search(r'\bOver[.!…\s]*$',re.sub('<[^>]+>','',source),re.I):
            target=re.sub(r'زيادة(?=(?:[.!…\s]|<[^>]+>)*$)','حوّل',target)
        if re.search(r'\bbackup\b',source,re.I):target=target.replace('نسخة احتياطية','مساندة')
        if re.search(r'break a leg',source,re.I):target=target.replace('كسر ساق','بالتوفيق').replace('اكسر ساقك','بالتوفيق')
    target=formal_terms(key,source,target)
    if re.search(r'\bGiul\b',source,re.I):
        target=re.sub(r'(?<![\u0621-\u064a])جيول(?![\u0621-\u064a])',names['GIUL'],target)
    return target
