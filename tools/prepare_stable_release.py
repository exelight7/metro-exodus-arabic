"""Stage/package the user-authorized stable release, with honest review coverage."""
from pathlib import Path
import csv,json,shutil,hashlib,re,zipfile
import prepare_full_project_release as full
ROOT=Path(__file__).resolve().parents[1];TAG='v1.0.0';REPO=ROOT/'06_build/github_publish';OUT=ROOT/'09_release'/TAG
BASE='https://github.com/exelight7/metro-exodus-arabic';URL=BASE+'/releases/tag/'+TAG;DOWNLOAD=BASE+'/releases/download/'+TAG
def write(p,s):full.write(p,s)
def sha(p):return full.digest(p)
def stage():
 full.TAG=TAG;full.OUT=OUT;full.DOWNLOAD=DOWNLOAD
 full.stage()
 for n in ['app.py','core.py','test_core.py','test_ui.py']:
  full.copy(ROOT/'tools/installer'/n,REPO/'installer'/n)
 for p in (ROOT/'06_build/installer_resources').iterdir():
  if p.is_file() and p.name!='build-inputs.json':full.copy(p,REPO/'installer/resources'/p.name)
 shutil.copy2(ROOT/'08_qa/render_tests/installer_windows_exe.png',REPO/'assets/installer-preview.png')
 rebuild=REPO/'installer/REBUILD.txt'
 if rebuild.exists():write(rebuild,rebuild.read_text(encoding='utf8').replace('review edition','stable edition').replace('The UI is pending owner approval.','Publication of this release was explicitly authorized by the project owner.'))
 report=json.loads((ROOT/'08_qa/audit/full_language_r1.json').read_text(encoding='utf8'))
 write(REPO/'translations/stats.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 with (ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 with (REPO/'translations/arabic.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['id','target','status']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in rows)
 guide=(REPO/'docs/INSTALLATION_AR.md').read_text(encoding='utf8').replace('final_review_r1','full_language_r1')
 guide=guide.replace('## Windows','**إذا ثبّتَّ إصدارًا قديمًا، استرجع الأصل بمثبته القديم أولًا، ثم استخدم هذا الإصدار.** لا يقبل المثبت فهرس تعريب قديمًا غير مطابق لبصمته.\n\n## Windows',1)
 write(REPO/'docs/INSTALLATION_AR.md',guide);write(OUT/'INSTALLATION_AR.md',guide)
 notes=f'''تعريب **Metro Exodus — {TAG}**، إصدار مستقر غير تجريبي.

- تحديث الحزمة والمثبتين بجميع التصحيحات المعتمدة في هذه الجولة.
- رُوجع **23,500** سجل مقابل الأصل، وعُدّل **12,618** منها؛ بقي **14,721** سجلًا لم تكتمل مراجعته في الجولة الحالية، و**4** مواضع ملتبسة محفوظة للتثبت.
- فُحصت بنية **38,221** سجلًا و**38,223** سلسلة عرض. بقيت المعرّفات والمصادر والوسوم والتوقيتات والأصول غير النصية محفوظة.
- تضمين المشروع القابل للتحرير كاملًا، والجداول والمراجعات والمسرد وأدوات البناء، وSkill وأدوات حوارات 4A.
- EXE لـWindows، وAppImage لـLinux وSteam Deck لتثبيت التعريب على **نسخة Windows من اللعبة عبر Proton فقط**. نسخة Linux الأصلية وEnhanced Edition غير مدعومتين.

**الترقية:** استرجع الأصل بمثبت الإصدار القديم أولًا. يدعم هذا المثبت الملفات المطابقة فقط، ويحفظ الأصل ويتيح الاسترجاع. ابدأ بـ`INSTALLATION_AR.md`.

**التحقق:** 20 اختبارًا لعمليات المثبت، وفحص واجهته المجمعة على Windows، وتشغيل AppImage في Linux معزول. تثبيت/إعادة تثبيت/استرجاع الفروق الحقيقية نجح في مجلد مؤقت. لم تُشغّل اللعبة ولم تُعدّل ملفاتها المثبتة.

**حدود الجودة:** «مستقر» وصف لحالة الإصدار على GitHub؛ لا يعني اكتمال التدقيق اللغوي لكل سطر أو خلو اللعبة من الأخطاء. اسم المتحدث ما زال أبيض مؤقتًا؛ البرتقالي المستقل لم ينجز. إصلاح التحميل يعرض النص كاملًا عند أول كشف، ولا ينفذ كتابة تدريجية من اليمين. لا يوجد اختبار لعب جديد أو اختبار على Steam Deck فعلي.

الملفات المرفقة: المثبتان، ZIP المشروع الكامل، Skill وToolkit لمحرك 4A، الأدلة، تقرير التحقق وبصمات SHA256. لا تتضمن النسخة أرشيفات اللعبة الأصلية أو ملفها التنفيذي أو بيانات جهاز المطور. تُستعاد أصول البناء محليًا من نسخة مملوكة متوافقة.
'''
 write(OUT/'RELEASE_NOTES_AR.md',notes)
 write(REPO/'docs/QA.md','# تحقق الإصدار '+TAG+'\n\n'+notes+'\nتفاصيل الأعداد والمواضع الملتبسة في `08_qa/audit/full_language_r1.json`.\n')
 readme=f'''# تعريب Metro Exodus

تعريب عربي غير رسمي، مع مثبت بواجهة عربية ونسخة احتياطية واسترجاع.

[![الإصدار](https://img.shields.io/badge/release-v1.0.0-brightgreen)]({URL})
[![الحالة](https://img.shields.io/badge/status-stable-brightgreen)]({URL})

## التنزيل

| النظام | الملف |
|---|---|
| Windows x86_64 | [مثبت EXE]({DOWNLOAD}/Metro-Arabic-Installer-Windows.exe) |
| Linux وSteam Deck — لعبة Windows عبر Proton | [مثبت AppImage]({DOWNLOAD}/Metro-Arabic-Installer-Proton-x86_64.AppImage) |
| المشروع كاملًا | [ملفات المشروع ZIP]({DOWNLOAD}/Metro-Exodus-Arabic-{TAG}-Full-Project.zip) |
| Skill حوارات محرك 4A | [Skill]({DOWNLOAD}/FourA-Dialogue-Skill.zip) |
| أدوات حوارات محرك 4A | [Toolkit]({DOWNLOAD}/FourA-Dialogue-Toolkit.zip) |
| بصمات الملفات | [SHA256SUMS]({DOWNLOAD}/SHA256SUMS.txt) |

**[صفحة الإصدار]({URL}) · [شرح التثبيت وProton](docs/INSTALLATION_AR.md)**

![واجهة المثبت](assets/installer-preview.png)

## التثبيت

أغلق اللعبة، وافتح المثبت، وحدد مجلد `MetroExodus.exe`، ثم افحص الملفات وثبت التعريب.
اختر English للغة النصوص إن لم تُفعّل تلقائيًا. إذا كنت تستخدم إصدارًا قديمًا من التعريب،
استرجع الأصل بمثبته القديم أولًا، ثم ثبت هذا الإصدار. تبقى ملفات الحفظ وإعدادات الصوت محفوظة.

**AppImage لتثبيت التعريب على لعبة Windows عبر Proton؛ لا تشغّل المثبت نفسه عبر Proton.
نسخة اللعبة الأصلية لـLinux وEnhanced Edition غير مدعومتين.**

## المراجعة والجودة

الحزمة `full_language_r1` تشمل النصوص الحالية كلها: 38,221 سجلًا، منها 37,413 غير فارغ.
رُوجع في الجولة 23,500 سجل، وأُصلح 12,618 منها. بقي 14,721 سجلًا لم تكتمل مراجعته،
و4 مواضع تحتاج قرينة إضافية. الإصدار مستقر على GitHub؛ المراجعة اللغوية الشاملة غير مكتملة.

كلام الحوار أبيض، واسم المتحدث أبيض مؤقتًا؛ فصل الاسم بالبرتقالي لم ينجز. التحميل يعرض
النص كاملًا عند أول كشف، ولا ينفذ حركة كتابة RTL. اجتازت البنية والمثبت الاختبارات المعزولة؛
لا يوجد اختبار لعب جديد أو اختبار على Steam Deck فعلي. [التقرير](docs/QA.md).

## المشروع والأدوات

تشمل المصادر الجداول بالمصدر والهدف، والمسرد وجولات المراجعة وذاكرة المسودات، وأدوات
البناء والفحص والمثبت، والخط المرخص وقياساته، وسجل القرارات وSkill محرك 4A.

- [دليل المشروع واستعادة بيئة العمل](docs/FULL_PROJECT_AR.md)
- [Skill حوارات 4A](skills/foura-dialogue/SKILL.md) · [التوافق](skills/foura-dialogue/references/formats.md)
- [الجداول](03_translation/tables/game.csv) · [مصدر المثبت](installer/) · [البناء](docs/BUILD.md)

لا توزع ملفات اللعبة الأصلية؛ تعيد أداة الاستعادة بناء الحزمة محليًا من نسخة متوافقة،
دون تشغيلها. دعم أدوات 4A يعتمد على صيغة الملف، وليس مجرد اسم المحرك.
'''
 write(REPO/'README.md',readme)
 doc=(REPO/'docs/FULL_PROJECT_AR.md').read_text(encoding='utf8').replace('`final_review_r1`','`full_language_r1`')
 write(REPO/'docs/FULL_PROJECT_AR.md',doc+'\n## تغطية الجولة الحالية\n\nرُوجع 23,500 سجل وعدّل 12,618؛ بقي 14,721 خارج التغطية و4 مواضع ملتبسة. سجل القرارات محفوظ في `03_translation/review/full_language_r1/`.\n')
 change=(REPO/'CHANGELOG.md').read_text(encoding='utf8')
 if '## v1.0.0' not in change:write(REPO/'CHANGELOG.md',change.replace('# سجل التغييرات','# سجل التغييرات\n\n## v1.0.0 — 2026-11-06\n\n- إصدار مستقر مع مثبتين جديدين، والمصدر الكامل.\n- مراجعة 23,500 سجل وتصحيح 12,618 منها؛ لم تكتمل المراجعة الشاملة.\n- حفظ الوسوم والمصادر والأصول غير النصية، والتحقق من التثبيت والاسترجاع في بيئة مؤقتة.\n'))
 # Refresh the manifest after all generated/staged files, so it describes exact Git bytes.
 manifest=json.loads((REPO/'docs/SOURCE_MANIFEST.json').read_text(encoding='utf8'))
 files=[p for p in REPO.rglob('*') if p.is_file() and '.git' not in p.relative_to(REPO).parts and p!=REPO/'docs/SOURCE_MANIFEST.json']
 for p in files:
  assert p.suffix.lower() not in ('.exe','.dll','.pyd','.vfx','.vfs0','.appimage','.pyc'),p
  if p.suffix.lower() in full.TEXT:
   t=p.read_text(encoding='utf-8-sig');assert not re.search(r'(?i)npxf\d+|7656119\d{10}|(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',t),p
 manifest['files']={p.relative_to(REPO).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files};manifest['tag']=TAG
 write(REPO/'docs/SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Staged complete public source:',len(files),'files')
