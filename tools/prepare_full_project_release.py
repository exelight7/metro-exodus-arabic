"""Stage the full shareable authoring project, not the original game or caches."""
from pathlib import Path
import collections, csv, hashlib, json, re, shutil, zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT/'06_build/github_publish'
TAG = 'v0.2.0-beta.2'
OUT = ROOT/'09_release'/TAG
BASE = 'https://github.com/exelight7/metro-exodus-arabic'
DOWNLOAD = BASE+'/releases/download/'+TAG
EXCLUDED = ['01_original/', '02_extracted/raw game resources', '06_build/caches and virtual environments',
            '07_patch/raw game-derived binaries (recover locally from differences)', 'backups/',
            '00_admin/private receipts, locks, sessions and host information',
            'tools/upstream/third-party SDK archives and binaries', '.git/ and credentials']
TEXT = {'.py','.md','.json','.jsonl','.csv','.txt','.yaml','.yml','.ps1','.sh','.desktop','.svg','.xml','.toml','.ini','.cfg'}


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')


def public_text(text):
    for path,label in [(Path.home(),'USER_HOME'),(ROOT.parent,'WORKSPACE')]:
        value=str(path)
        for variant in [value,value.replace('\\','/'),value.replace('\\','\\\\')]:
            text=text.replace(variant,label)
    text=re.sub(r'7656119\d{10}','STEAM_USER_ID',text)
    return re.sub(r'(?i)npxf\d+','local-user',text)


