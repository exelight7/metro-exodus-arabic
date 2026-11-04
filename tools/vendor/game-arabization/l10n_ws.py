#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
l10n_ws.py - workspace manager for game Arabization projects.

Executable definition of the shared project standard L10N-STD (l10n-std: 1.0),
used by the skills `game-arabization-workspace` (the standard) and
`game-arabization` (the toolbox, incl. references/engines/unity.md and unreal.md).
The LAYOUT table below IS the standard: docs describe it, this file enforces it.

Commands
  init DIR --game NAME [--engine unity|unreal|ue3|other] [--game-version V]
           [--roles tech,translation,operator] [--vendor] [--git]
  check   [--verify-originals] [--strict] [--json]     exit 1 on ERROR
  status  [--write]                                     progress; --write updates STATUS.md
  owner   PATH [--role ROLE]                            exit 0 allowed, 3 not your folder
  snapshot --from GAME_DIR --version V [--set-current] [REL_PATH|GLOB ...]   pristine copies + SHA256SUMS
  backup  FILE... --step NAME [--base DIR]              backups/pre_<step>_<ts>/
  restore BACKUP_DIR [--to DIR] [--yes]                 dry run unless --yes
  decision "TEXT" --why "REASON" [--role R] [--supersedes D-003] [--evidence PATH]
  build   [--list] [--only STEP]... [--from STEP] [--dry-run] [--keep-going]
  vendor  [--from SCRIPTS_DIR] [--update]               pin game-arabization scripts in tools/vendor
  sync    [--skills-dir DIR]...                         skills / docs / project / vendored tools agree?
  pack    [--out FILE.zip]                              zip of irreplaceable files (authored+evidence)
  clean   [--yes] [--all]                               empty build outputs (proves rebuildability); --all adds 02_extracted/incoming