def package():
 OUT.mkdir(exist_ok=True)
 for name in ['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage']:
  shutil.copy2(ROOT/'09_release/installer-review'/name,OUT/name)
 name=f'Metro-Exodus-Arabic-{TAG}-Full-Project.zip'
 full.zip_files(OUT/name,[(p,p.relative_to(REPO).as_posix()) for p in sorted(REPO.rglob('*')) if p.is_file() and '.git' not in p.relative_to(REPO).parts])
 # Reuse the already validated, unchanged standalone Skill/toolkit bytes.
 for n in ['FourA-Dialogue-Skill.zip','FourA-Dialogue-Toolkit.zip']:
  shutil.copy2(ROOT/'09_release/v0.2.0-beta.2'/n,OUT/n)
 shutil.copy2(REPO/'docs/FULL_PROJECT_AR.md',OUT/'FULL_PROJECT_AR.md')
 qa={n:json.loads((ROOT/'08_qa/audit'/n).read_text(encoding='utf8')) for n in ['full_language_r1.json','installer_windows_smoke.json','installer_real_transaction.json']}
 assert qa['installer_windows_smoke.json']['exe_sha256']==sha(OUT/'Metro-Arabic-Installer-Windows.exe')
 assert (ROOT/'06_build/installer_linux_qa/serial.log').stat().st_mtime>(OUT/'Metro-Arabic-Installer-Proton-x86_64.AppImage').stat().st_mtime
 qa['linux_smoke_passed']=all(s in (ROOT/'06_build/installer_linux_qa/serial.log').read_text(errors='replace') for s in ['EXTRACT_EXIT:0','CORE_TEST_EXIT:0','UI_TEST_EXIT:0','LINUX_QA_DONE'])
 assert qa['linux_smoke_passed']
 write(OUT/'QA.json',json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
 names=['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage',name,'FourA-Dialogue-Skill.zip','FourA-Dialogue-Toolkit.zip','FULL_PROJECT_AR.md','INSTALLATION_AR.md','QA.json']
 write(OUT/'SHA256SUMS.txt',''.join(sha(OUT/n)+'  '+n+'\n' for n in names));names.append('SHA256SUMS.txt')
 write(OUT/'publish-manifest.json',json.dumps({'repository':'exelight7/metro-exodus-arabic','tag':TAG,'publication_authorized':True,'stable':True,'full_source':True,'authorization':'User explicitly requested light finishing, complete GitHub upload, and a stable final release on 2026-11-06.','assets':{n:sha(OUT/n) for n in names}},ensure_ascii=False,indent=2)+'\n')
 print('Packaged:',{n:(OUT/n).stat().st_size for n in names})
if __name__=='__main__':
 import sys
 package() if '--package' in sys.argv else stage()
