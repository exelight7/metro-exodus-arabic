# تعريب Metro Exodus

تعريب عربي غير رسمي، مع مثبت بواجهة عربية ونسخة احتياطية واسترجاع.

[![الإصدار](https://img.shields.io/badge/release-v1.0.0-brightgreen)](https://github.com/exelight7/metro-exodus-arabic/releases/tag/v1.0.0)
[![الحالة](https://img.shields.io/badge/status-stable-brightgreen)](https://github.com/exelight7/metro-exodus-arabic/releases/tag/v1.0.0)

## التنزيل

| النظام | الملف |
|---|---|
| Windows x86_64 | [مثبت EXE](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/Metro-Arabic-Installer-Windows.exe) |
| Linux وSteam Deck — لعبة Windows عبر Proton | [مثبت AppImage](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/Metro-Arabic-Installer-Proton-x86_64.AppImage) |
| المشروع كاملًا | [ملفات المشروع ZIP](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/Metro-Exodus-Arabic-v1.0.0-Full-Project.zip) |
| Skill حوارات محرك 4A | [Skill](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/FourA-Dialogue-Skill.zip) |
| أدوات حوارات محرك 4A | [Toolkit](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/FourA-Dialogue-Toolkit.zip) |
| بصمات الملفات | [SHA256SUMS](https://github.com/exelight7/metro-exodus-arabic/releases/download/v1.0.0/SHA256SUMS.txt) |

**[صفحة الإصدار](https://github.com/exelight7/metro-exodus-arabic/releases/tag/v1.0.0) · [شرح التثبيت وProton](docs/INSTALLATION_AR.md)**

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
