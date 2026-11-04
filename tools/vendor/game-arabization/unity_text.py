#!/usr/bin/env python3
"""
unity_text.py - find, export and re-inject text in Unity games (Mono and IL2CPP) with UnityPy.

  scan    inventory of a game folder: where the text is (TextAssets, MonoBehaviour string
          fields per script, TMP text components, I2 Localization, Unity Localization tables),
          which fonts exist (legacy Font, TMP font assets: schema, glyphs, Arabic coverage)
  export  MonoBehaviour string fields -> CSV (id, script, object, field, source, target)
          TextAssets -> files in --dump-dir (edit JSON/CSV/XML there with format-aware tools)
  import  CSV + edited dump files -> modified copies of the Unity files in -o (same relative
          paths, original compression), then re-reads them and verifies every change
  font-swap  replace the TTF data inside a legacy dynamic Font asset (UI Text / TextMesh)
  fonts-export  save the TTF/OTF bytes of every dynamic Font asset (the game's own fonts,
          e.g. the Latin source font of a TMP asset) -> merge Arabic into them with font_merge.py
  bulk-set  set one field on every MonoBehaviour that has it (dry run unless --write), e.g.
          --field m_isRightToLeft --value true        (TMP RTL on, for ar_shape --mode forms)
          --field m_HorizontalAlignment --value 4 --if-equals 1   (TMP Left -> Right)
          --field m_textAlignment --align-right       (legacy TMP alignment enum, keeps vertical part)
          --field m_enableWordWrapping --value false  (when you wrap yourself with ar_shape --wrap-px)
          --field m_characterSpacing --value 0        (hairline gaps between joined letters)

IL2CPP / missing type trees: pass --game-root <folder with GameAssembly.dll or Managed/>;
UnityPy then generates the MonoBehaviour layouts (needs: pip install TypeTreeGeneratorAPI).

Usage
  unity_text.py scan "C:/Games/X" --report unity_scan.md
  unity_text.py export "C:/Games/X/X_Data" -o strings.csv --dump-dir dump --game-root "C:/Games/X"
  unity_text.py import "C:/Games/X/X_Data" strings_ar.csv --dump-dir dump -o patched_files --game-root "C:/Games/X"
  unity_text.py font-swap "C:/Games/X/X_Data/resources.assets" --font-name Arial --ttf Arabic.ttf -o patched_files
Filters for export: --script-re "Dialog|Item|Quest" --field-re "text|desc|name" --skip-field-re ...
Rows whose source looks like a file name / id / code are skipped by default (--keep-ids to keep).
Needs: pip install UnityPy (tested API: UnityPy 1.25). Work on copies; verify in game.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

try:
    import UnityPy
except ImportError:
    sys.exit('needs UnityPy:  pip install UnityPy')

UNITY_EXT = ('.assets', '.bundle', '.unity3d', '.ab', '.asset', '.resource_bundle')
UNITY_NAMES = re.compile(r'^(globalgamemanagers|resources\.assets|sharedassets\d+\.assets|level\d+|data\.unity3d|'
                         r'unity_builtin_extra|unity default resources)$', re.I)
DEFAULT_SKIP_FIELD = r'(^|\.)(m_Name|guid|GUID|path|Path|url|URL|id|ID|Id|key|Key|tag|Tag|asset|Asset|file|File|' \
                     r'anim|Anim|sound|Sound|sprite|Sprite|icon|Icon|shader|Shader|prefab|Prefab|scene|Scene|Code|code|lang|Lang)\b'
ID_LIKE = re.compile(r'^[\w./\\:#@$-]+$')


def find_files(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for d, _, fs in os.walk(root):
        for f in sorted(fs):
            p = os.path.join(d, f)
            low = f.lower()
            if low.endswith(('.ress', '.resource', '.dll', '.exe', '.json', '.txt', '.mp4', '.webm')):
                continue
            if low.endswith(UNITY_EXT) or UNITY_NAMES.match(low):
                out.append(p)
                continue
            try:
                with open(p, 'rb') as fh:
                    head = fh.read(8)
                if head.startswith((b'UnityFS', b'UnityWeb', b'UnityRaw', b'UnityArc')):
                    out.append(p)
            except OSError:
                pass
    return out


def make_env(path, game_root):
    env = UnityPy.load(path)
    if game_root:
        try:
            from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
            ver = None
            for f in env.files.values():
                ver = getattr(f, 'unity_version', None) or ver
            for o in env.objects:
                ver = getattr(o.assets_file, 'unity_version', None) or ver
                break
            gen = TypeTreeGenerator(str(ver or '2020.3.0f1'))
            gen.load_local_game(game_root)
            env.typetree_generator = gen
        except Exception as e:
            print('note: typetree generator unavailable (%s)' % e, file=sys.stderr)
    return env


def script_name(obj):
    try:
        mb = obj.read(check_read=False)
        ms = mb.m_Script.read()
        return (ms.m_Namespace + '.' if getattr(ms, 'm_Namespace', '') else '') + ms.m_ClassName
    except Exception:
        return '?'


def walk_strings(node, path=''):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, '%s.%s' % (path, k) if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, '%s[%d]' % (path, i))
    elif isinstance(node, str):
        yield path, node


def set_path(tree, path, value):
    parts = re.findall(r'[^.\[\]]+|\[\d+\]', path)
    cur = tree
    for p in parts[:-1]:
        cur = cur[int(p[1:-1])] if p.startswith('[') else cur[p]
    last = parts[-1]
    if last.startswith('['):
        cur[int(last[1:-1])] = value
    else:
        cur[last] = value


def get_path(tree, path):
    cur = tree
    for p in re.findall(r'[^.\[\]]+|\[\d+\]', path):
        cur = cur[int(p[1:-1])] if p.startswith('[') else cur[p]
    return cur


def looks_like_text(s, min_letters, keep_ids):
    letters = sum(1 for c in s if c.isalpha())
    if letters < min_letters:
        return False
    if not keep_ids and ' ' not in s and ID_LIKE.match(s) and (
            '_' in s or '/' in s or '.' in s or re.search(r'[a-z][A-Z]', s) or s.isupper() and len(s) > 3):
        return False
    return True


def rel(path, base):
    return os.path.relpath(path, base) if os.path.isdir(base) else os.path.basename(path)


# ------------------------------------------------------------------------------------------ scan
def cmd_scan(a):
    files = find_files(a.path)
    lines = ['# Unity scan: %s' % a.path, '', '%d Unity files' % len(files), '']
    scripts, textassets, fonts, tmp_fonts, comps, i2, loc = {}, [], [], [], 0, [], []
    for p in files:
        try:
            env = make_env(p, a.game_root)
        except Exception as e:
            lines.append('- cannot load %s: %s' % (rel(p, a.path), e))
            continue
        for obj in env.objects:
            t = obj.type.name
            try:
                if t == 'TextAsset':
                    d = obj.read()
                    s = d.m_Script if isinstance(d.m_Script, str) else ''
                    textassets.append((rel(p, a.path), d.m_Name, len(s), s[:60].replace('\n', ' ')))
                elif t == 'Font':
                    d = obj.read()
                    fonts.append((rel(p, a.path), d.m_Name, len(d.m_FontData or [])))
                elif t == 'MonoBehaviour':
                    sn = script_name(obj)
                    try:
                        tree = obj.read_typetree()
                    except Exception:
                        scripts.setdefault(sn, [0, 0, 'no typetree'])[0] += 1
                        continue
                    n_str = sum(1 for _, s in walk_strings(tree) if looks_like_text(s, 2, False))
                    rec = scripts.setdefault(sn, [0, 0, ''])
                    rec[0] += 1
                    rec[1] += n_str
                    if 'm_GlyphTable' in tree or 'm_glyphInfoList' in tree:
                        modern = 'm_GlyphTable' in tree
                        chars = tree.get('m_CharacterTable') if modern else tree.get('m_glyphInfoList')
                        cps = [c.get('m_Unicode', c.get('id', 0)) for c in chars or []]
                        n_ar = sum(1 for c in cps if 0x600 <= c <= 0x6FF or 0xFE70 <= c <= 0xFEFF)
                        tmp_fonts.append((rel(p, a.path), tree.get('m_Name'), 'modern' if modern else 'legacy',
                                          len(cps), n_ar, tree.get('m_AtlasPopulationMode', '-'),
                                          tree.get('m_AtlasWidth', '?'), tree.get('m_AtlasHeight', '?')))
                    if 'm_text' in tree and isinstance(tree.get('m_text'), str):
                        comps += 1
                    if 'mSource' in tree or 'mTerms' in tree or 'I2' in sn or 'LanguageSource' in sn:
                        i2.append((rel(p, a.path), sn, tree.get('m_Name')))
                    if 'm_TableData' in tree and 'm_SharedData' in tree:
                        loc.append((rel(p, a.path), tree.get('m_Name'), len(tree.get('m_TableData') or [])))
            except Exception:
                continue
    lines += ['## Localization systems']
    lines += ['- I2 Localization: %s (built-in RTL fixer: try an Arabic language with code `ar`)' % ', '.join(
        '%s/%s' % (f, n) for f, _, n in i2[:5])] if i2 else ['- I2 Localization: none found']
    lines += ['- Unity Localization StringTables: %d (%s)' % (len(loc), ', '.join(n for _, n, _ in loc[:8]))] if loc \
        else ['- Unity Localization StringTables: none found']
    lines += ['', '## TextMeshPro font assets (%d)' % len(tmp_fonts)]
    for f, n, sch, nc, nar, pop, w, h in tmp_fonts:
        lines.append('- `%s` in %s: %s schema, %d chars (%d Arabic), atlas %sx%s, population mode %s' %
                     (n, f, sch, nc, nar, w, h, pop))
    lines += ['', '## Legacy Font assets (%d)' % len(fonts)]
    lines += ['- `%s` in %s: %s bytes of font data%s' % (n, f, sz, ' (dynamic: TTF inside -> font-swap)' if sz else '')
              for f, n, sz in fonts]
    lines += ['', '## Text components with m_text (TMP/UI): %d' % comps]
    lines += ['', '## MonoBehaviour scripts with text-like strings (top 40)']
    for sn, (cnt, nstr, note) in sorted(scripts.items(), key=lambda x: -x[1][1])[:40]:
        lines.append('- %s: %d objects, %d text-like strings %s' % (sn, cnt, nstr, note))
    lines += ['', '## TextAssets (%d, largest first)' % len(textassets)]
    for f, n, sz, head in sorted(textassets, key=lambda x: -x[2])[:40]:
        lines.append('- `%s` in %s: %d chars - %s' % (n, f, sz, head))
    text = '\n'.join(lines) + '\n'
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            f.write(text)
        print('report: %s' % a.report)
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------------------- export
def cmd_export(a):
    files = find_files(a.path)
    inc = re.compile(a.field_re) if a.field_re else None
    skip = re.compile(a.skip_field_re) if a.skip_field_re else None
    sre = re.compile(a.script_re) if a.script_re else None
    rows, n_ta = [], 0
    for p in files:
        rp = rel(p, a.path)
        env = make_env(p, a.game_root)
        for obj in env.objects:
            t = obj.type.name
            oid = '%s|%s|%d' % (rp, obj.assets_file.name, obj.path_id)
            if t == 'TextAsset' and a.dump_dir:
                d = obj.read()
                s = d.m_Script
                raw = s.encode('utf-8', 'surrogateescape') if isinstance(s, str) else bytes(s)
                name = re.sub(r'[^\w.-]', '_', d.m_Name) or 'textasset'
                ext = '' if '.' in name else '.txt'
                out = os.path.join(a.dump_dir, rp.replace(os.sep, '__'), '%d_%s%s' % (obj.path_id, name, ext))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, 'wb') as f:
                    f.write(raw)
                with open(out + '.sha256', 'w') as f:
                    f.write(hashlib.sha256(raw).hexdigest() + ' ' + oid)
                n_ta += 1
            elif t == 'MonoBehaviour':
                sn = script_name(obj)
                if sre and not sre.search(sn):
                    continue
                try:
                    tree = obj.read_typetree()
                except Exception:
                    continue
                oname = tree.get('m_Name', '')
                for path, s in walk_strings(tree):
                    if skip and skip.search(path) and not (inc and inc.search(path)):
                        continue
                    if inc and not inc.search(path):
                        continue
                    if not looks_like_text(s, a.min_letters, a.keep_ids):
                        continue
                    rows.append({'id': '%s|%s' % (oid, path), 'script': sn, 'object': oname, 'field': path,
                                 'source': s, 'target': ''})
    with open(a.output, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'script', 'object', 'field', 'source', 'target'])
        w.writeheader()
        w.writerows(rows)
    print('exported %d MonoBehaviour strings -> %s%s' % (len(rows), a.output,
          (', %d TextAssets -> %s' % (n_ta, a.dump_dir)) if a.dump_dir else ''))
    return 0


# ---------------------------------------------------------------------------------------- import
def cmd_import(a):
    changes = {}          # rel file -> {(cab, pathid): {field: text}}
    if a.csv:
        with open(a.csv, encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                t = r.get(a.target_col, '')
                if not t:
                    continue
                rp, cab, pid, field = r['id'].split('|', 3)
                changes.setdefault(rp, {}).setdefault((cab, int(pid)), {})[field] = t
    ta_changes = {}       # rel file -> {(cab, pathid): bytes}
    if a.dump_dir and os.path.isdir(a.dump_dir):
        for d, _, fs in os.walk(a.dump_dir):
            for fn in fs:
                if fn.endswith('.sha256'):
                    continue
                p = os.path.join(d, fn)
                if not os.path.isfile(p + '.sha256'):
                    continue
                h0, oid = open(p + '.sha256').read().split(' ', 1)
                raw = open(p, 'rb').read()
                if hashlib.sha256(raw).hexdigest() == h0:
                    continue
                rp, cab, pid = oid.strip().split('|')
                ta_changes.setdefault(rp, {})[(cab, int(pid))] = raw
    todo = sorted(set(changes) | set(ta_changes))
    if not todo:
        sys.exit('nothing to import (empty target column and no edited dump files)')
    total = bad = 0
    base = a.path if os.path.isdir(a.path) else os.path.dirname(a.path)
    for rp in todo:
        src = os.path.join(base, rp) if os.path.isdir(a.path) else a.path
        env = make_env(src, a.game_root)
        want = changes.get(rp, {})
        want_ta = ta_changes.get(rp, {})
        for obj in env.objects:
            key = (obj.assets_file.name, obj.path_id)
            if key in want and obj.type.name == 'MonoBehaviour':
                tree = obj.read_typetree()
                for field, text in want[key].items():
                    set_path(tree, field, text)
                    total += 1
                obj.save_typetree(tree)
            elif key in want_ta and obj.type.name == 'TextAsset':
                d = obj.read()
                d.m_Script = want_ta[key].decode('utf-8', 'surrogateescape')
                d.save()
                total += 1
        dst = os.path.join(a.output, rp)
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        root_file = list(env.files.values())[0]
        with open(dst, 'wb') as f:
            f.write(root_file.save(packer=a.packer))
        # verify by reloading the written file
        env2 = make_env(dst, a.game_root)
        for obj in env2.objects:
            key = (obj.assets_file.name, obj.path_id)
            if key in want and obj.type.name == 'MonoBehaviour':
                tree = obj.read_typetree()
                for field, text in want[key].items():
                    if get_path(tree, field) != text:
                        bad += 1
            elif key in want_ta and obj.type.name == 'TextAsset':
                s = obj.read().m_Script
                if (s.encode('utf-8', 'surrogateescape') if isinstance(s, str) else bytes(s)) != want_ta[key]:
                    bad += 1
        print('  %s -> %s' % (rp, dst))
    print('imported %d values into %d files, verify mismatches: %d' % (total, len(todo), bad))
    return 1 if bad else 0


# -------------------------------------------------------------------------------------- font swap
def cmd_font_swap(a):
    env = make_env(a.path, a.game_root)
    data = open(a.ttf, 'rb').read()
    n = 0
    for obj in env.objects:
        if obj.type.name != 'Font':
            continue
        tree = obj.read_typetree()
        if tree.get('m_Name') != a.font_name:
            continue
        old = tree.get('m_FontData')
        if not old:
            print('Font %s has no embedded data (bitmap/OS font) - cannot swap' % a.font_name)
            continue
        tree['m_FontData'] = list(data) if isinstance(old, list) else data
        obj.save_typetree(tree)
        n += 1
    if not n:
        sys.exit('no dynamic Font named %r found' % a.font_name)
    dst = os.path.join(a.output, os.path.basename(a.path))
    os.makedirs(a.output, exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(list(env.files.values())[0].save(packer=a.packer))
    print('swapped %d Font asset(s) -> %s' % (n, dst))
    return 0


def cmd_fonts_export(a):
    os.makedirs(a.output, exist_ok=True)
    n = 0
    for p in find_files(a.path):
        env = make_env(p, a.game_root)
        for obj in env.objects:
            if obj.type.name != 'Font':
                continue
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            data = tree.get('m_FontData')
            if not data:
                continue
            raw = bytes(data) if isinstance(data, list) else data
            ext = '.otf' if raw[:4] == b'OTTO' else '.ttf'
            name = re.sub(r'[^\w.-]', '_', tree.get('m_Name') or 'font')
            out = os.path.join(a.output, '%s_%d%s' % (name, obj.path_id, ext))
            with open(out, 'wb') as f:
                f.write(raw)
            n += 1
            print('  %s (%d bytes) from %s' % (out, len(raw), rel(p, a.path)))
    print('exported %d fonts -> %s' % (n, a.output))
    return 0


def cmd_bulk_set(a):
    val = json.loads(a.value) if a.value is not None else None
    cond = json.loads(a.if_equals) if a.if_equals is not None else None
    sre = re.compile(a.script_re) if a.script_re else None
    total = files_changed = 0
    for p in find_files(a.path):
        env = make_env(p, a.game_root)
        changed = 0
        for obj in env.objects:
            if obj.type.name != 'MonoBehaviour':
                continue
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            if a.field not in tree or (a.where_field and a.where_field not in tree):
                continue
            if sre and not sre.search(script_name(obj)):
                continue
            cur = tree[a.field]
            if a.align_right:
                if not isinstance(cur, int) or (cur & 0xFF) not in (1, 8, 16):   # Left / Justified / Flush
                    continue
                new = (cur & ~0xFF) | 4
            else:
                if cond is not None and cur != cond:
                    continue
                if cur == val:
                    continue
                new = type(cur)(val) if isinstance(cur, (bool, int, float)) and not isinstance(val, str) else val
            tree[a.field] = new
            if a.write:
                obj.save_typetree(tree)
            changed += 1
        if changed:
            total += changed
            files_changed += 1
            print('  %s: %d objects' % (rel(p, a.path), changed))
            if a.write:
                dst = os.path.join(a.output, rel(p, a.path))
                os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
                with open(dst, 'wb') as f:
                    f.write(list(env.files.values())[0].save(packer=a.packer))
    print('%s %d objects in %d files%s' % ('changed' if a.write else 'would change', total, files_changed,
                                           '' if a.write else ' (dry run - add --write -o DIR)'))
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Unity text scan / export / import / font swap.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('scan', 'export', 'import', 'font-swap', 'fonts-export', 'bulk-set'):
        s = sub.add_parser(name)
        s.add_argument('path', help='game folder, *_Data folder or one Unity file')
        s.add_argument('--game-root', help='folder with GameAssembly.dll or *_Data/Managed (type trees)')
        if name == 'scan':
            s.add_argument('--report')
        if name == 'export':
            s.add_argument('-o', '--output', required=True)
            s.add_argument('--dump-dir')
            s.add_argument('--script-re')
            s.add_argument('--field-re')
            s.add_argument('--skip-field-re', default=DEFAULT_SKIP_FIELD)
            s.add_argument('--min-letters', type=int, default=2)
            s.add_argument('--keep-ids', action='store_true')
        if name == 'import':
            s.add_argument('csv', nargs='?')
            s.add_argument('--dump-dir')
            s.add_argument('-o', '--output', required=True)
            s.add_argument('--target-col', default='target')
            s.add_argument('--packer', default='original', help='original | lz4 | none')
        if name == 'fonts-export':
            s.add_argument('-o', '--output', required=True)
        if name == 'bulk-set':
            s.add_argument('--field', required=True)
            s.add_argument('--value', help='JSON value: true, 4, 0.0, "text"')
            s.add_argument('--if-equals', help='only change when the current value equals this JSON value')
            s.add_argument('--align-right', action='store_true', help='TMP alignment enum: Left/Justified -> Right')
            s.add_argument('--where-field', default='m_text', help='only objects that also have this field')
            s.add_argument('--script-re')
            s.add_argument('--write', action='store_true')
            s.add_argument('-o', '--output')
            s.add_argument('--packer', default='original')
        if name == 'font-swap':
            s.add_argument('--font-name', required=True)
            s.add_argument('--ttf', required=True)
            s.add_argument('-o', '--output', required=True)
            s.add_argument('--packer', default='original')
    a = ap.parse_args()
    if getattr(a, 'packer', None) == 'none':
        a.packer = None
    if a.cmd == 'bulk-set' and a.write and not a.output:
        ap.error('--write needs -o DIR')
    if a.cmd == 'bulk-set' and a.value is None and not a.align_right:
        ap.error('give --value or --align-right')
    return {'scan': cmd_scan, 'export': cmd_export, 'import': cmd_import, 'font-swap': cmd_font_swap,
            'fonts-export': cmd_fonts_export, 'bulk-set': cmd_bulk_set}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