def copy(source, target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if source.suffix.lower() in TEXT:
        raw=source.read_bytes()
        try: text=raw.decode('utf-8-sig'); cleaned=public_text(text)
        except UnicodeError: shutil.copy2(source,target); return
        if cleaned==text: target.write_bytes(raw)
        else: write(target,cleaned)
    else: shutil.copy2(source,target)


def tree(relative):
    for source in sorted((ROOT/relative).rglob('*')):
        if not source.is_file() or any(x in ('__pycache__','upstream','.git') for x in source.parts): continue
        if source.suffix.lower() in ('.pyc','.pyd','.dll','.exe','.zip','.vfs0','.vfx','.skill'): continue
        if source.is_symlink(): raise ValueError('Source symlink: '+str(source))
        copy(source,REPO/source.relative_to(ROOT))


def zip_files(destination, members):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        for source,name in members: archive.write(source,name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(set(archive.namelist()))


def stage():
    assert (REPO/'.git').is_dir() and (REPO/'LICENSE').is_file()
    OUT.mkdir(exist_ok=True)
    for folder in ['03_translation','04_fonts/src','04_fonts/maps','05_media','tools','skills','08_qa']:
        tree(folder)
    # This font is derived from OFL Noto only; original game bitmap atlases are excluded.
    for name in ['noto_arabic_pf.ttf','font_characters.json']:
        copy(ROOT/'04_fonts/build'/name,REPO/'04_fonts/build'/name)
    for name in ['dramatis_records.json','speaker_map.json']:
        copy(ROOT/'02_extracted/steam_local'/name,REPO/'project_seed'/name)
    for name in ['DECISIONS.md','JOURNAL.md','CHANGELOG.md']:
        copy(ROOT/'00_admin'/name,REPO/'docs/history'/name)
    copy(ROOT/'AGENTS.md',REPO/'AGENTS.md')
    copy(ROOT/'STATUS.md',REPO/'docs/history/STATUS.md')
    metadata=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
    metadata['paths']['game_dir']='Set your compatible local Steam game path'
    metadata['local_tools_sources']=['https://github.com/ShokerStlk/MetroEX','https://github.com/tsnest/MetroTools']
    metadata['progress']['installed']=False
    metadata['publication'].update(tag=TAG,status='source_release_prepared',asset_count=None,
                                   release_url=BASE+'/releases/tag/'+TAG)
    metadata['publication'].pop('source_commit',None)
    metadata['portable_recovery']='python tools/recover_project.py --game GAME_PATH --out NEW_WORKSPACE'
    write(REPO/'project.json',json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    vendor=REPO/'tools/vendor/game-arabization/VERSION.json'
    data=json.loads(vendor.read_text(encoding='utf-8'));data['source']='User-supplied game-arabization skill scripts, standard 1.0'
    write(vendor,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    write(REPO/'requirements-project.txt','''# Python 3.12; recovery and current-table rendering
bsdiff4==1.4.1
lz4==4.4.5
Pillow==13.0.0
# Optional legacy font rebuild / native-recipe emulation
fonttools==4.68.0
ispc_texcomp==1.0.1
pefile==2024.8.26
unicorn==2.1.4
''')
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig',newline='')))
    assert len(rows)==38221 and not any(r['source'].strip() and not r['target'].strip() for r in rows)
    # All editable tables and review data must remain byte-identical in the snapshot.
    for source in (ROOT/'03_translation').rglob('*'):
        if source.is_file(): assert digest(source)==digest(REPO/source.relative_to(ROOT)),source.name
    write(REPO/'translations/README.md','''# بيانات الترجمة

النسخة الكاملة المعتمدة للتحرير في [`03_translation/`](../03_translation)، ويشمل
`tables/game.csv` المعرّف والمصدر والهدف وحالة المراجعة. هذا المجلد يبقي تصدير
العربية المختصر المنشور سابقًا للتوافق. لا تعدّل النسختين؛ حرّر الجدول الكامل.
ذاكرة الترجمة والمراجعات والمصطلحات محفوظة بجانبه. لا تعِد توليد الجدول من ذاكرة
المسودات بعد التحرير؛ أداة `rebuild_text.py` تقرأ الهدف الحالي مباشرة.
''')
    write(REPO/'docs/FULL_PROJECT_AR.md',f'''# مصادر المشروع الكاملة — {TAG}

هذه نسخة العمل القابلة للمشاركة: جداول المصدر والترجمة وحالاتها، ذاكرة المسودات،
كل جولات المراجعة والمصطلحات، مصادر أدوات البناء والفحص والمثبت، الخط المرخص،
قياسات الخط، بيانات ربط المتحدثين، القرارات وسجل العمل وتقارير المعاينات السابقة،
والفروقات اللازمة لاستعادة الحزمة الحالية. يسرد `docs/SOURCE_MANIFEST.json`
ملفات النسخة وبصماتها. تقارير الماضي توثق تجارب قديمة وبعضها فاشل؛ المرجع الحالي
`final_review_r1` و`loading_complete_r1` وملخص الحالة في README.

أصول اللعبة التنفيذية وأرشيفاتها والنسخ الاحتياطية وإعدادات جهاز المطور وبيانات
الدخول وبيئات البناء المؤقتة لا توزّع. تُستعاد الملفات المطلوبة محليًا من نسخة
Steam المتوافقة. ليست هذه حزمة لعبة أو مجموعة مفاتيح لفك حماية ملفاتها التنفيذية.

## استعادة بيئة العمل والحزمة الحالية

يلزم Python 3.12 ونسخة Steam الخاصة بـWindows، أو ملفاتها على Linux عبر Proton.
كل ما يلي يكتب إلى مجلد عمل جديد، ويقرأ اللعبة فقط دون تشغيلها.

```sh
python -m pip install -r requirements-project.txt
python tools/recover_project.py --game "/path/to/Metro Exodus" --out "../MetroWork"
```

في Windows يمكن وضع مسار Steam المعتاد بين علامتي اقتباس. الأداة تتحقق من
البصمات، وتستعيد الفهرس و12 أصلًا مطلوبًا ومرحلة التعريب الحالية، وتفحص وصفة
إصلاح التحميل في الذاكرة. لا تنشئ نسخة EXE للعبة. يقبل الفحص النسخة الأصلية
المطابقة أو التعريب الحالي المطابق؛ تتوقف الأداة عند أي اختلاف.

## التحرير دون الرجوع إلى مسودات قديمة

داخل `MetroWork`، عدّل `03_translation/tables/game.csv` بعربية منطقية، ثم:

```sh
python tools/rebuild_text.py --out "../MetroArabicEdited"
```

يحفظ البناء كل الأصول غير النصية، ويلف النص بالقياسات الحالية قبل ترتيب العرض.
إذا أدخلت محرفًا لا يغطيه الخط الحالي يتوقف البناء لتجديد الخط أولًا. الناتج
فهرس وحمولة منفصلان؛ لا يثبتان نفسيهما. يلزم فحصهما قبل إعداد مثبت جديد.

المصادر التاريخية كلها محفوظة في `tools/`، وبعضها يفترض مسارات Windows ومراحل
سابقة. لا تشغّل `build_localization.py` فوق جدول حررته؛ يعيد إدخال ذاكرة المسودات.
أدوات `install_*` القديمة تغيّر الملفات عند تشغيلها صراحة؛ مسار الاستعادة أعلاه
هو المسار المختبر للقراءة وإعادة إنشاء النسخة الحالية. مصدر المثبت الجاهز في
`installer/`، وأدوات بنائه التاريخية في `tools/installer/`.

## Skill وأدوات محرك 4A

الـSkill في [`skills/foura-dialogue/`](../skills/foura-dialogue)، ونسخة مستقلة
بمرفقات الإصدار. انسخ مجلد `foura-dialogue` إلى مجلد skills في مساعدك، ثم أعد
فتح الجلسة. جميع السكربتات والمراجع مرفقة به.

```sh
python tools/foura_dialogue.py probe "/path/to/game"
python tools/foura_dialogue.py list "/path/to/game/patch_04.vfx"
python skills/foura-dialogue/scripts/test_foura_dialogue.py
```

تشمل الأدوات فك تعمية أسماء الملفات بـXOR، وفك ضغط LZ4، وقراءة ترميز LNG،
وتصدير CSV واستيراده وإعادة حزم منفصلة. اختبرت على ملفات Exodus الحقيقية.
VFX 1 و2 لهما اختبارات اصطناعية فقط. QuickLZ القديم وVFI/UPK غير منفذين؛ لا
يعني اشتراك اللعبة في المحرك توافق كل إصدار. راجع [جدول التوافق](../skills/foura-dialogue/references/formats.md).

## حالة الجودة

38,221 سجلًا، منها 37,413 هدفًا غير فارغ. لا توجد خانة مصدر غير فارغة بلا هدف؛
لكن المراجعة البشرية الشاملة لم تكتمل. لون اسم المتحدث البرتقالي ما زال مفتوحًا.
إصلاح التحميل يعرض النص كاملًا عند أول كشف، ولا ينفذ كتابة تدريجية من اليمين.
هذه الحزمة لا تدّعي تحققًا جديدًا داخل اللعبة أو على جهاز Steam Deck فعلي.
''')
    write(REPO/'docs/UPSTREAM_SOURCES.md','''# Format references and third-party provenance

- MetroEX: https://github.com/ShokerStlk/MetroEX — MIT. Used as a VFX/LZ4 format reference; full upstream SDK is not bundled.
- MetroTools: https://github.com/tsnest/MetroTools — repository currently declares no license. Links are format references; its C++ source/libraries are not redistributed or relicensed as this project's MIT code.
- `tools/vendor/game-arabization`: user-supplied standard 1.0 helper scripts retained with their original notices and file hashes in VERSION.json. These are not Codex system skill files.
- `04_fonts/src/NotoSansArabic.ttf`, its presentation-form derivative and installer font: SIL OFL 1.1; see `04_fonts/src/OFL.txt`.
- The standalone 4A helper is independently written Python; its source and tests are included under the project's MIT license.
- Installer dependency notices/licenses remain under `installer/assets/licenses/` and `docs/THIRD-PARTY-NOTICES.txt`.
- Translation source/context is included for editing this localization; Metro Exodus text and game resources remain the property of their respective owners. The project license does not relicense the game.
''')
    guide=(REPO/'docs/INSTALLATION_AR.md').read_text(encoding='utf-8').replace('v0.1.0-beta.1',TAG)
    guide=re.sub(r'v0\.2\.0-beta\.\d+',TAG,guide)
    write(REPO/'docs/INSTALLATION_AR.md',guide);write(OUT/'INSTALLATION_AR.md',guide)
    readme=(REPO/'README.md').read_text(encoding='utf-8').replace('v0.1.0-beta.1',TAG).replace('v0.1.0--beta.1',TAG.replace('-','--'))
    readme=re.sub(r'v0\.2\.0-beta\.\d+',TAG,readme)
    readme=re.sub(r'v0\.2\.0--beta\.\d+',TAG.replace('-','--'),readme)
    readme=readme.replace('Metro-Exodus-Arabic-'+TAG+'-Source.zip','Metro-Exodus-Arabic-'+TAG+'-Full-Project.zip')
    readme=readme.replace('Source ZIP','المشروع كاملًا ZIP')
    readme=readme.replace(TAG+' المختبرة؛ الإضافات','v0.1.0-beta.1 المختبرة؛ الإضافات')
    if '## المشروع الكامل وSkill محرك 4A' not in readme:
        readme=readme.replace('## المصدر والمساهمة','''## المشروع الكامل وSkill محرك 4A

تتضمن هذه النسخة الجداول الكاملة والمصدر والهدف، وذاكرة الترجمة وجميع المراجعات
والأدوات وملفات الخطوط المرخصة وتقارير الفحص وسجل القرارات.

- [دليل المصدر واستعادة بيئة العمل](docs/FULL_PROJECT_AR.md)
- [Skill حوارات 4A](skills/foura-dialogue/SKILL.md) · [التوافق وحدود الدعم](skills/foura-dialogue/references/formats.md)
- [تحميل Skill جاهز]('''+DOWNLOAD+'''/FourA-Dialogue-Skill.zip) · [تحميل الأدوات مستقلة]('''+DOWNLOAD+'''/FourA-Dialogue-Toolkit.zip)

استعادة المشروع تقرأ ملفات اللعبة الأصلية محليًا وتتحقق من البصمات؛ لا توزّع
أرشيفات اللعبة أو ملفاتها التنفيذية. ملفات المثبّت في هذا الإصدار مطابقة لنسخة
v0.1.0-beta.1 المختبرة؛ الإضافات هنا للمصدر وأدوات العمل.

## المصدر والمساهمة''')
    write(REPO/'README.md',readme)
    changelog=(REPO/'CHANGELOG.md').read_text(encoding='utf-8')
    if f'## {TAG}' not in changelog:
        changelog=changelog.replace('# سجل التغييرات','# سجل التغييرات\n\n'+f'''## {TAG} — 2026-11-04

- نشر مصادر العمل الكاملة والجداول وذاكرة الترجمة وجميع المراجعات والمصطلحات.
- Skill مستقل وأدوات VFX/LZ4/LNG لتصدير الحوارات وتحريرها وإعادة حزمها.
- استعادة بيئة العمل من نسخة محلية متوافقة، وبناء النص من الجدول الحالي مباشرة.
- 22 اختبار أدوات و15 ملف لغة حقيقيًا؛ لا ادعاء لدعم جميع ألعاب 4A.
- المثبتان والحزمة العربية مطابقان للإصدار السابق، مع بقاء قيود الجودة المعلنة.
''')
    write(REPO/'CHANGELOG.md',changelog)
    if TAG=='v0.2.0-beta.2':
        text=(REPO/'CHANGELOG.md').read_text(encoding='utf-8')
        text=text.replace('## '+TAG+' — 2026-11-04\n','## '+TAG+' — 2026-11-04\n\n- توحيد بايتات الملفات القديمة بين المستودع وحزمة المصدر؛ فحص بصمات كل ملف قبل النشر.\n')
        write(REPO/'CHANGELOG.md',text)
    write(REPO/'.gitignore','''__pycache__/
*.pyc
.venv/
*.spec
*.exe
*.AppImage
*.vfs0
*.vfx
*.dll
*.pyd
.metro_arabic/
.env
01_original/
02_extracted/
06_build/
07_patch/
09_release/
backups/
tools/upstream/
dist/
''')
    write(REPO/'.gitattributes','* -text\n')
    # Remove any cached bytecode copied by a previous preparation, in this checkout only.
    for path in REPO.rglob('*.pyc'):
        assert path.resolve().is_relative_to(REPO.resolve()); path.unlink()
    files=[p for p in REPO.rglob('*') if p.is_file() and '.git' not in p.relative_to(REPO).parts]
    for path in files:
        relative=path.relative_to(REPO).as_posix()
        assert path.suffix.lower() not in ('.exe','.dll','.pyd','.vfx','.vfs0','.appimage','.pyc'),relative
        if path.suffix.lower() in TEXT:
            text=path.read_text(encoding='utf-8-sig')
            assert not re.search(r'(?i)npxf\d+|7656119\d{10}',text),relative
            assert not re.search(r'(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',text),relative
    manifest=dict(tag=TAG,scope='All shareable authoring sources; originals recovered locally',
                  excluded=EXCLUDED,files={p.relative_to(REPO).as_posix():dict(bytes=p.stat().st_size,sha256=digest(p)) for p in files if p!=REPO/'docs/SOURCE_MANIFEST.json'})
    write(REPO/'docs/SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    summary=dict(files=len(manifest['files']),translation_rows=len(rows),nonempty_targets=sum(bool(r['target'].strip()) for r in rows),
                 translation_sources_preserved=True,original_game_files_included=False,private_receipts_included=False)
    write(ROOT/'08_qa/audit/full_project_preflight.json',json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def package():
    assert (REPO/'docs/SOURCE_MANIFEST.json').is_file()
    previous=ROOT/'09_release/v0.1.0-beta.1'
    for name in ['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage']:
        shutil.copy2(previous/name,OUT/name);assert digest(previous/name)==digest(OUT/name)
    full=OUT/f'Metro-Exodus-Arabic-{TAG}-Full-Project.zip'
    zip_files(full,[(p,p.relative_to(REPO).as_posix()) for p in sorted(REPO.rglob('*')) if p.is_file() and '.git' not in p.relative_to(REPO).parts])
    skill=REPO/'skills/foura-dialogue'
    zip_files(OUT/'FourA-Dialogue-Skill.zip',[(p,'foura-dialogue/'+p.relative_to(skill).as_posix()) for p in sorted(skill.rglob('*')) if p.is_file()]+[(REPO/'LICENSE','foura-dialogue/LICENSE')])
    toolkit=[(skill/'scripts'/name,name) for name in ['foura_dialogue.py','test_foura_dialogue.py','requirements.txt']]
    for name in ['formats.md','workflow.md']:
        text=(skill/'references'/name).read_text(encoding='utf-8').replace('python scripts/foura_dialogue.py','python foura_dialogue.py')
        text=text.replace('relative to the skill directory','relative to the toolkit directory')
        write(OUT/'toolkit-docs'/name,text)
        toolkit.append((OUT/'toolkit-docs'/name,'docs/'+name))
    write(OUT/'TOOLKIT_README.md','''# 4A Dialogue Toolkit 0.2.0

Python 3.10+; `python -m pip install -r requirements.txt`.
`python foura_dialogue.py --help`; `python test_foura_dialogue.py`.
See docs/workflow.md for complete commands and docs/formats.md for compatibility.
Exodus real-file validation; Redux/Arktika fixtures only; legacy QuickLZ/VFI/UPK not implemented.
Extraction and rebuild create separate new outputs and never launch/install a game.
''')
    toolkit += [(OUT/'TOOLKIT_README.md','README.md'),(REPO/'LICENSE','LICENSE')]
    zip_files(OUT/'FourA-Dialogue-Toolkit.zip',toolkit)
    shutil.copy2(REPO/'docs/FULL_PROJECT_AR.md',OUT/'FULL_PROJECT_AR.md')
    qa=json.loads((ROOT/'08_qa/audit/foura_real_validation.json').read_text(encoding='utf-8'))
    qa.update(synthetic_tool_tests=22,skill_validated=True,installer_binaries_unchanged=True,
              source_recovery=json.loads((ROOT/'08_qa/audit/full_project_recovery.json').read_text(encoding='utf-8')))
    write(OUT/'QA.json',json.dumps(qa,indent=2)+'\n')
    notes=f'''مصادر المشروع الكاملة وأدوات حوارات محرك **4A** — `{TAG}`.

- `Metro-Exodus-Arabic-{TAG}-Full-Project.zip`: جداول المصدر والترجمة والذاكرة وجميع المراجعات والمصطلحات، وأدوات البناء والفحص والمثبت، والخط المرخص وتقارير العمل وSkill.
- `FourA-Dialogue-Skill.zip`: Skill جاهز مع السكربتات والمراجع؛ انسخ مجلد `foura-dialogue` إلى مجلد skills في مساعدك.
- `FourA-Dialogue-Toolkit.zip`: أدوات مستقلة لفك تعمية أسماء XOR وضغط LZ4 وترميز LNG، وتصدير CSV واستيراده وإعادة حزم VFX في مجلد منفصل.
- مثبت EXE لـWindows وAppImage لـLinux/Steam Deck لتثبيت التعريب على **نسخة Windows عبر Proton**. المثبتان والحزمة مطابقان للإصدار السابق.

أداة الاستعادة تعيد إنشاء بيئة العمل والحزمة من نسخة اللعبة المحلية المتوافقة، دون تشغيل اللعبة أو الكتابة في ملفاتها. ابدأ بـ`FULL_PROJECT_AR.md`.

**التحقق:** 22 اختبارًا للأدوات، وفحص استخراج/إعادة بناء 15 ملف لغة حقيقيًا، وإعادة إنتاج ملف الحوار الحالي وبصمات الحزمة في مجلد منفصل. VFX 1/2 اختبرا ببيانات اصطناعية فقط؛ QuickLZ القديم وVFI/UPK غير منفذين. لا يوجد ادعاء دعم شامل لكل ألعاب المحرك.

**الحالة:** إصدار تجريبي. جميع النصوص المستخرجة لها أهداف، لكن تدقيق كل الحوارات يدويًا لم يكتمل؛ لون اسم المتحدث البرتقالي ما زال مفتوحًا. إصلاح التحميل يظهر النص كاملًا عند أول كشف. لم يجر اختبار لعب جديد أو اختبار على جهاز Steam Deck فعلي. لا توزع أصول اللعبة أو ملفاتها التنفيذية أو إعدادات المطور؛ يلزم امتلاك الإصدار المتوافق.
'''
    write(OUT/'RELEASE_NOTES_AR.md',notes)
    names=['Metro-Arabic-Installer-Windows.exe','Metro-Arabic-Installer-Proton-x86_64.AppImage',full.name,
           'FourA-Dialogue-Skill.zip','FourA-Dialogue-Toolkit.zip','FULL_PROJECT_AR.md','INSTALLATION_AR.md','QA.json']
    write(OUT/'SHA256SUMS.txt',''.join(digest(OUT/n)+'  '+n+'\n' for n in names));names.append('SHA256SUMS.txt')
    manifest=dict(repository='exelight7/metro-exodus-arabic',tag=TAG,publication_authorized=True,
                  authorization='User requested publishing all project files, a Skill and 4A dialogue tools on 2026-11-04.',
                  assets={name:digest(OUT/name) for name in names})
    write(OUT/'publish-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({name:(OUT/name).stat().st_size for name in names},indent=2))


if __name__=='__main__':
    import sys
    if '--package' in sys.argv: package()
    else: stage()
