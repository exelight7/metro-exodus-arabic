"""Prepare a minimal public source tree and release assets, never game originals."""
from pathlib import Path
import collections,csv,hashlib,json,re,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT/'06_build/github_publish';TAG='v0.1.0-beta.1'
SOURCE=ROOT/'09_release/installer-review';OUT=ROOT/'09_release'/TAG
BASE='https://github.com/exelight7/metro-exodus-arabic';DOWNLOAD=BASE+'/releases/download/'+TAG
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
def main():
    assert (REPO/'.git').is_dir();OUT.mkdir(exist_ok=True)
    old=json.loads((SOURCE/'build-metadata.json').read_text(encoding='utf-8'))
    for name,data in old['artifacts'].items():assert sha(SOURCE/name)==data['sha256']
    # Use the byte-for-byte tested EXE/AppImage. Runtime behavior is unchanged.
    for name in ['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage']:shutil.copy2(SOURCE/name,OUT/name)
    installer=REPO/'installer';installer.mkdir(exist_ok=True)
    with zipfile.ZipFile(SOURCE/'Metro-Arabic-Installer-Source.zip') as z:
        assert z.testzip() is None
        for member in z.infolist():
            name=member.filename
            if name.startswith('development/') or name in ['README-ar.md','REBUILD.txt']:continue
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            target=installer/name
            if member.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
    # Existing owner-selected MIT license is retained without replacement.
    shutil.copy2(SOURCE/'THIRD-PARTY-NOTICES.txt',REPO/'docs/THIRD-PARTY-NOTICES.txt') if (REPO/'docs').exists() else None
    (REPO/'docs').mkdir(exist_ok=True);shutil.copy2(SOURCE/'THIRD-PARTY-NOTICES.txt',REPO/'docs/THIRD-PARTY-NOTICES.txt')
    shutil.copytree(SOURCE/'licenses/Debian',installer/'assets/licenses/Debian',dirs_exist_ok=True)
    for name in ['extra_timed_ar.json','speaker_names.json','settings_glossary.json']:
        dest=REPO/'translations'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'03_translation'/name,dest)
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig',newline='')))
    assert len(rows)==38221 and not any(x['source'].strip() and not x['target'].strip() for x in rows)
    with (REPO/'translations/arabic.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['id','target','status']);writer.writeheader()
        for row in rows:writer.writerow({k:row[k] for k in writer.fieldnames})
    stats=dict(rows=len(rows),nonempty_targets=sum(bool(x['target'].strip()) for x in rows),intentionally_empty_rows=sum(not bool(x['source'].strip()) for x in rows),status_counts=dict(collections.Counter(x['status'] for x in rows)),patch_revision='final_review_r1',manual_proofreading_complete=False,in_game_runtime_tested=False)
    write(REPO/'translations/stats.json',json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    write(REPO/'translations/README.md','''# بيانات الترجمة

`arabic.csv` يضم معرّفات النصوص والنص العربي المنطقي وحالة المراجعة.
لا يتضمن عمود النص الإنجليزي الأصلي. الأرقام الحالية في `stats.json`.
الخانات الفارغة الأصلية محفوظة، وحالة draft تعني أن النص ما زال يحتاج إلى مراجعة بشرية.
`extra_timed_ar.json` للمقاطع المؤقتة، و`speaker_names.json` للأسماء المعتمدة،
و`settings_glossary.json` لتوحيد تسميات الإعدادات.

قواعد التحرير: عربية فصحى ذات معنى، مثل «الانحناء» و«حقيبة الإسعافات»؛ لا نقل
صوتي للإنجليزية في مصطلحات اللعب. احفظ أسماء الشخصيات والأماكن، وأسماء تقنيات
الرسوميات الإنجليزية المعتمدة، ووسوم الأزرار والمتغيرات والتوقيتات.
أبق النص منطقيًا؛ التشكيل وترتيب العرض خاصان ببناء ملفات اللعبة.
''')
    guide=f'''# تثبيت تعريب Metro Exodus — {TAG}

تعريب غير رسمي للحزمة الحالية final_review_r1. أغلق اللعبة قبل التثبيت والاسترجاع.
يلزم إصدار Steam الخاص بـWindows المطابق لبصمات المثبت. النسخة الأصلية للعبة على
Linux ونسخة Enhanced Edition غير مدعومتين.

## Windows

1. حمل `Metro-Arabic-Installer-Windows.exe` من [الإصدار]({BASE}/releases/tag/{TAG}).
2. افتحه وحدد مجلد اللعبة الذي يحتوي على `MetroExodus.exe`؛ يدعم اكتشاف مكتبات Steam.
3. اضغط «فحص الملفات»، ثم «تثبيت التعريب».
4. إذا تعذرت الكتابة في مجلد اللعبة، أغلق المثبت وشغله كمسؤول ثم أعد المحاولة.
5. اترك تفعيل لغة النصوص محددًا، أو اختر English للغة النصوص داخل اللعبة لاحقًا.
   تبقى لغة الأصوات واختياراتها كما حددتها.

## Linux وSteam Deck عبر Proton

**AppImage تطبيق Linux لتثبيت التعريب على نسخة اللعبة الخاصة بـWindows عبر Proton.
لا تشغل المثبت نفسه عبر Proton، ولا تختَر ملفات نسخة اللعبة الأصلية الخاصة بـLinux.**

1. في خصائص اللعبة داخل Steam افتح التوافق، واختر استخدام Proton. انتظر تجهيز نسخة Windows.
2. على Steam Deck انتقل إلى وضع سطح المكتب، وأغلق اللعبة.
3. امنح AppImage صلاحية التنفيذ من خصائص الملف، أو افتح الطرفية في مجلدها:

   ```sh
   chmod +x Metro-Arabic-Installer-Proton-x86_64.AppImage
   ./Metro-Arabic-Installer-Proton-x86_64.AppImage
   ```

4. اختر مجلد اللعبة الذي يحتوي على `MetroExodus.exe`، وغالبًا يكون داخل
   `~/.local/share/Steam/steamapps/common/Metro Exodus` أو مكتبة بطاقة الذاكرة.
   لا تختَر مجلد `compatdata`.
5. افحص الملفات وثبت التعريب. شغله بحسابك المعتاد دون sudo.
6. عند عدم توفر FUSE، استخدم التشغيل مع الاستخراج المؤقت:

   ```sh
   ./Metro-Arabic-Installer-Proton-x86_64.AppImage --appimage-extract-and-run
   ```

متطلبات AppImage: Linux x86_64 وglibc 2.36 أو أحدث؛ مثل Debian 12 وUbuntu 24.04.
Python وQt مدمجان. أجهزة ARM غير مدعومة.

## الاسترجاع واستكشاف الأخطاء

يحفظ المثبت الأصل في `.metro_arabic` داخل مجلد اللعبة. احتفظ به واستخدم زر
«استرجاع الأصل» في المثبت نفسه عند الحاجة. لا يتعامل مع ملفات الحفظ.
إذا انقطعت العملية، اختر المجلد نفسه واسترجع الأصل قبل إعادة التثبيت.
الإصدار غير المطابق أو الملفات المتعارضة يرفضان؛ لا تتجاوز فحص البصمات.
قد يلزم تحديث التعريب بعد تحديث ملفات اللعبة عبر Steam.

يفعل المثبت لغة النصوص في ملفات الإعدادات الموجودة فقط. في Proton يدعم البادئة
المعتادة للعبة Steam رقم 412020. إن لم تظهر العربية، اختر English للغة النصوص.
تبقى الحمولات المثبتة بأدوات قديمة محفوظة؛ يبدأ هذا التطبيق بإدارة نسخته الاحتياطية
بعد التثبيت من داخله.

## حالة الإصدار

هذا إصدار تجريبي قابل للاستخدام ويشمل الحزمة الحالية. مراجعة جميع الحوارات يدويًا
لم تكتمل، واسم المتحدث أبيض مؤقتًا. إصلاح التحميل يعرض النص كاملًا عند أول كشف،
ولا ينفذ حركة كتابة متدرجة من اليمين. لم يجر اختبار لعب جديد داخل المحرك أو على
جهاز Steam Deck. المثبت غير موقع رقميًا.
'''
    write(REPO/'docs/INSTALLATION_AR.md',guide);write(OUT/'INSTALLATION_AR.md',guide)
    qa=dict(windows_backend_cases=20,windows_qt_ui_cases=3,packaged_windows_gui_smoke=True,linux_backend_cases=20,actual_appimage_extract_and_run=True,linux_gui_test='Qt offscreen in isolated x86_64 Linux / glibc2.36',real_asset_install_reinstall_restore=True,game_files_unchanged=True,game_started=False,steam_deck_hardware_tested=False,full_manual_language_review=False)
    write(REPO/'docs/QA.md','''# التحقق من النسخة الحالية

اجتازت اختبارات الملفات العشرين على Windows وLinux، وثلاثة اختبارات لأزرار Qt.
شغل ملف EXE النهائي، وشغلت AppImage الفعلية بالاستخراج المؤقت داخل Linux معزول.
الصورة المرفقة من التطبيق الفعلي. ثبتت الفروقات الحقيقية وأعيد تثبيتها واسترجعت
في مجلد تجريبي منفصل، مع مطابقة البصمات قبل العملية وبعدها.

هذه الاختبارات تثبت عمليات المثبت، ولا تعادل مراجعة لغوية بشرية شاملة أو تجربة لعب
داخل المحرك. لم يشغّل البناء اللعبة، ولم يغيّر تثبيتها الحي. اختبار واجهة Linux
كان خارج الشاشة، ولم تختبر اللعبة عبر Proton على جهاز Steam Deck فعلي.
''')
    write(OUT/'QA.json',json.dumps(qa,indent=2)+'\n')
    metadata=dict(release=TAG,patch_revision='final_review_r1',native_loading_revision='loading_complete_r1',status='public-beta',qa=qa,dependencies=old['dependencies'],linux_libraries=old['linux_libraries'])
    write(OUT/'build-metadata.json',json.dumps(metadata,indent=2)+'\n')
    write(REPO/'docs/BUILD.md','''# تشغيل المثبت من المصدر

المصدر في `installer/`، ويحتوي فروقات التعريب والخط المرخص. لا يحتوي ملفات اللعبة الأصلية.
يلزم Python 3.12. أعد بناء المثبت مع بقاء مكتبات Qt قابلة للاستبدال:

```sh
python -m venv .venv
# Linux:
.venv/bin/python -m pip install -r installer/requirements.txt
.venv/bin/python installer/app.py --review
.venv/bin/python installer/rebuild.py
```

في Windows استخدم `.venv/Scripts/python.exe` بدل `.venv/bin/python`.
ملف rebuild ينشئ ملفًا تنفيذيًا أصليًا للنظام عبر PyInstaller. بناء Windows يعزل
مسار الاعتماديات ويضم طقم C++ المطابق؛ لا يلتقط نسخ ICU الخاصة بأدوات أخرى في PATH.
الفروقات في installer/resources مقيدة ببصمات الإصدار المدعوم. لا توزع EXE اللعبة
أو أرشيفاتها الأصلية. أدوات إعادة إنشاء AppImage نفسها تتطلب بيئة تطوير Linux
وأداة mksquashfs ورانتيم AppImage الرسمي؛ الحزمة المنشورة تحتوي الرانتيم جاهزًا.

```sh
.venv/bin/python installer/test_core.py
QT_QPA_PLATFORM=offscreen .venv/bin/python installer/test_ui.py
```

الاختبارات تستخدم مجلدات مؤقتة. لا تختبر التثبيت على اللعبة الحية ضمن الاختبارات الآلية.
''')
    readme=f'''# تعريب Metro Exodus

تعريب عربي غير رسمي مع مثبت بواجهة عربية، وفحص للإصدار، ونسخة احتياطية واسترجاع.
يدعم إصدار Steam الخاص بـWindows، ونسخته العاملة عبر Proton على Linux وSteam Deck.

[![الإصدار](https://img.shields.io/badge/release-{TAG.replace('-','--')}-ea8c35)]({BASE}/releases/tag/{TAG})
[![الحالة](https://img.shields.io/badge/status-public_beta-orange)]({BASE}/releases)

## التنزيل

| النظام | الملف |
|---|---|
| Windows x86_64 | [مثبت EXE]({DOWNLOAD}/Metro-Arabic-Installer-Windows.exe) |
| Linux وSteam Deck — لعبة Windows عبر Proton | [مثبت AppImage]({DOWNLOAD}/Metro-Arabic-Installer-Proton-x86_64.AppImage) |
| المصدر والفروقات | [Source ZIP]({DOWNLOAD}/Metro-Exodus-Arabic-{TAG}-Source.zip) |
| التحقق من التنزيل | [SHA256SUMS.txt]({DOWNLOAD}/SHA256SUMS.txt) |

**[صفحة الإصدار]({BASE}/releases/tag/{TAG}) · [شرح التثبيت وProton](docs/INSTALLATION_AR.md)**

![واجهة مثبت التعريب](assets/installer-preview.png)

## التثبيت

أغلق اللعبة، وافتح المثبت، وحدد مجلد `MetroExodus.exe`، ثم افحص الملفات وثبت التعريب.
اختر English للغة النصوص إن لم تفعل تلقائيًا. يحفظ التطبيق نسخة من الأصل، ويتيح
استرجاعها من الواجهة. إعداد الصوت وملفات الحفظ لا يتغيران.

**AppImage مخصصة لتثبيت التعريب على نسخة Windows عبر Proton. نسخة اللعبة الأصلية
الخاصة بـLinux وEnhanced Edition غير مدعومتين.** شرح اختيار Proton والتشغيل على
Steam Deck وحل عدم توفر FUSE موجود في [دليل التثبيت](docs/INSTALLATION_AR.md).

## محتويات المشروع

- الحزمة الحالية: `final_review_r1` مع إصلاح نص التحميل `loading_complete_r1`.
- القوائم والإعدادات والحوارات والمقاطع المؤقتة واليوميات والتلميحات والخطوط العربية.
- بيانات الترجمة: 38,221 سجلًا، منها 37,413 نصًا غير فارغ؛ بقية السجلات خانات أصلية فارغة.
- مصطلحات لعب عربية فصحى، مع حفظ أسماء الشخصيات وأسماء تقنيات الرسوميات المعتمدة بالإنجليزية.
- فروقات ثنائية تعمل دون اتصال بالإنترنت بعد تنزيل المثبت، وتفحص النسخة قبل الكتابة.

## حالة الإصدار التجريبي

هذا الإصدار يتيح الحزمة الحالية للتجربة. مراجعة جميع الحوارات يدويًا ما زالت غير مكتملة؛
وجود ترجمة لكل خانة نصية غير فارغة لا يعني اكتمال التدقيق البشري. اسم المتحدث أبيض
مؤقتًا، وفصل لونه البرتقالي لم ينجز. نص التحميل يظهر كاملًا عند أول كشف.
اجتازت عمليات المثبت الاختبارات المعزولة؛ لم يجر اختبار لعب جديد داخل المحرك أو على
جهاز Steam Deck فعلي. التفاصيل في [تقرير التحقق](docs/QA.md).

## المصدر والمساهمة

المثبت في [`installer/`](installer)، وبيانات النص العربي المنطقي في
[`translations/`](translations). راجع [تعليمات التشغيل والبناء](docs/BUILD.md).
عند الإبلاغ عن خطأ، أرفق الجملة والمكان أو صورة، واذكر إصدار اللعبة والمثبت.

## التراخيص

شفرة المشروع وفق [MIT](LICENSE). تراخيص الأطراف الأخرى محفوظة في
[`installer/assets/licenses/`](installer/assets/licenses) و[إشعارات المكتبات](docs/THIRD-PARTY-NOTICES.txt).
الخط Noto Sans Arabic مرخص بـSIL OFL 1.1، وQt/PySide6 بموجب LGPL v3.
Metro Exodus وأصولها مملوكة لأصحابها. المشروع غير رسمي ولا يوزع اللعبة أو EXE الخاص بها؛
توزع الترجمة والخط المرخص والفروقات فقط، ويلزم امتلاك نسخة اللعبة المتوافقة.
'''
    write(REPO/'README.md',readme)
    write(REPO/'CHANGELOG.md',f'''# سجل التغييرات

## {TAG} — 2026-11-04

- أول إصدار عام للحزمة العربية الحالية final_review_r1.
- مثبت Windows EXE ومثبت Linux AppImage لنسخة Windows عبر Proton.
- واجهة عربية مستوحاة من ألوان اللعبة، واكتشاف Steam، وفحص نسخة، ونسخ احتياطي واسترجاع.
- تضمين إصلاح اكتمال نص التحميل والخطوط ومواضع اليوميات والتلميحات وتصحيحات المصطلحات السابقة.
- نشر مصدر المثبت والنصوص العربية المنطقية وشرح التثبيت والبصمات.
- إصدار تجريبي؛ المراجعة اليدوية الشاملة ولون اسم المتحدث البرتقالي ما زالا مفتوحين.
''')
    write(REPO/'.gitignore','''__pycache__/
*.pyc
.venv/
build/
dist/
*.spec
*.exe
*.AppImage
*.vfs0
*.vfx
*.dll
*.pyd
.metro_arabic/
.env
''')
    (REPO/'assets').mkdir(exist_ok=True);shutil.copy2(SOURCE/'معاينة-المثبت.png',REPO/'assets/installer-preview.png')
    write(installer/'README.md','''# مثبت التعريب

راجع [دليل البناء](../docs/BUILD.md) و[التثبيت](../docs/INSTALLATION_AR.md).
الحزمة منشورة كإصدار تجريبي؛ ملفات اللعبة الأصلية لا ترفق بالمصدر.
''')
    sourcezip=OUT/f'Metro-Exodus-Arabic-{TAG}-Source.zip'
    with zipfile.ZipFile(sourcezip,'w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['installer','translations','docs','assets']:
            for p in (REPO/folder).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(REPO).as_posix())
        for name in ['README.md','LICENSE','CHANGELOG.md','.gitignore']:z.write(REPO/name,name)
    notes=f'''أول إصدار عام تجريبي لتعريب **Metro Exodus** — `{TAG}`.

## التنزيل والتثبيت

- **Windows:** حمل `Metro-Arabic-Installer-Windows.exe`.
- **Linux وSteam Deck:** حمل `Metro-Arabic-Installer-Proton-x86_64.AppImage` لتثبيت التعريب على **نسخة Windows عبر Proton فقط**.
- أغلق اللعبة، وحدد مجلد `MetroExodus.exe`، وافحص الملفات ثم ثبت التعريب. يدعم المثبت النسخ الاحتياطي والاسترجاع.
- [شرح التثبيت وProton]({BASE}/blob/{TAG}/docs/INSTALLATION_AR.md).
- `SHA256SUMS.txt` للتحقق من الملفات، وSource ZIP للمصدر والفروقات وبيانات الترجمة.

## الحزمة

تشمل النسخة الحالية `final_review_r1` مع إصلاح التحميل `loading_complete_r1`، والخطوط والقوائم والإعدادات والحوارات واليوميات والتلميحات والمقاطع المؤقتة. بيانات المشروع تضم 37,413 نصًا غير فارغ ضمن 38,221 سجلًا. المثبتان يحتويان فروقات الحزمة اللازمة، ويعملان دون اتصال بعد التنزيل.

## حدود الإصدار التجريبي

مراجعة كل الحوارات يدويًا لم تكتمل، واسم المتحدث أبيض مؤقتًا. إصلاح التحميل يعرض النص كاملًا عند أول كشف، وليس حركة كتابة متدرجة من اليمين. اجتازت عمليات التثبيت والاسترجاع اختبارات معزولة، وشغل EXE النهائي وAppImage الفعلية؛ لم يجر اختبار لعب جديد داخل المحرك أو على Steam Deck فعلي.

يلزم إصدار Steam المتوافق الخاص بـWindows؛ نسخة Linux الأصلية وEnhanced Edition غير مدعومتين. المثبت غير موقع رقميًا. لا تتضمن الحزمة ملفات اللعبة الأصلية، ويلزم امتلاك اللعبة.
'''
    write(OUT/'RELEASE_NOTES_AR.md',notes)
    assets=['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage',sourcezip.name,'INSTALLATION_AR.md','QA.json','build-metadata.json']
    write(OUT/'SHA256SUMS.txt',''.join(sha(OUT/name)+'  '+name+'\n' for name in assets))
    assets.append('SHA256SUMS.txt')
    manifest=dict(repository='exelight7/metro-exodus-arabic',tag=TAG,publication_authorized=True,authorization='User explicitly requested publishing patch and GitHub Release with chosen tag on 2026-11-04.',assets={n:sha(OUT/n) for n in assets})
    write(OUT/'publish-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    # Inspect all outgoing source paths/content. Never copy receipts, backups,
    # local identity/config, original archives or the game executable.
    checked=[]
    for folder in ['installer','translations','docs','assets']:
        for p in (REPO/folder).rglob('*'):
            if not p.is_file():continue
            assert p.suffix.lower() not in ('.exe','.vfx','.vfs0','.dll','.pyd','.appimage')
            assert p.stat().st_size<100_000_000
            if p.suffix.lower() in ('.py','.md','.txt','.json','.csv'):
                text=p.read_text(encoding='utf-8',errors='replace')
                assert not re.search(r'local-user|local-user@|STEAM_USER_ID|C:[/\\]Users[/\\]',text,re.I),str(p)
                assert not re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}',text),str(p)
            checked.append(p.relative_to(REPO).as_posix())
    with zipfile.ZipFile(sourcezip) as z:assert z.testzip() is None
    report=dict(tag=TAG,outgoing_files=len(checked),translation_rows=len(rows),nonempty_targets=stats['nonempty_targets'],no_nonempty_source_without_target=True,original_game_files_published=False,private_local_files_published=False,assets=manifest['assets'])
    write(ROOT/'08_qa/audit/github_publication_preflight.json',json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(outgoing_files=len(checked),translation_rows=len(rows),assets={n:(OUT/n).stat().st_size for n in assets}),indent=2))
if __name__=='__main__':main()
