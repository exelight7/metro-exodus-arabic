# تشغيل المثبت من المصدر

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