Pipeline steps (project.json "pipeline"): {"name","run","enabled","modes","note"}; "run" is a shell
command with placeholders {py} {scripts} {root} {ver} {slug} {game} {mode} {table} + "vars" (and
{<var>_name} = the var's file name), or a
builtin: @copy SRC DST | @seed SRC DST (copy only if DST missing) | @mkdir DIR.

Terminal output is English on purpose (bidi-safe in any console); the files it
writes (READMEs, STATUS.md, DECISIONS.md...) are Arabic.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import zipfile

STD = '1.0'
TOOL = 'l10n_ws.py'

CLASSES = {
    'original':  ('أصل', 'قراءة فقط + SHA256SUMS. لا يعدل، لا git، لا يوزع. البناء يقرأ منه دائما.'),
    'authored':  ('مؤلف', 'شغل يدوي لا يعوض: git + نسخة احتياطية (pack).'),
    'generated': ('مولد', 'يعاد بأمر build؛ يحذف بأمان (clean)؛ لا git؛ لا تعدله يدويا.'),
    'evidence':  ('دليل', 'لقطات وتقارير تثبت القرارات: تحفظ ولا تعدل.'),
    'backup':    ('نسخ أمان', 'نسخة قبل كل تعديل؛ لا تحذف قبل الإطلاق؛ لا git.'),
    'release':   ('إصدار', 'ما نشر فعلا؛ لا يتغير بعد النشر؛ لا git.'),
    'vendor':    ('أدوات مثبتة', 'نسخة مثبتة من سكربتات الـskill لإعادة البناء بنفس الأدوات؛ git؛ لا تعديل محلي.'),
}

ROLES = collections.OrderedDict([
    ('tech', 'التقنية (الرئيسية): فك، استخراج، خطوط، بناء، حقن، باتش، تركيب'),
    ('translation', 'الترجمة: الجداول، المسرد، ترجمة الكتسينات'),
    ('textfont', 'النص/الخط: مكتبة تشكيل/قياس خاصة بالمشروع (اختياري)'),
    ('review', 'المراجعة اللغوية (اختياري)'),
    ('operator', 'المشغل البشري: يشغل اللعبة ويصور'),
])

# (path, class, owner, contents, never)  -- longest prefix wins
LAYOUT = [
    ('00_admin', 'authored', 'tech', 'DECISIONS.md (سجل القرارات)، CHANGELOG.md، sessions/، prompts/', 'ملفات لعبة أو مخرجات بناء'),
    ('00_admin/sessions', 'authored', '*', 'ملف لكل دور <role>.md: حالته وطلباته. كل دور يكتب ملفه فقط', 'ملفات غير .md'),
    ('00_admin/prompts', 'authored', 'tech', 'برومتات الجلسات المعبأة لهذا المشروع', ''),
    ('01_original', 'original', 'tech', '<إصدار اللعبة>/ نسخ أصلية للملفات اللي بتعدل (بمساراتها) + SHA256SUMS — عبر snapshot فقط', 'أي تعديل؛ أي ملف معدل'),
    ('02_extracted', 'generated', 'tech', '<إصدار اللعبة>/ مخرجات الفك والاستخراج كما خرجت من الأدوات (dump، locres، ufont...)', 'تعديل يدوي — التعديل مكانه 03_translation'),
    ('03_translation', 'authored', 'translation', 'glossary.csv (المسرد)، puns.csv (التلاعب اللفظي)', 'نص مشكل مسبقا (presentation forms)'),
    ('03_translation/tables', 'authored', 'translation', 'جداول الترجمة الرئيسية: مفتاح + source + target (+status...) — عربي منطقي دائما', 'نسخ بأسماء final/copy/v2؛ نص مشكل مسبقا'),
    ('03_translation/review', 'authored', 'review', 'تقارير المراجعة اللغوية واقتراحاتها', 'تعديل الجداول مباشرة'),
    ('03_translation/tm', 'authored', 'translation', '<إصدار>/ لقطات الجداول من إصدارات سابقة (ذاكرة ترجمة لـtm_fill)', ''),
    ('03_translation/incoming', 'generated', 'translation', '<إصدار جديد>/ التصدير الخام من الأدوات قبل دمجه بـtm_fill', 'ترجمة يدوية هنا'),
    ('04_fonts', 'authored', 'tech', 'كل ما يخص الخطوط', ''),
    ('04_fonts/src', 'authored', 'tech', 'الخطوط المصدر (لاتيني اللعبة المستخرج + العربي) + ملف ترخيص لكل خط', 'خط بدون ترخيص'),
    ('04_fonts/maps', 'authored', 'tech', 'جداول الخانات (charset_remap map.json) وجداول العروض — ضياعها = استحالة أي تعديل لاحق', ''),
    ('04_fonts/build', 'generated', 'tech', 'الخطوط والأطالس المولدة (font_merge، presforms، tmp_sdf_atlas، BMFont)', 'تعديل يدوي'),
    ('05_media', 'authored', 'tech', 'الوسائط: video/ (كتسينات) وtextures/ (صور فيها نص)', ''),
    ('05_media/video/subs', 'authored', 'translation', 'ترجمة الكتسينات: CSV/SRT/ASS بعد التحرير', ''),
    ('05_media/video/out', 'generated', 'tech', 'المقاطع المحروقة/المعاد تغليفها + لقطات VERIFY', ''),
    ('05_media/textures/src', 'authored', 'tech', 'ملفات تصميم الصور النصية (PSD/XCF/SVG)', ''),
    ('05_media/textures/out', 'generated', 'tech', 'الصور النهائية بصيغة اللعبة', ''),
    ('06_build', 'generated', 'tech', 'كل المخرجات الوسيطة: text/ (الجداول المشكلة)، stage/، sim/، logs/', 'أي شيء لا يعاد توليده'),
    ('07_patch', 'generated', 'tech', 'شجرة الباتش بنفس مسارات مجلد اللعبة (هذا اللي يركب)', 'ملفات لم تتغير عن الأصل'),
    ('08_qa', 'evidence', 'tech', 'bugs.csv وكل أدلة الجودة', ''),
    ('08_qa/render_tests', 'evidence', 'tech', 'حزم T01–T14 وصور simulate_render', ''),
    ('08_qa/shots', 'evidence', 'operator', 'لقطات اللعبة: YYYYMMDD_<Txx|batch>_<screen>_<nn>.png', 'صور معدلة'),
    ('08_qa/audit', 'generated', 'tech', 'تقارير l10n_audit وfont_check (تعاد بـbuild)', ''),
    ('09_release', 'release', 'tech', 'v<X.Y.Z>/ الباتش المنشور + RELEASE.md', 'تعديل إصدار بعد نشره'),
    ('tools', 'authored', 'tech', 'l10n_ws.py + سكربتات خاصة بالمشروع', ''),
    ('tools/textlib', 'authored', 'textfont', 'مكتبة تشكيل/قياس خاصة بالمشروع (إن وجدت)', ''),
    ('tools/vendor', 'vendor', 'tech', 'game-arabization/: نسخة مثبتة من سكربتات الـskill (VERSION.json)', 'تعديل محلي — عدل الـskill ثم vendor --update'),
    ('backups', 'backup', 'tech', 'pre_<step>_<YYYYmmdd-HHMMSS>/ بنفس المسارات + SHA256SUMS + ORIGIN.json؛ authored_*.zip', 'حذف قبل الإطلاق'),
]
ROOT_FILES = {'project.json': 'tech', 'STATUS.md': 'tech', 'README.md': 'tech', '.gitignore': 'tech', '.gitattributes': 'tech'}
TOP = sorted({p.split('/')[0] for p, *_ in LAYOUT})
TABLE_STATUS = ['todo', 'draft', 'translated', 'reviewed', 'final', 'skip']
RENDER_MODES = ['undecided', 'logical', 'visual', 'forms', 'reorder', 'wrap']
KEY_SETS = [['id'], ['namespace', 'key'], ['file', 'section', 'key', 'occurrence'], ['key']]
GLOSSARY_COLS = ['source', 'target', 'type', 'gender', 'forbidden', 'notes']
PUNS_COLS = ['id', 'source', 'decision', 'target', 'notes']
BUGS_COLS = ['id', 'date', 'status', 'severity', 'screen', 'description', 'evidence', 'fix', 'decision']
PF_RE = re.compile('[\ufb50-\ufdff\ufe70-\ufefc]')
STD_MARK = re.compile(r'l10n-std:\s*(\d+\.\d+)')
FAMILY = {  # skill name -> files inside the skill that must carry the marker
    'game-arabization-workspace': ['SKILL.md'],
    'game-arabization': ['SKILL.md', 'references/project-layout.md',
                         'references/engines/unity.md', 'references/engines/unreal.md'],
}
NOT_REBUILDABLE = ['02_extracted', '03_translation/incoming']   # generated, but clean skips them unless --all
OUT_ARG = re.compile(r'(?:^|\s)(?:-o|--out|--output|--report|--issues|--out-font|--out-map)\s+("[^"]+"|\S+)')
GEN_DIRS = ['06_build/text', '06_build/stage', '06_build/sim', '06_build/logs', '07_patch',
            '08_qa/audit', '04_fonts/build']
EXT_HOME = {'.csv': '03_translation/tables', '.tsv': '03_translation/tables', '.po': '03_translation/tables',
            '.ttf': '04_fonts/src', '.otf': '04_fonts/src', '.png': '08_qa/shots', '.jpg': '08_qa/shots',
            '.mp4': '05_media/video', '.usm': '05_media/video', '.bk2': '05_media/video', '.webm': '05_media/video',
            '.ass': '05_media/video/subs', '.srt': '05_media/video/subs', '.py': 'tools', '.ps1': 'tools',
            '.zip': '09_release or backups', '.md': '00_admin', '.txt': '00_admin', '.json': '02_extracted or 03_translation',
            '.pak': '01_original or 07_patch', '.locres': '02_extracted', '.ufont': '02_extracted',
            '.assets': '01_original', '.bundle': '01_original', '.int': '01_original'}
BAD_NAME = re.compile(r'(?i)(final|copy|fixed|temp|tmp|backup|(^|[_\-. ])v\d+$|[_\-. ](new|old)$|\(\d+\)|نسخة|نهائي|معدل|جديد)')

# ---------------------------------------------------------------- pipelines
# Placeholders: {py} {scripts} {root} {ver} {slug} {game} {mode} {table} + project.json "vars".
# A var whose value still looks like <...> blocks the build until filled.
COMMON_TAIL = [
    {'name': 'audit', 'run': '{py} {scripts}/l10n_audit.py {table} --glossary 03_translation/glossary.csv '
                             '--report 08_qa/audit/audit.md --issues 08_qa/audit/issues.csv',
     'note': 'لازم 0 ERROR قبل أي حقن'},
    {'name': 'shape', 'modes': ['visual', 'forms', 'reorder', 'wrap'],
     'run': '{py} {scripts}/ar_shape.py --mode {mode} --csv {table} --column target -o 06_build/text/build.csv',
     'note': 'للمحركات اللي ما تشكل (قرار المرحلة C). أضف --wrap-px/--font/--size إذا تلف بنفسك'},
    {'name': 'pass_logical', 'modes': ['logical'], 'run': '@copy {table} 06_build/text/build.csv',
     'note': 'المحرك يشكل بنفسه: النص يبقى منطقي'},
]
SHAPING = ['visual', 'forms', 'reorder', 'wrap']
FONT_STEPS = [
    {'name': 'font_merge', 'run': '{py} {scripts}/font_merge.py {latin_font} 04_fonts/src/{arabic_font} '
                                  '-o 04_fonts/build/merged.ttf --auto-scale --fit-metrics',
     'note': 'لاتيني اللعبة (02_extracted) + العربي المرخص (04_fonts/src)'},
    {'name': 'presforms', 'modes': SHAPING,
     'run': '{py} {scripts}/font_add_presforms.py 04_fonts/build/merged.ttf 04_fonts/build/merged_pf.ttf',
     'note': 'نص مشكل مسبقاً يحتاج نقاط presentation forms في الخط'},
    {'name': 'pass_font', 'modes': ['logical'], 'run': '@copy 04_fonts/build/merged.ttf 04_fonts/build/merged_pf.ttf'},
    {'name': 'font_check', 'run': '{py} {scripts}/font_check.py 04_fonts/build/merged_pf.ttf --text {table} --column target',
     'note': 'لازم 0 ناقص'},
]
PIPELINES = {
    'unity': {
        'vars': {'data': '<Game>_Data', 'latin_font': '02_extracted/{ver}/fonts/<Latin>.ttf', 'arabic_font': 'NotoSansArabic-Regular.ttf',
                 'font_asset': '<TMP Font Asset name>', 'font_file': '<file inside {data} that holds the font asset>',
                 'pt_size': '<m_PointSize>', 'padding': '<m_AtlasPadding>'},
        'steps': [
            {'name': 'scan', 'enabled': False, 'run': '{py} {scripts}/unity_text.py scan 01_original/{ver}/{data} --report 08_qa/audit/scan.md --game-root "{game}"',
             'note': 'مرة لكل إصدار لعبة'},
            {'name': 'export', 'enabled': False,
             'run': '{py} {scripts}/unity_text.py export 01_original/{ver}/{data} -o 03_translation/incoming/{ver}/strings.csv '
                    '--dump-dir 02_extracted/{ver}/dump --game-root "{game}"',
             'note': 'مرة لكل إصدار؛ بعدها tm_fill إلى 03_translation/tables'},
            {'name': 'fonts_export', 'enabled': False,
             'run': '{py} {scripts}/unity_text.py fonts-export 01_original/{ver}/{data} -o 02_extracted/{ver}/fonts --game-root "{game}"',
             'note': 'مرة لكل إصدار: خطوط اللعبة المضمنة (مصدر لاتيني الدمج)'},
        ] + COMMON_TAIL + [
            {'name': 'inject', 'run': '{py} {scripts}/unity_text.py import 01_original/{ver}/{data} 06_build/text/build.csv '
                                      '--dump-dir 02_extracted/{ver}/dump -o 07_patch/{data} --game-root "{game}"'},
        ] + FONT_STEPS + [
            {'name': 'atlas', 'modes': SHAPING,
             'run': '{py} {scripts}/tmp_sdf_atlas.py build --font 04_fonts/build/merged_pf.ttf --text {table} --column target '
                    '--mode {mode} --size {pt_size} --padding {padding} --out 04_fonts/build/ar_sdf'},
            {'name': 'atlas_seed', 'modes': SHAPING,
             'run': '@seed 01_original/{ver}/{data}/{font_file} 07_patch/{data}/{font_file}',
             'note': 'ينسخ ملف الخط من الأصل فقط إذا الحقن ما عدّله (عشان ما يمسح تعديل النص)'},
            {'name': 'atlas_apply', 'modes': SHAPING,
             'run': '{py} {scripts}/tmp_sdf_atlas.py apply --unity-file 07_patch/{data}/{font_file} --font-asset "{font_asset}" '
                    '--atlas 04_fonts/build/ar_sdf -o 06_build/stage/atlas --write',
             'note': 'يكتب في stage (لا كتابة فوق الملف المقروء) ثم atlas_place'},
            {'name': 'atlas_place', 'modes': SHAPING,
             'run': '@copy 06_build/stage/atlas/{font_file_name} 07_patch/{data}/{font_file}'},
        ],
    },
    'unreal': {
        'vars': {'project': '<Project>', 'locres_rel': '<Project>/Content/Localization/Game/en/Game.locres',
                 'ufont_rel': '<Project>/Content/UI/Fonts/<Font>.ufont', 'latin_font': '02_extracted/{ver}/fonts/<Latin>.ttf',
                 'arabic_font': 'NotoSansArabic-Regular.ttf', 'pak_stem': 'zz_Arabic_P'},
        'steps': [
            {'name': 'roundtrip', 'run': '{py} {scripts}/locres_tool.py roundtrip 02_extracted/{ver}/{locres_rel}',
             'note': 'لازم byte-identical'},
            {'name': 'export', 'enabled': False,
             'run': '{py} {scripts}/locres_tool.py export 02_extracted/{ver}/{locres_rel} -o 03_translation/incoming/{ver}/game.csv',
             'note': 'مرة لكل إصدار؛ بعدها tm_fill إلى 03_translation/tables'},
        ] + COMMON_TAIL + [
            {'name': 'inject', 'run': '{py} {scripts}/locres_tool.py import 02_extracted/{ver}/{locres_rel} 06_build/text/build.csv '
                                      '-o 06_build/stage/{pak_stem}/{locres_rel}'},
        ] + FONT_STEPS + [
            {'name': 'ufont', 'run': '{py} {scripts}/ue_font_swap.py swap 02_extracted/{ver}/{ufont_rel} 04_fonts/build/merged_pf.ttf '
                                     '-o 06_build/stage/{pak_stem}/{ufont_rel}'},
            {'name': 'pak', 'enabled': False, 'run': 'repak pack 06_build/stage/{pak_stem}',
             'note': 'تأكد من repak pack --help (نسخة الـpak ونقطة التحميل = الأصل) ثم فعّل الخطوة'},
            {'name': 'pak_place', 'enabled': False,
             'run': '@copy 06_build/stage/{pak_stem}.pak 07_patch/{project}/Content/Paks/{pak_stem}.pak'},
        ],
    },
    'ue3': {
        'vars': {'int_dir': '<Game>/Localization/INT'},
        'steps': [
            {'name': 'export', 'enabled': False,
             'run': '{py} {scripts}/ue3_int_tool.py export 01_original/{ver}/{int_dir} -o 03_translation/incoming/{ver}/int.csv',
             'note': 'مرة لكل إصدار'},
        ] + COMMON_TAIL + [
            {'name': 'inject', 'run': '{py} {scripts}/ue3_int_tool.py import 01_original/{ver}/{int_dir} 06_build/text/build.csv '
                                      '-o 07_patch/{int_dir}'},
        ],
    },
    'other': {'vars': {}, 'steps': COMMON_TAIL + [
        {'name': 'inject', 'enabled': False, 'run': '<أداة الحقن الخاصة بالمحرك: تقرأ 06_build/text/build.csv وتكتب في 07_patch/>'}]},
}


# ---------------------------------------------------------------- helpers
def out(msg=''):
    print(msg, flush=True)


def die(msg, code=2):
    print('ERROR: ' + msg, file=sys.stderr)
    sys.exit(code)


def now_ts():
    return dt.datetime.now().strftime('%Y%m%d-%H%M%S')


def today():
    return dt.date.today().isoformat()


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def write_text(path, text, overwrite=True):
    if os.path.exists(path) and not overwrite:
        return False
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return True


def write_csv_header(path, cols):
    if os.path.exists(path):
        return
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(cols)


def find_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        p = os.path.join(d, 'project.json')
        if os.path.isfile(p):
            try:
                with open(p, encoding='utf-8') as f:
                    if 'std' in json.load(f):
                        return d
            except (ValueError, OSError):
                pass
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


def load_project(root):
    with open(os.path.join(root, 'project.json'), encoding='utf-8') as f:
        return json.load(f)


def save_project(root, pj):
    with open(os.path.join(root, 'project.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(pj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def need_project(a):
    root = os.path.abspath(a.root) if a.root else find_root()
    if not root or not os.path.isfile(os.path.join(root, 'project.json')):
        die('not inside an L10N-STD project (no project.json up the tree). Use --root or run init.')
    return root, load_project(root)


def relp(root, p):
    return os.path.relpath(os.path.abspath(p), root).replace(os.sep, '/')


def layout_entry(rel):
    best = None
    for e in LAYOUT:
        if rel == e[0] or rel.startswith(e[0] + '/'):
            if best is None or len(e[0]) > len(best[0]):
                best = e
    return best


def owner_of(rel):
    """-> (owner, class) or (None, None)."""
    if rel in ROOT_FILES:
        return ROOT_FILES[rel], 'authored'
    m = re.match(r'00_admin/sessions/([A-Za-z0-9_-]+)\.md$', rel)
    if m:
        return m.group(1), 'authored'
    e = layout_entry(rel)
    if e:
        return e[2], e[1]
    return None, None


def q(s):
    s = str(s)
    if os.name == 'nt':
        return '"%s"' % s if (' ' in s or '&' in s) else s
    return shlex.quote(s)


def read_table(path):
    delim = '\t' if path.lower().endswith('.tsv') else ','
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f, delimiter=delim)
        rows = list(rd)
        return [c.strip() for c in (rd.fieldnames or [])], rows


def table_key(header):
    for ks in KEY_SETS:
        if all(k in header for k in ks):
            return ks
    return None


def walk_files(base, skip_dirs=('.git', '__pycache__')):
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in skip_dirs]
        for fn in fns:
            yield os.path.join(dp, fn)


def make_readonly(p):
    try:
        os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


def make_writable(p):
    try:
        os.chmod(p, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


def write_sums(folder, exclude=('SHA256SUMS', 'ORIGIN.json')):
    lines = []
    for f in sorted(walk_files(folder)):
        r = os.path.relpath(f, folder).replace(os.sep, '/')
        if r in exclude:
            continue
        lines.append('%s  %s' % (sha256(f), r))
    p = os.path.join(folder, 'SHA256SUMS')
    if os.path.exists(p):
        make_writable(p)
    write_text(p, '\n'.join(lines) + ('\n' if lines else ''))
    return len(lines)


def read_sums(folder):
    p = os.path.join(folder, 'SHA256SUMS')
    d = collections.OrderedDict()
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.strip():
                h, r = line.split('  ', 1)
                d[r] = h
    return d


def skill_roots(root=None, extra=()):
    home = os.path.expanduser('~')
    c = list(extra or []) + [os.path.join(home, '.claude', 'skills'), '/mnt/skills',
                             os.path.join(home, '.config', 'opencode', 'skills'), os.path.join(home, '.agents', 'skills')]
    if root:
        c.append(os.path.join(root, '.claude', 'skills'))
    return [d for d in dict.fromkeys(os.path.abspath(x) for x in c) if os.path.isdir(d)]


def find_skills(roots, maxdepth=5):
    """-> list of (name, skill_dir)."""
    res, seen = [], set()
    for r in roots:
        base = r.rstrip(os.sep).count(os.sep)
        for dp, dns, fns in os.walk(r, followlinks=True):
            if dp.count(os.sep) - base >= maxdepth:
                dns[:] = []
            if 'SKILL.md' in fns:
                real = os.path.realpath(dp)
                if real in seen:
                    continue
                seen.add(real)
                name = os.path.basename(dp)
                try:
                    with open(os.path.join(dp, 'SKILL.md'), encoding='utf-8') as f:
                        head = f.read(2000)
                    m = re.search(r'^name:\s*(\S+)', head, re.M)
                    if m:
                        name = m.group(1).strip('"\'')
                except OSError:
                    pass
                res.append((name, dp))
    return res


def installed_scripts(root=None, extra=()):
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isfile(os.path.join(here, 'ar_shape.py')) and '/tools/vendor/' not in here.replace(os.sep, '/'):
        return here
    for name, d in find_skills(skill_roots(root, extra)):
        s = os.path.join(d, 'scripts')
        if name == 'game-arabization' and os.path.isfile(os.path.join(s, 'ar_shape.py')):
            return s
    return None


def resolve_scripts(root, pj):
    p = (pj.get('paths') or {}).get('scripts')
    cands = []
    if p:
        cands.append(p if os.path.isabs(p) else os.path.join(root, p))
    cands.append(os.path.join(root, 'tools', 'vendor', 'game-arabization'))
    s = installed_scripts(root)
    if s:
        cands.append(s)
    for c in cands:
        if os.path.isfile(os.path.join(c, 'ar_shape.py')):
            return os.path.abspath(c)
    return None


def file_std(path):
    try:
        with open(path, encoding='utf-8') as f:
            m = STD_MARK.search(f.read())
        return m.group(1) if m else None
    except OSError:
        return None


# ---------------------------------------------------------------- templates (Arabic documents)
def folder_readme(path, cls, own, contents, never):
    owner_txt = 'كل دور يكتب ملفه فقط (00_admin/sessions/<role>.md)' if own == '*' else '%s — %s' % (own, ROLES.get(own, ''))
    s = '# %s\n\n- **الصنف:** %s — %s\n- **المالك:** %s\n- **يحتوي:** %s\n' % (
        path, CLASSES[cls][0], CLASSES[cls][1], owner_txt, contents)
    if never:
        s += '- **ممنوع:** %s\n' % never
    s += '\n> معيار L10N-STD %s (l10n-std: %s) — تحقق: `python tools/l10n_ws.py check` · المالك: `python tools/l10n_ws.py owner <path> --role <role>`\n' % (STD, STD)
    return s


def status_md(pj):
    g = pj['game']
    return """# {name} — حالة التعريب
> معيار التنظيم: L10N-STD {std} · المحرك: {engine} · إصدار اللعبة: {ver} · يملك الملف: tech

## المرحلة الحالية
- A) الاستطلاع

<!-- AUTO:PROGRESS -->
(يحدث بـ `python tools/l10n_ws.py status --write`)
<!-- /AUTO:PROGRESS -->

## الحقائق المثبتة (كل سطر بدليل: أمر + ناتج، أو لقطة في 08_qa/shots)
- المحرك:
- مكان النص:
- الترميز:
- قرار العرض: (project.json → render، والقرار في 00_admin/DECISIONS.md)
- الخط:

## خط البناء
- كامل: `python tools/l10n_ws.py build` (الخطوات في project.json → pipeline، والمتغيرات في vars)
- السجلات: 06_build/logs/

## المفتوح
- [ ]

## السقوف التقنية الموثقة
-

## آخر تحديث
- {date} — tech — إنشاء المشروع
""".format(name=g['name'], std=STD, engine=g.get('engine', ''), ver=g.get('version', ''), date=today())


def decisions_md():
    return """# سجل القرارات
> سجل إلحاقي: لا يحذف قرار ولا يعدل. للتغيير أضف قرارا جديدا "يلغي D-00X".
> أضف بـ: `python tools/l10n_ws.py decision "القرار" --why "السبب" --evidence 08_qa/shots/...`

## D-001 — اعتماد معيار L10N-STD {std} لتنظيم ملفات المشروع
- التاريخ: {date} · الدور: tech
- السبب: تنظيم واحد متزامن مع skills: game-arabization-workspace وgame-arabization (ومنها دليلا Unity وUnreal)
""".format(std=STD, date=today())


def changelog_md():
    return """# سجل التغييرات
الصيغة: `## vX.Y.Z — YYYY-MM-DD` ثم أضيف / تغير / أصلح.
X = تغطية كاملة أو إصدار لعبة جديد · Y = محتوى جديد مترجم · Z = إصلاحات فقط.

## غير منشور
-
"""


def session_md(role):
    return """# جلسة: {role} — {desc}
> اكتب في مجلداتك فقط. قبل أي كتابة: `python tools/l10n_ws.py owner <path> --role {role}` (0 = مسموح).
> أي تعديل خارج مجلداتك = طلب في الجدول تحت ثم توقف.

## آخر حالة
- {date}: بداية

## ما أنجزت (مع الدليل: أمر + ناتج أو لقطة)
-

## طلبات لأدوار أخرى
| # | إلى | الطلب | الحالة |
|---|---|---|---|

## أسئلة للمستخدم
-
""".format(role=role, desc=ROLES.get(role, ''), date=today())


def readme_md(pj):
    return """# تعريب {name}
مشروع منظم حسب L10N-STD {std} (skill: game-arabization-workspace؛ الأدوات: game-arabization).

ابدأ بقراءة: `STATUS.md` ← `00_admin/DECISIONS.md` ← `03_translation/glossary.csv` ← ملف جلستك في `00_admin/sessions/`.

| أبي... | الأمر |
|---|---|
| أشوف التقدم | `python tools/l10n_ws.py status` |
| أفحص التنظيم | `python tools/l10n_ws.py check` |
| أبني كل شيء من الأصل | `python tools/l10n_ws.py build` |
| أعرف هل المسار لي | `python tools/l10n_ws.py owner <path> --role <role>` |
| آخذ نسخة أصلية من اللعبة | `python tools/l10n_ws.py snapshot --from "<game>" --version <ver> <files>` |
| نسخة أمان قبل تعديل | `python tools/l10n_ws.py backup <files> --step <name>` |
| أسجل قرارا | `python tools/l10n_ws.py decision "..." --why "..."` |
| أسلم المشروع لجهاز/جلسة | `python tools/l10n_ws.py pack` |
| أتأكد إن الأدوات والـskills متزامنة | `python tools/l10n_ws.py sync` |
""".format(name=pj['game']['name'], std=STD)


GITIGNORE = """# L10N-STD {std}: لا ملفات لعبة ولا مخرجات مولدة في git
/01_original/**
/02_extracted/**
/03_translation/incoming/**
/04_fonts/build/**
/05_media/video/out/**
/05_media/textures/out/**
/06_build/**
/07_patch/**
/08_qa/audit/**
/09_release/**
/backups/**
!**/_README.md
__pycache__/
*.pyc
""".format(std=STD)


# ---------------------------------------------------------------- commands
def cmd_init(a):
    root = os.path.abspath(a.dir)
    if os.path.isfile(os.path.join(root, 'project.json')):
        die('already a project (%s). Use check/status.' % root)
    if os.path.isdir(root) and os.listdir(root) and not a.force:
        die('folder not empty: %s (use --force to organize an existing folder; nothing is deleted)' % root)
    slug = a.slug or re.sub(r'[^A-Za-z0-9]+', '', a.game.title()) or 'Game'
    if not re.match(r'^[A-Za-z0-9_-]+$', slug):
        die('--slug must be ASCII letters/digits/_/-')
    roles = [r.strip() for r in a.roles.split(',') if r.strip()]
    bad = [r for r in roles if r not in ROLES]
    if bad:
        die('unknown roles %s (known: %s)' % (bad, ', '.join(ROLES)))
    if 'tech' not in roles:
        roles.insert(0, 'tech')
    eng = a.engine if a.engine in PIPELINES else 'other'
    tpl = PIPELINES[eng]
    pj = collections.OrderedDict([
        ('std', STD), ('created', today()),
        ('game', collections.OrderedDict([('name', a.game), ('slug', slug), ('engine', a.engine or 'other'),
                                          ('engine_version', a.engine_version or ''), ('version', a.game_version),
                                          ('store', a.store or ''), ('notes', '')])),
        ('langs', {'source': a.source_lang, 'target': a.target_lang}),
        ('render', collections.OrderedDict([('mode', 'undecided'), ('harakat', 'undecided'), ('digits', 'western'), ('decision', '')])),
        ('roles', roles),
        ('tables', []),
        ('fonts', []),
        ('vars', dict(tpl['vars'])),
        ('pipeline', [dict(s) for s in tpl['steps']]),
        ('paths', collections.OrderedDict([('game_dir', os.path.abspath(a.game_dir) if a.game_dir else ''), ('scripts', '')])),
        ('releases', []),
    ])
    os.makedirs(root, exist_ok=True)
    for path, cls, own, contents, never in LAYOUT:
        d = os.path.join(root, path)
        os.makedirs(d, exist_ok=True)
        write_text(os.path.join(d, '_README.md'), folder_readme(path, cls, own, contents, never), overwrite=False)
    save_project(root, pj)
    write_text(os.path.join(root, 'STATUS.md'), status_md(pj), overwrite=False)
    write_text(os.path.join(root, 'README.md'), readme_md(pj), overwrite=False)
    write_text(os.path.join(root, '.gitignore'), GITIGNORE, overwrite=False)
    write_text(os.path.join(root, '00_admin', 'DECISIONS.md'), decisions_md(), overwrite=False)
    write_text(os.path.join(root, '00_admin', 'CHANGELOG.md'), changelog_md(), overwrite=False)
    for r in roles:
        write_text(os.path.join(root, '00_admin', 'sessions', r + '.md'), session_md(r), overwrite=False)
    write_csv_header(os.path.join(root, '03_translation', 'glossary.csv'), GLOSSARY_COLS)
    write_csv_header(os.path.join(root, '03_translation', 'puns.csv'), PUNS_COLS)
    write_csv_header(os.path.join(root, '08_qa', 'bugs.csv'), BUGS_COLS)
    me = os.path.abspath(__file__)
    dst = os.path.join(root, 'tools', TOOL)
    if os.path.abspath(dst) != me:
        shutil.copy2(me, dst)
    out('created L10N-STD %s project: %s' % (STD, root))
    out('  game=%s slug=%s engine=%s version=%s roles=%s' % (a.game, slug, a.engine or 'other', a.game_version, ','.join(roles)))
    out('  pipeline template: %s (%d steps) - fill project.json "vars"' % (eng, len(tpl['steps'])))
    if a.vendor:
        a2 = argparse.Namespace(root=root, from_=None, update=True)
        cmd_vendor(a2)
    if a.git:
        if shutil.which('git'):
            subprocess.run(['git', 'init', '-q', root])
            out('  git init done (commit when ready: git add -A && git commit -m "[tech] init")')
        else:
            out('  git not found - skipped')
    out('next: snapshot the files you will modify ->  python tools/%s snapshot --from "<game dir>" --version %s <rel paths>' % (TOOL, a.game_version))


def cmd_check(a):
    root, pj = need_project(a)
    res = []

    def add(level, area, msg):
        res.append((level, area, msg))

    # 1 project.json
    if pj.get('std') != STD:
        add('WARN', 'project', 'project std %s != tool std %s (run sync; migrate per the workspace skill)' % (pj.get('std'), STD))
    for k in ('game', 'langs', 'render', 'roles', 'tables', 'pipeline', 'paths'):
        if k not in pj:
            add('ERROR', 'project', 'project.json missing key "%s"' % k)
    mode = (pj.get('render') or {}).get('mode', 'undecided')
    if mode not in RENDER_MODES:
        add('ERROR', 'project', 'render.mode "%s" not in %s' % (mode, RENDER_MODES))
    unfilled = [k for k, v in (pj.get('vars') or {}).items() if re.search(r'<[^>]+>', str(v))]
    if unfilled:
        add('WARN', 'project', 'vars still placeholders: %s' % ', '.join(unfilled))
    # 2 folders
    for path, cls, own, _, _ in LAYOUT:
        if not os.path.isdir(os.path.join(root, path)):
            add('ERROR' if '/' not in path else 'WARN', 'layout', 'missing folder %s/' % path)
    for f in ('STATUS.md', 'README.md', '00_admin/DECISIONS.md', '03_translation/glossary.csv'):
        if not os.path.isfile(os.path.join(root, f)):
            add('ERROR', 'layout', 'missing %s' % f)
    # 3 root clutter
    allowed = set(TOP) | set(ROOT_FILES) | {'.git', '.claude'}
    for n in sorted(os.listdir(root)):
        if n in allowed or n.startswith('LICENSE'):
            continue
        ext = os.path.splitext(n)[1].lower()
        add('WARN', 'layout', 'stray item at project root: %s -> belongs in %s' % (n, EXT_HOME.get(ext, 'a standard folder')))
    # 4 naming hygiene (authored/evidence/vendor only; originals keep game names)
    nonascii, badname = [], []
    for f in walk_files(root):
        r = relp(root, f)
        own, cls = owner_of(r)
        if cls not in ('authored', 'evidence') or r.endswith('_README.md'):
            continue
        name = os.path.basename(r)
        if re.search(r'[^\x21-\x7e]', r):
            nonascii.append(r)
        stem = os.path.splitext(name)[0]
        if (r.startswith('03_translation/tables/') or r.startswith('04_fonts/src/')) and BAD_NAME.search(stem) \
                and not re.search(r'(?i)(license|ofl)', stem):
            badname.append(r)
    for r in nonascii[:10]:
        add('WARN', 'naming', 'non-ASCII or space in path (many modding tools break): %s' % r)
    if len(nonascii) > 10:
        add('WARN', 'naming', '... %d more non-ASCII paths' % (len(nonascii) - 10))
    for r in badname[:10]:
        add('WARN', 'naming', 'version-ish name (versions live in git/tm, not file names): %s' % r)
    # 5 originals
    od = os.path.join(root, '01_original')
    for ver in sorted(os.listdir(od)) if os.path.isdir(od) else []:
        vd = os.path.join(od, ver)
        if not os.path.isdir(vd):
            continue
        sums = read_sums(vd)
        files = sorted(relp(vd, f) for f in walk_files(vd) if os.path.basename(f) not in ('SHA256SUMS', '_README.md'))
        if sums is None:
            if files:
                add('ERROR', 'original', '01_original/%s has %d files but no SHA256SUMS (use snapshot)' % (ver, len(files)))
            continue
        miss = [r for r in sums if not os.path.isfile(os.path.join(vd, r))]
        extra = [r for r in files if r not in sums]
        for r in miss[:5]:
            add('ERROR', 'original', 'listed in SHA256SUMS but missing: 01_original/%s/%s' % (ver, r))
        for r in extra[:5]:
            add('ERROR', 'original', 'not in SHA256SUMS (added by hand?): 01_original/%s/%s' % (ver, r))
        if a.verify_originals:
            bad = [r for r, h in sums.items() if os.path.isfile(os.path.join(vd, r)) and sha256(os.path.join(vd, r)) != h]
            for r in bad[:10]:
                add('ERROR', 'original', 'ORIGINAL MODIFIED: 01_original/%s/%s' % (ver, r))
            if not bad:
                add('OK', 'original', '01_original/%s: %d files verified' % (ver, len(sums)))
        else:
            add('OK', 'original', '01_original/%s: %d files listed (hash check: --verify-originals)' % (ver, len(sums)))
    # 6 tables
    td = os.path.join(root, '03_translation', 'tables')
    listed = {t.get('file') for t in pj.get('tables', []) if isinstance(t, dict)}
    present = set()
    total_rows = translated = 0
    for f in sorted(walk_files(td)) if os.path.isdir(td) else []:
        r = relp(root, f)
        if r.endswith('_README.md'):
            continue
        if not r.lower().endswith(('.csv', '.tsv')):
            add('WARN', 'tables', 'non-table file in tables/: %s' % r)
            continue
        present.add(r)
        try:
            header, rows = read_table(f)
        except UnicodeDecodeError:
            add('ERROR', 'tables', '%s is not UTF-8' % r)
            continue
        except csv.Error as e:
            add('ERROR', 'tables', '%s: CSV error %s' % (r, e))
            continue
        for c in ('source', 'target'):
            if c not in header:
                add('ERROR', 'tables', '%s: missing column "%s" (contract: key + source + target)' % (r, c))
        ks = table_key(header)
        if not ks:
            add('WARN', 'tables', '%s: no key column (id | namespace,key | file,section,key,occurrence)' % r)
        else:
            seen, dup = set(), 0
            for row in rows:
                k = tuple((row.get(c) or '') for c in ks)
                if k in seen:
                    dup += 1
                seen.add(k)
            if dup:
                add('ERROR', 'tables', '%s: %d duplicate keys %s' % (r, dup, '+'.join(ks)))
        pf = sum(1 for row in rows if PF_RE.search(row.get('target') or ''))
        if pf:
            add('ERROR', 'tables', '%s: %d rows with pre-shaped Arabic (presentation forms) - tables stay logical; shaping is a build step' % (r, pf))
        if 'status' in header:
            badst = collections.Counter((row.get('status') or '').strip().lower() for row in rows)
            unk = {s: n for s, n in badst.items() if s and s not in TABLE_STATUS}
            if unk:
                add('WARN', 'tables', '%s: unknown status values %s (allowed: %s)' % (r, unk, '|'.join(TABLE_STATUS)))
        n = sum(1 for row in rows if (row.get('source') or '').strip())
        t = sum(1 for row in rows if (row.get('source') or '').strip() and (row.get('target') or '').strip())
        total_rows += n
        translated += t
    for r in sorted(listed - present):
        add('ERROR', 'tables', 'project.json lists %s but it does not exist' % r)
    for r in sorted(present - listed):
        add('WARN', 'tables', '%s not registered in project.json "tables" (add file/from/tool/key)' % r)
    if translated and mode == 'undecided':
        add('WARN', 'project', '%d rows translated but render.mode is undecided - do phase C (test_strings) and record it' % translated)
    # 7 glossary
    gp = os.path.join(root, '03_translation', 'glossary.csv')
    if os.path.isfile(gp):
        try:
            header, rows = read_table(gp)
            for c in ('source', 'target'):
                if c not in header:
                    add('ERROR', 'glossary', 'glossary.csv missing column "%s"' % c)
            by = collections.defaultdict(set)
            for row in rows:
                s = (row.get('source') or '').strip().lower()
                if s:
                    by[s].add((row.get('target') or '').strip())
            for s, ts in sorted(by.items()):
                if len(ts) > 1:
                    add('WARN', 'glossary', 'conflict: "%s" -> %s' % (s, ' | '.join(sorted(ts))))
        except UnicodeDecodeError:
            add('ERROR', 'glossary', 'glossary.csv is not UTF-8')
    # 8 fonts need licenses
    fd = os.path.join(root, '04_fonts', 'src')
    if os.path.isdir(fd):
        for dp, _, fns in os.walk(fd):
            lic = [n for n in fns if re.search(r'(?i)(ofl|license|licence|copying)', n)]
            for n in fns:
                if n.lower().endswith(('.ttf', '.otf', '.ttc', '.woff', '.woff2')) and not lic:
                    add('WARN', 'fonts', 'no license file next to %s' % relp(root, os.path.join(dp, n)))
    # 9 sessions
    for r in pj.get('roles', []):
        if not os.path.isfile(os.path.join(root, '00_admin', 'sessions', r + '.md')):
            add('WARN', 'sessions', 'role %s has no 00_admin/sessions/%s.md' % (r, r))
    # 10 STATUS freshness
    sp = os.path.join(root, 'STATUS.md')
    if os.path.isfile(sp):
        newest = 0
        for base in ('03_translation/tables', '03_translation/glossary.csv', '04_fonts/src', '00_admin/DECISIONS.md'):
            p = os.path.join(root, base)
            for f in ([p] if os.path.isfile(p) else (walk_files(p) if os.path.isdir(p) else [])):
                newest = max(newest, os.path.getmtime(f))
        if newest - os.path.getmtime(sp) > 3 * 86400:
            add('WARN', 'status', 'STATUS.md is %d days older than the newest authored change - update it (status --write)'
                % ((newest - os.path.getmtime(sp)) // 86400))
    # 11 decisions numbering
    dp_ = os.path.join(root, '00_admin', 'DECISIONS.md')
    if os.path.isfile(dp_):
        with open(dp_, encoding='utf-8') as f:
            ids = re.findall(r'^## (D-\d{3,})', f.read(), re.M)
        dups = [i for i, n in collections.Counter(ids).items() if n > 1]
        if dups:
            add('ERROR', 'decisions', 'duplicate decision ids %s' % dups)
    # 12 backups / releases naming
    bd = os.path.join(root, 'backups')
    for n in sorted(os.listdir(bd)) if os.path.isdir(bd) else []:
        p = os.path.join(bd, n)
        if os.path.isdir(p):
            if not re.match(r'^pre_[A-Za-z0-9_-]+_\d{8}-\d{6}$', n):
                add('WARN', 'backups', 'backup folder not named pre_<step>_<YYYYmmdd-HHMMSS>: %s' % n)
            elif not os.path.isfile(os.path.join(p, 'SHA256SUMS')):
                add('WARN', 'backups', '%s has no SHA256SUMS' % n)
    rd = os.path.join(root, '09_release')
    for n in sorted(os.listdir(rd)) if os.path.isdir(rd) else []:
        if os.path.isdir(os.path.join(rd, n)) and not re.match(r'^v\d+\.\d+\.\d+$', n):
            add('WARN', 'release', 'release folder not named vX.Y.Z: %s' % n)
    # 13 vendored tools untouched
    vd = os.path.join(root, 'tools', 'vendor', 'game-arabization')
    vj = os.path.join(vd, 'VERSION.json')
    if os.path.isfile(vj):
        with open(vj, encoding='utf-8') as f:
            v = json.load(f)
        edited = [n for n, h in v.get('files', {}).items() if not os.path.isfile(os.path.join(vd, n)) or sha256(os.path.join(vd, n)) != h]
        if edited:
            add('WARN', 'vendor', 'vendored scripts edited/missing locally: %s (edit the skill, then vendor --update)' % ', '.join(edited[:6]))
    elif os.path.isdir(vd) and os.listdir(vd):
        add('WARN', 'vendor', 'tools/vendor/game-arabization has no VERSION.json (use vendor)')
    # 14 project tool copy
    tp = os.path.join(root, 'tools', TOOL)
    if not os.path.isfile(tp):
        add('WARN', 'tools', 'tools/%s missing (re-run init --force or copy it) - the project should carry its own tool' % TOOL)

    if not any(l == 'ERROR' for l, _, _ in res):
        add('OK', 'summary', 'tables: %d files, %d/%d rows translated' % (len(present), translated, total_rows))
    if a.json:
        out(json.dumps([{'level': l, 'area': ar, 'message': m} for l, ar, m in res], ensure_ascii=False, indent=1))
    else:
        order = {'ERROR': 0, 'WARN': 1, 'OK': 2}
        for l, ar, m in sorted(res, key=lambda x: order[x[0]]):
            out('[%-5s] %-9s %s' % (l, ar, m))
        c = collections.Counter(l for l, _, _ in res)
        out('\ncheck: %d ERROR, %d WARN  (L10N-STD %s, %s)' % (c['ERROR'], c['WARN'], STD, root))
    errs = sum(1 for l, _, _ in res if l == 'ERROR')
    warns = sum(1 for l, _, _ in res if l == 'WARN')
    sys.exit(1 if errs or (a.strict and warns) else 0)


def gather_status(root, pj):
    tables = []
    td = os.path.join(root, '03_translation', 'tables')
    for f in sorted(walk_files(td)) if os.path.isdir(td) else []:
        if not f.lower().endswith(('.csv', '.tsv')):
            continue
        try:
            header, rows = read_table(f)
        except (UnicodeDecodeError, csv.Error):
            continue
        st = collections.Counter()
        n = done = 0
        for row in rows:
            if not (row.get('source') or '').strip():
                continue
            n += 1
            t = (row.get('target') or '').strip()
            s = (row.get('status') or '').strip().lower() or ('translated' if t else 'todo')
            st[s] += 1
            if t or s == 'skip':
                done += 1
        tables.append((relp(root, f), n, done, st))
    gl = 0
    gp = os.path.join(root, '03_translation', 'glossary.csv')
    if os.path.isfile(gp):
        try:
            gl = sum(1 for r in read_table(gp)[1] if (r.get('source') or '').strip())
        except (UnicodeDecodeError, csv.Error):
            pass
    bugs = collections.Counter()
    bp = os.path.join(root, '08_qa', 'bugs.csv')
    if os.path.isfile(bp):
        try:
            for r in read_table(bp)[1]:
                bugs[(r.get('status') or 'open').strip().lower() or 'open'] += 1
        except (UnicodeDecodeError, csv.Error):
            pass
    dec = []
    dp_ = os.path.join(root, '00_admin', 'DECISIONS.md')
    if os.path.isfile(dp_):
        with open(dp_, encoding='utf-8') as f:
            dec = re.findall(r'^## (D-\d{3,}) — (.*)$', f.read(), re.M)
    shots = sorted(n for n in os.listdir(os.path.join(root, '08_qa', 'shots'))
                   if n.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))) if os.path.isdir(os.path.join(root, '08_qa', 'shots')) else []
    lb = None
    lbp = os.path.join(root, '06_build', 'logs', 'last_build.json')
    if os.path.isfile(lbp):
        with open(lbp, encoding='utf-8') as f:
            lb = json.load(f)
    return tables, gl, bugs, dec, shots, lb


def cmd_status(a):
    root, pj = need_project(a)
    tables, gl, bugs, dec, shots, lb = gather_status(root, pj)
    g, rn = pj['game'], pj.get('render', {})
    N = sum(t[1] for t in tables)
    D = sum(t[2] for t in tables)
    out('%s | engine %s | game %s | render %s | std %s' % (g['name'], g.get('engine'), g.get('version'), rn.get('mode'), pj.get('std')))
    out('%-48s %7s %7s %6s  %s' % ('table', 'rows', 'done', '%', 'status counts'))
    for r, n, d, st in tables:
        out('%-48s %7d %7d %5.1f%%  %s' % (r, n, d, 100.0 * d / n if n else 0, dict(st)))
    out('%-48s %7d %7d %5.1f%%' % ('TOTAL', N, D, 100.0 * D / N if N else 0))
    out('glossary %d | bugs %s | decisions %d (last %s) | shots %d (last %s) | last build %s'
        % (gl, dict(bugs) or 0, len(dec), dec[-1][0] if dec else '-', len(shots), shots[-1] if shots else '-',
           ('%s %s' % (lb.get('finished'), lb.get('result'))) if lb else '-'))
    if a.write:
        lines = ['**آخر تحديث آلي:** %s' % dt.datetime.now().strftime('%Y-%m-%d %H:%M'), '',
                 '| الجدول | الصفوف | المنجز | النسبة | مراجع | نهائي | تخطي |', '|---|---|---|---|---|---|---|']
        for r, n, d, st in tables:
            lines.append('| `%s` | %d | %d | %.1f%% | %d | %d | %d |' % (r.split('/')[-1], n, d, 100.0 * d / n if n else 0,
                                                                  st.get('reviewed', 0), st.get('final', 0), st.get('skip', 0)))
        lines.append('| **المجموع** | %d | %d | %.1f%% | | | |' % (N, D, 100.0 * D / N if N else 0))
        lines += ['', '- قرار العرض: `%s` · الحركات: `%s` · الأرقام: `%s`' % (rn.get('mode'), rn.get('harakat'), rn.get('digits')),
                  '- المسرد: %d مصطلح · المشاكل: %s · القرارات: %d (آخرها %s)' % (
                      gl, '، '.join('%s %d' % (k, v) for k, v in bugs.items()) or '0', len(dec),
                      ('%s — %s' % dec[-1]) if dec else '-'),
                  '- اللقطات: %d (آخرها `%s`) · آخر بناء: %s' % (len(shots), shots[-1] if shots else '-',
                                                               ('%s — %s' % (lb.get('finished'), lb.get('result'))) if lb else '-')]
        block = '<!-- AUTO:PROGRESS -->\n' + '\n'.join(lines) + '\n<!-- /AUTO:PROGRESS -->'
        sp = os.path.join(root, 'STATUS.md')
        txt = open(sp, encoding='utf-8').read() if os.path.isfile(sp) else ''
        if '<!-- AUTO:PROGRESS -->' in txt and '<!-- /AUTO:PROGRESS -->' in txt:
            txt = re.sub(r'<!-- AUTO:PROGRESS -->.*?<!-- /AUTO:PROGRESS -->', lambda m: block, txt, flags=re.S)
        else:
            txt = txt.rstrip('\n') + '\n\n' + block + '\n'
        write_text(sp, txt)
        out('STATUS.md progress block updated')


def cmd_owner(a):
    root, pj = need_project(a)
    r = relp(root, a.path)
    if r.startswith('..'):
        out('%s: OUTSIDE the project' % a.path)
        sys.exit(3 if a.role else 0)
    own, cls = owner_of(r)
    if own is None:
        out('%s: not a standard location (no owner) - put files in a standard folder' % r)
        sys.exit(3 if a.role else 0)
    out('%s: owner=%s class=%s' % (r, own, cls))
    if a.role:
        if cls == 'original':
            out('DENIED: originals are written only by "snapshot" (role tech)')
            sys.exit(3)
        if own == a.role:
            if cls == 'generated':
                out('ALLOWED (generated: prefer producing it through build)')
            else:
                out('ALLOWED')
            sys.exit(0)
        out('DENIED: %s belongs to role "%s". Write a request in 00_admin/sessions/%s.md and stop.' % (r, own, a.role))
        sys.exit(3)


def expand_paths(base, items):
    files = []
    for it in items:
        pat = it if os.path.isabs(it) else os.path.join(base, it)
        hits = glob.glob(pat, recursive=True) or ([pat] if os.path.exists(pat) else [])
        if not hits:
            die('not found: %s' % it)
        for h in hits:
            if os.path.isdir(h):
                files.extend(walk_files(h))
            else:
                files.append(h)
    return sorted(set(os.path.abspath(f) for f in files))


def cmd_snapshot(a):
    root, pj = need_project(a)
    src = os.path.abspath(a.from_)
    if not os.path.isdir(src):
        die('--from must be the game folder: %s' % src)
    if not re.match(r'^[A-Za-z0-9._+-]+$', a.version):
        die('--version must be ASCII (e.g. 1.0.3 or 1.0.3_steam-12345)')
    if os.path.abspath(root).startswith(src + os.sep):
        die('the project folder is inside the game folder - keep them apart')
    dest = os.path.join(root, '01_original', a.version)
    files = expand_paths(src, a.paths) if a.paths else sorted(walk_files(src))
    added = same = 0
    conflicts = []
    for f in files:
        r = os.path.relpath(f, src)
        if r.startswith('..'):
            die('path outside --from: %s' % f)
        d = os.path.join(dest, r)
        if os.path.exists(d):
            if sha256(d) == sha256(f):
                same += 1
            else:
                conflicts.append(r.replace(os.sep, '/'))
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(f, d)
        make_readonly(d)
        added += 1
    n = write_sums(dest)
    g = pj['game']
    if a.set_current or not g.get('version') or g.get('version') == 'unknown':
        if g.get('version') not in (None, '', 'unknown', a.version):
            out('game.version: %s -> %s (build now reads 01_original/%s)' % (g.get('version'), a.version, a.version))
        g['version'] = a.version
    pj.setdefault('paths', {})['game_dir'] = src
    save_project(root, pj)
    out('snapshot 01_original/%s: +%d new, %d already identical, %d total in SHA256SUMS' % (a.version, added, same, n))
    if conflicts:
        out('CONFLICT: %d files differ from the existing originals (game updated or already patched?):' % len(conflicts))
        for r in conflicts[:20]:
            out('  ' + r)
        out('-> verify the game files (Steam: verify integrity) and snapshot under a NEW --version')
        sys.exit(2)


def cmd_backup(a):
    root, pj = need_project(a)
    if not re.match(r'^[A-Za-z0-9_-]+$', a.step):
        die('--step must be ASCII letters/digits/_/-')
    gd = (pj.get('paths') or {}).get('game_dir') or ''
    files = expand_paths(os.getcwd(), a.files)
    dest = os.path.join(root, 'backups', 'pre_%s_%s' % (a.step, now_ts()))
    entries = []
    for f in files:
        if a.base:
            base = os.path.abspath(a.base)
        elif f.startswith(root + os.sep):
            base = root
        elif gd and f.startswith(os.path.abspath(gd) + os.sep):
            base = os.path.abspath(gd)
        else:
            base = os.path.dirname(f)
        r = os.path.relpath(f, base)
        if r.startswith('..'):
            die('%s is not under --base %s' % (f, base))
        d = os.path.join(dest, r)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(f, d)
        entries.append({'rel': r.replace(os.sep, '/'), 'origin': f, 'sha256': sha256(d)})
    write_text(os.path.join(dest, 'ORIGIN.json'), json.dumps({'step': a.step, 'created': dt.datetime.now().isoformat(timespec='seconds'),
                                                               'files': entries}, ensure_ascii=False, indent=1) + '\n')
    write_sums(dest)
    out('backup %s: %d files' % (relp(root, dest), len(entries)))
    out('restore: python tools/%s restore %s --yes' % (TOOL, relp(root, dest)))
    return dest


def cmd_restore(a):
    root, pj = need_project(a)
    bd = os.path.abspath(a.backup)
    oj = os.path.join(bd, 'ORIGIN.json')
    if not os.path.isfile(oj):
        die('no ORIGIN.json in %s' % bd)
    with open(oj, encoding='utf-8') as f:
        meta = json.load(f)
    plan = []
    for e in meta['files']:
        src = os.path.join(bd, e['rel'])
        if sha256(src) != e['sha256']:
            die('backup corrupted: %s' % e['rel'])
        dst = os.path.join(os.path.abspath(a.to), e['rel']) if a.to else e['origin']
        plan.append((src, dst))
    for s, d in plan:
        out('%s -> %s%s' % (relp(bd, s), d, '' if os.path.exists(d) else ' (new)'))
    if not a.yes:
        out('dry run: %d files. Add --yes to restore (current files are backed up first).' % len(plan))
        return
    existing = [d for _, d in plan if os.path.exists(d)]
    if existing:
        cmd_backup(argparse.Namespace(root=root, files=existing, step='restore', base=None))
    for s, d in plan:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.exists(d):
            make_writable(d)
        shutil.copy2(s, d)
        if sha256(d) != sha256(s):
            die('verify failed after restore: %s' % d)
    out('restored %d files, verified' % len(plan))


def cmd_decision(a):
    root, pj = need_project(a)
    p = os.path.join(root, '00_admin', 'DECISIONS.md')
    txt = open(p, encoding='utf-8').read() if os.path.isfile(p) else decisions_md()
    ids = [int(x) for x in re.findall(r'^## D-(\d{3,})', txt, re.M)]
    if a.supersedes and ('## %s ' % a.supersedes) not in txt:
        die('%s not found in DECISIONS.md' % a.supersedes)
    nid = 'D-%03d' % ((max(ids) if ids else 0) + 1)
    block = '\n## %s — %s\n- التاريخ: %s · الدور: %s\n- السبب: %s\n' % (nid, a.text, today(), a.role, a.why)
    if a.evidence:
        block += '- الدليل: %s\n' % a.evidence
    if a.supersedes:
        block += '- يلغي: %s\n' % a.supersedes
    write_text(p, txt.rstrip('\n') + '\n' + block)
    out('%s recorded' % nid)


def run_builtin(cmd, root):
    parts = shlex.split(cmd[1:], posix=(os.name != 'nt'))
    op = parts[0]
    if op in ('copy', 'seed') and len(parts) == 3:
        s, d = (p if os.path.isabs(p) else os.path.join(root, p) for p in parts[1:])
        if not os.path.isfile(s):
            return 2, 'source not found: %s\n' % parts[1]
        if op == 'seed' and os.path.exists(d):
            return 0, 'seed: %s already exists (kept - an earlier step modified it)\n' % parts[2]
        os.makedirs(os.path.dirname(d) or '.', exist_ok=True)
        if os.path.exists(d):
            make_writable(d)
        shutil.copyfile(s, d)   # content only: originals are read-only, copies must not be
        make_writable(d)
        return 0, '%s %s -> %s\n' % (op, parts[1], parts[2])
    if op == 'mkdir' and len(parts) == 2:
        os.makedirs(os.path.join(root, parts[1]), exist_ok=True)
        return 0, 'mkdir %s\n' % parts[1]
    return 2, 'unknown builtin: %s\n' % cmd


def cmd_build(a):
    root, pj = need_project(a)
    steps = []
    for i, s in enumerate(pj.get('pipeline', [])):
        s = {'name': 'step%d' % (i + 1), 'run': s} if isinstance(s, str) else dict(s)
        steps.append(s)
    if not steps:
        die('project.json "pipeline" is empty')
    mode = (pj.get('render') or {}).get('mode', 'undecided')
    if a.list:
        for i, s in enumerate(steps, 1):
            flags = []
            if s.get('enabled', True) is False:
                flags.append('disabled')
            if s.get('modes'):
                flags.append('modes=' + '/'.join(s['modes']) + ('' if mode in s['modes'] else ' (skipped: mode %s)' % mode))
            out('%2d. %-14s %s%s' % (i, s['name'], s['run'], ('   [' + ', '.join(flags) + ']') if flags else ''))
            if s.get('note'):
                out('      note: %s' % s['note'])
        return
    names = [s['name'] for s in steps]
    sel = list(range(len(steps)))
    if a.from_:
        if a.from_ not in names:
            die('unknown step %s (have: %s)' % (a.from_, ', '.join(names)))
        sel = sel[names.index(a.from_):]
    if a.only:
        bad = [n for n in a.only if n not in names]
        if bad:
            die('unknown steps %s' % bad)
        sel = [i for i in sel if names[i] in a.only]
    scripts = resolve_scripts(root, pj)
    tables = [t['file'] for t in pj.get('tables', []) if isinstance(t, dict) and t.get('main')] or \
             [t['file'] for t in pj.get('tables', []) if isinstance(t, dict)]
    ctx = {'py': q(sys.executable), 'scripts': q(scripts) if scripts else None, 'root': q(root),
           'ver': pj['game'].get('version', ''), 'slug': pj['game'].get('slug', ''),
           'game': (pj.get('paths') or {}).get('game_dir') or None, 'mode': mode,
           'table': tables[0] if tables else None}
    for k, v in (pj.get('vars') or {}).items():
        ctx[k] = str(v)
        ctx[k + '_name'] = os.path.basename(str(v).replace('\\', '/'))   # {var_name} = file name only
    for d in GEN_DIRS + ['02_extracted/%s' % ctx['ver'], '03_translation/incoming/%s' % ctx['ver']]:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    plan = []
    for i in sel:
        s = steps[i]
        explicit = bool(a.only)
        if s.get('enabled', True) is False and not explicit:
            out('- %-14s skipped (disabled)' % s['name'])
            continue
        if s.get('modes') and mode not in s['modes']:
            out('- %-14s skipped (render.mode=%s)' % (s['name'], mode))
            continue
        cmd = s['run']
        for _ in range(3):  # vars may reference other vars
            for k in re.findall(r'\{([A-Za-z_][A-Za-z0-9_]*)\}', cmd):
                if k in ctx and ctx[k] is not None and not re.search(r'<[^>]+>', ctx[k]):
                    cmd = cmd.replace('{%s}' % k, ctx[k])
        missing = sorted(set(re.findall(r'\{([A-Za-z_][A-Za-z0-9_]*)\}', cmd)))
        if missing or re.search(r'<[^>]+>', cmd):
            hint = []
            if 'scripts' in missing:
                hint.append('game-arabization scripts not found (vendor, or paths.scripts)')
            if 'table' in missing:
                hint.append('register a table in project.json "tables"')
            if 'mode' in missing or mode == 'undecided':
                hint.append('render.mode undecided (phase C)')
            die('step "%s" not ready: unresolved %s %s' % (s['name'], missing or 'placeholder <...>', ('- ' + '; '.join(hint)) if hint else '- fill project.json "vars"'))
        if mode == 'undecided' and '{mode}' in s['run']:
            die('step "%s" needs render.mode (phase C decision) - set project.json render.mode' % s['name'])
        plan.append((s['name'], cmd))
    if a.dry_run:
        for n, c in plan:
            out('%-14s %s' % (n, c))
        return
    ts = now_ts()
    logs = os.path.join(root, '06_build', 'logs')
    summary = {'started': dt.datetime.now().isoformat(timespec='seconds'), 'steps': [], 'scripts': scripts, 'std': STD}
    env = dict(os.environ, L10N_ROOT=root, L10N_SCRIPTS=scripts or '', PYTHONIOENCODING='utf-8')
    failed = False
    for k, (n, c) in enumerate(plan, 1):
        lp = os.path.join(logs, '%s_%02d_%s.log' % (ts, k, n))
        t0 = time.time()
        if c.startswith('@'):
            rc, text = run_builtin(c, root)
            write_text(lp, '$ %s\n%s' % (c, text))
        else:
            for m in OUT_ARG.finditer(c):   # tools may not create parent folders of their outputs
                op_ = m.group(1).strip('"\'')
                op_ = op_ if os.path.isabs(op_) else os.path.join(root, op_)
                if op_.startswith(root + os.sep):
                    os.makedirs(os.path.dirname(op_), exist_ok=True)
            with open(lp, 'w', encoding='utf-8') as lf:
                lf.write('$ %s\n' % c)
                lf.flush()
                rc = subprocess.run(c, shell=True, cwd=root, stdout=lf, stderr=subprocess.STDOUT, env=env).returncode
        dur = time.time() - t0
        summary['steps'].append({'name': n, 'rc': rc, 'seconds': round(dur, 1), 'log': relp(root, lp)})
        out('%s %-14s rc=%d %6.1fs  %s' % ('OK  ' if rc == 0 else 'FAIL', n, rc, dur, relp(root, lp)))
        if rc != 0:
            failed = True
            with open(lp, encoding='utf-8', errors='replace') as lf:
                tail = lf.read().splitlines()[-15:]
            for line in tail:
                out('    | ' + line)
            if not a.keep_going:
                break
    summary['finished'] = dt.datetime.now().isoformat(timespec='seconds')
    summary['result'] = 'FAILED' if failed else 'OK'
    write_text(os.path.join(logs, 'last_build.json'), json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    out('build %s (%d steps) - log index 06_build/logs/last_build.json' % (summary['result'], len(summary['steps'])))
    sys.exit(1 if failed else 0)


def cmd_vendor(a):
    root, pj = need_project(a)
    src = os.path.abspath(a.from_) if a.from_ else installed_scripts(root)
    if not src or not os.path.isfile(os.path.join(src, 'ar_shape.py')):
        die('game-arabization scripts not found - pass --from <skill>/scripts')
    dst = os.path.join(root, 'tools', 'vendor', 'game-arabization')
    vj = os.path.join(dst, 'VERSION.json')
    names = sorted(n for n in os.listdir(src) if n.endswith('.py'))
    new = {n: sha256(os.path.join(src, n)) for n in names}
    if os.path.isfile(vj) and not a.update:
        with open(vj, encoding='utf-8') as f:
            old = json.load(f).get('files', {})
        ch = [n for n in new if n in old and old[n] != new[n]]
        ad = [n for n in new if n not in old]
        rm = [n for n in old if n not in new]
        out('vendored vs %s: %d changed, %d new, %d removed%s' % (src, len(ch), len(ad), len(rm),
                                                                   ' -> vendor --update to pin the new tools' if ch or ad or rm else ' (in sync)'))
        for n in ch + ad + rm:
            out('  ' + n)
        return
    os.makedirs(dst, exist_ok=True)
    for n in names:
        d = os.path.join(dst, n)
        if os.path.exists(d):
            make_writable(d)
        shutil.copy2(os.path.join(src, n), d)
    write_text(vj, json.dumps({'source': src, 'date': dt.datetime.now().isoformat(timespec='seconds'), 'std': STD,
                               'files': new}, ensure_ascii=False, indent=1) + '\n')
    pj.setdefault('paths', {})['scripts'] = 'tools/vendor/game-arabization'
    save_project(root, pj)
    out('vendored %d scripts from %s -> tools/vendor/game-arabization (paths.scripts updated)' % (len(names), src))


def cmd_sync(a):
    root = os.path.abspath(a.root) if a.root else find_root()
    problems = []
    out('tool %s  std %s  (%s)' % (TOOL, STD, os.path.abspath(__file__)))
    found = [(n, d) for n, d in find_skills(skill_roots(root, a.skills_dir)) if n in FAMILY]
    for name in FAMILY:
        hits = [d for n, d in found if n == name]
        if not hits:
            out('  %-28s NOT INSTALLED (searched: %s)' % (name, ', '.join(skill_roots(root, a.skills_dir)) or '-'))
            continue
        for d in hits:
            for f in FAMILY[name]:
                p = os.path.join(d, f)
                if not os.path.isfile(p):
                    out('  %-28s %-34s MISSING' % (name, f))
                    problems.append('%s/%s missing' % (name, f))
                    continue
                v = file_std(p)
                ok = v == STD
                out('  %-28s %-34s std %-5s %s' % (name, f, v or '-', 'OK' if ok else 'MISMATCH'))
                if not ok:
                    problems.append('%s/%s std %s' % (name, f, v))
    if root:
        pj = load_project(root)
        v = pj.get('std')
        out('  %-28s %-34s std %-5s %s' % ('project', 'project.json', v, 'OK' if v == STD else 'MISMATCH'))
        if v != STD:
            problems.append('project.json std %s' % v)
        tp = os.path.join(root, 'tools', TOOL)
        if os.path.isfile(tp) and os.path.realpath(tp) != os.path.realpath(__file__):
            m = re.search(r"^STD = '(\d+\.\d+)'", open(tp, encoding='utf-8').read(), re.M)
            same = sha256(tp) == sha256(os.path.abspath(__file__))
            out('  %-28s %-34s std %-5s %s' % ('project', 'tools/' + TOOL, m.group(1) if m else '-',
                                               'OK (identical)' if same else 'DIFFERS from this tool -> copy the newer one into tools/'))
            if not same:
                problems.append('tools/%s differs' % TOOL)
        vj = os.path.join(root, 'tools', 'vendor', 'game-arabization', 'VERSION.json')
        inst = installed_scripts(root, a.skills_dir)
        if os.path.isfile(vj) and inst:
            with open(vj, encoding='utf-8') as f:
                old = json.load(f).get('files', {})
            cur = {n: sha256(os.path.join(inst, n)) for n in os.listdir(inst) if n.endswith('.py')}
            diff = sorted(n for n in set(old) | set(cur) if old.get(n) != cur.get(n))
            out('  %-28s %-34s %s' % ('project', 'tools/vendor/game-arabization',
                                     'OK (same as installed skill)' if not diff else '%d scripts differ from installed skill: %s -> vendor --update after reading the skill changelog' % (len(diff), ', '.join(diff[:6]))))
    if problems:
        out('sync: %d problem(s)' % len(problems))
        sys.exit(1)
    out('sync: OK')


def cmd_pack(a):
    root, pj = need_project(a)
    outp = os.path.abspath(a.out) if a.out else os.path.join(root, 'backups', 'authored_%s_%s.zip' % (pj['game'].get('slug', 'game'), now_ts()))
    n = size = 0
    with zipfile.ZipFile(outp, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(walk_files(root)):
            r = relp(root, f)
            if os.path.abspath(f) == outp:
                continue
            own, cls = owner_of(r)
            if r in ROOT_FILES or cls in ('authored', 'evidence', 'vendor'):
                z.write(f, r)
                n += 1
                size += os.path.getsize(f)
    out('pack %s: %d files, %.1f MB raw (authored + evidence + vendor + root files; no originals/generated/backups)'
        % (relp(root, outp) if outp.startswith(root) else outp, n, size / 1048576.0))


def cmd_clean(a):
    root, pj = need_project(a)
    targets = []
    for path, cls, *_ in LAYOUT:
        if cls != 'generated':
            continue
        if path in NOT_REBUILDABLE and not a.all:   # often produced by external tools (FModel, UABEA...)
            continue
        d = os.path.join(root, path)
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            if n == '_README.md':
                continue
            p = os.path.join(d, n)
            # never descend into a nested non-generated layout entry
            own, c2 = owner_of(relp(root, p))
            if c2 != 'generated':
                continue
            targets.append(p)
    total = 0
    for p in targets:
        if os.path.isdir(p):
            total += sum(os.path.getsize(f) for f in walk_files(p))
        else:
            total += os.path.getsize(p)
    for p in targets:
        out(('delete ' if a.yes else 'would delete ') + relp(root, p))
    if not a.yes:
        out('dry run: %d items, %.1f MB. Add --yes (everything here must come back with "build").%s' % (
            len(targets), total / 1048576.0, '' if a.all else ' 02_extracted and incoming are kept (--all to include).'))
        return

    def onerr(func, path, _):
        make_writable(path)
        func(path)
    for p in targets:
        if os.path.isdir(p):
            shutil.rmtree(p, onerror=onerr)
        else:
            make_writable(p)
            os.remove(p)
    out('cleaned %d items (%.1f MB)' % (len(targets), total / 1048576.0))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', help='project root (default: search up from cwd for project.json)')
    sp = ap.add_subparsers(dest='cmd', required=True)

    p = sp.add_parser('init', help='create a standard project')
    p.add_argument('dir')
    p.add_argument('--game', required=True)
    p.add_argument('--slug')
    p.add_argument('--engine', default='other', help='unity | unreal | ue3 | rpgmaker | godot | idtech | other (pipeline templates: unity, unreal, ue3)')
    p.add_argument('--engine-version')
    p.add_argument('--game-version', default='unknown')
    p.add_argument('--game-dir', help='game install folder (read-only source; stored in paths.game_dir)')
    p.add_argument('--store')
    p.add_argument('--source-lang', default='en')
    p.add_argument('--target-lang', default='ar')
    p.add_argument('--roles', default='tech,translation,operator')
    p.add_argument('--vendor', action='store_true', help='pin game-arabization scripts into tools/vendor')
    p.add_argument('--git', action='store_true')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_init)

    p = sp.add_parser('check', help='validate the project against the standard')
    p.add_argument('--verify-originals', action='store_true')
    p.add_argument('--strict', action='store_true', help='exit 1 on WARN too')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_check)

    p = sp.add_parser('status', help='progress summary')
    p.add_argument('--write', action='store_true', help='update the AUTO:PROGRESS block in STATUS.md')
    p.set_defaults(fn=cmd_status)

    p = sp.add_parser('owner', help='who owns a path; with --role: exit 0 allowed / 3 denied')
    p.add_argument('path')
    p.add_argument('--role')
    p.set_defaults(fn=cmd_owner)

    p = sp.add_parser('snapshot', help='copy pristine game files into 01_original/<version>/ + SHA256SUMS')
    p.add_argument('--from', dest='from_', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--set-current', action='store_true', help='make this the project game.version (game update)')
    p.add_argument('paths', nargs='*', help='relative paths or globs inside --from (default: everything)')
    p.set_defaults(fn=cmd_snapshot)

    p = sp.add_parser('backup', help='copy files to backups/pre_<step>_<ts>/ before changing them')
    p.add_argument('files', nargs='+')
    p.add_argument('--step', required=True)
    p.add_argument('--base')
    p.set_defaults(fn=cmd_backup)

    p = sp.add_parser('restore', help='restore a backup (dry run unless --yes)')
    p.add_argument('backup')
    p.add_argument('--to')
    p.add_argument('--yes', action='store_true')
    p.set_defaults(fn=cmd_restore)

    p = sp.add_parser('decision', help='append D-NNN to 00_admin/DECISIONS.md')
    p.add_argument('text')
    p.add_argument('--why', required=True)
    p.add_argument('--role', default='tech')
    p.add_argument('--supersedes')
    p.add_argument('--evidence')
    p.set_defaults(fn=cmd_decision)

    p = sp.add_parser('build', help='run project.json pipeline (logs in 06_build/logs)')
    p.add_argument('--list', action='store_true')
    p.add_argument('--only', action='append')
    p.add_argument('--from', dest='from_')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--keep-going', action='store_true')
    p.set_defaults(fn=cmd_build)

    p = sp.add_parser('vendor', help='pin game-arabization scripts into tools/vendor/game-arabization')
    p.add_argument('--from', dest='from_')
    p.add_argument('--update', action='store_true')
    p.set_defaults(fn=cmd_vendor)

    p = sp.add_parser('sync', help='check skills, docs, project and vendored tools share the same standard')
    p.add_argument('--skills-dir', action='append', default=[])
    p.set_defaults(fn=cmd_sync)

    p = sp.add_parser('pack', help='zip the irreplaceable files')
    p.add_argument('--out')
    p.set_defaults(fn=cmd_pack)

    p = sp.add_parser('clean', help='empty generated folders (dry run unless --yes)')
    p.add_argument('--yes', action='store_true')
    p.add_argument('--all', action='store_true', help='also 02_extracted and 03_translation/incoming (only if build can re-export them)')
    p.set_defaults(fn=cmd_clean)

    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
