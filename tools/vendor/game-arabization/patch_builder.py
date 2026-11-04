#!/usr/bin/env python3
"""
patch_builder.py - turn "original game folder" vs "my modified copy" into a safe,
distributable Arabic patch with version check, automatic backup and uninstall.

  build      compare ORIGINAL and MODIFIED folders -> PATCH folder with:
               files/        new or changed files (only those)
               manifest.json sha256 of each original (to refuse a different game version)
                             and of each patched file (to verify the install)
               install.py / uninstall.py      (any OS with Python)
               install.ps1 / uninstall.ps1   (Windows, no Python needed)
               README_AR.txt
  check      verify a game folder against a manifest (which files are original / patched / other)

Usage
  patch_builder.py build --original "C:/Games/X (clean copy)" --modified ./X_ar --out ./X_Arabic_Patch --name "تعريب X" --version 1.0
  patch_builder.py check --game "C:/Games/X" --manifest X_Arabic_Patch/manifest.json
Notes
  * Build against a CLEAN copy of the game (Steam: verify integrity first).
  * Changed archives are copied whole. If they contain the publisher's content and you must not
    redistribute them, ship binary diffs instead (e.g. xdelta3) - see references/qa-release.md.
  * Never include save files, executables you did not need to change, or the whole game.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

INSTALL_PY = r'''#!/usr/bin/env python3
# Installs the patch next to this script into GAME_DIR. Usage: python install.py "GAME_DIR" [--force]
import hashlib, json, os, shutil, sys
here = os.path.dirname(os.path.abspath(__file__))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()
if len(sys.argv) < 2:
    sys.exit('usage: python install.py "GAME_DIR" [--force]')
game, force = sys.argv[1], '--force' in sys.argv
m = json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8'))
bad = []
for rel, e in m['files'].items():
    p = os.path.join(game, rel)
    if e['original'] and os.path.isfile(p) and sha(p) not in (e['original'], e['patched']):
        bad.append(rel)
    if e['original'] and not os.path.isfile(p):
        bad.append(rel + ' (missing)')
if bad and not force:
    sys.exit('game version differs from the one this patch was made for:\n  ' + '\n  '.join(bad[:20]) +
             '\nupdate the patch or use --force at your own risk')
bk = os.path.join(game, '_arabic_patch_backup')
for rel, e in m['files'].items():
    dst = os.path.join(game, rel)
    if os.path.isfile(dst) and not os.path.isfile(os.path.join(bk, rel)) and e['original']:
        os.makedirs(os.path.dirname(os.path.join(bk, rel)), exist_ok=True)
        shutil.copy2(dst, os.path.join(bk, rel))
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    shutil.copy2(os.path.join(here, 'files', rel), dst)
    if sha(dst) != e['patched']:
        sys.exit('verify failed: ' + rel)
print('installed %d files, backup in %s' % (len(m['files']), bk))
'''

UNINSTALL_PY = r'''#!/usr/bin/env python3
# Restores the original files from the backup. Usage: python uninstall.py "GAME_DIR"
import json, os, shutil, sys
here = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    sys.exit('usage: python uninstall.py "GAME_DIR"')
game = sys.argv[1]
m = json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8'))
bk = os.path.join(game, '_arabic_patch_backup')
n = 0
for rel, e in m['files'].items():
    dst, src = os.path.join(game, rel), os.path.join(bk, rel)
    if e['original'] and os.path.isfile(src):
        shutil.copy2(src, dst); n += 1
    elif not e['original'] and os.path.isfile(dst):
        os.remove(dst); n += 1
print('restored/removed %d files. You can delete %s' % (n, bk))
'''

INSTALL_PS1 = r'''# Install: right-click > Run with PowerShell, or:  powershell -ExecutionPolicy Bypass -File install.ps1 "C:\Path\To\Game"
param([Parameter(Mandatory=$true)][string]$Game, [switch]$Force)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -Raw -Encoding UTF8 (Join-Path $here 'manifest.json') | ConvertFrom-Json
$bad = @()
foreach ($p in $m.files.PSObject.Properties) {
  $rel = $p.Name; $e = $p.Value; $dst = Join-Path $Game $rel
  if ($e.original) {
    if (-not (Test-Path -LiteralPath $dst)) { $bad += "$rel (missing)"; continue }
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash.ToLower()
    if ($h -ne $e.original -and $h -ne $e.patched) { $bad += $rel }
  }
}
if ($bad.Count -gt 0 -and -not $Force) { Write-Host "Game version differs:"; $bad | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }; exit 1 }
$bk = Join-Path $Game '_arabic_patch_backup'
foreach ($p in $m.files.PSObject.Properties) {
  $rel = $p.Name; $e = $p.Value; $dst = Join-Path $Game $rel; $b = Join-Path $bk $rel
  if ($e.original -and (Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $b)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $b) | Out-Null
    Copy-Item -LiteralPath $dst -Destination $b
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
  Copy-Item -LiteralPath (Join-Path (Join-Path $here 'files') $rel) -Destination $dst -Force
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash.ToLower() -ne $e.patched) { Write-Host "verify failed: $rel"; exit 1 }
}
Write-Host "Installed. Backup: $bk"
'''

UNINSTALL_PS1 = r'''# Uninstall:  powershell -ExecutionPolicy Bypass -File uninstall.ps1 "C:\Path\To\Game"
param([Parameter(Mandatory=$true)][string]$Game)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -Raw -Encoding UTF8 (Join-Path $here 'manifest.json') | ConvertFrom-Json
$bk = Join-Path $Game '_arabic_patch_backup'
foreach ($p in $m.files.PSObject.Properties) {
  $rel = $p.Name; $e = $p.Value; $dst = Join-Path $Game $rel; $b = Join-Path $bk $rel
  if ($e.original -and (Test-Path -LiteralPath $b)) { Copy-Item -LiteralPath $b -Destination $dst -Force }
  elseif (-not $e.original -and (Test-Path -LiteralPath $dst)) { Remove-Item -LiteralPath $dst }
}
Write-Host "Restored. You can delete $bk"
'''


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def walk(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            yield os.path.relpath(p, root).replace(os.sep, '/'), p


def build(a):
    orig = dict(walk(a.original))
    files = {}
    if os.path.exists(a.out):
        sys.exit('output exists: %s' % a.out)
    for rel, p in walk(a.modified):
        if rel.startswith('_arabic_patch_backup/'):
            continue
        new_h = sha(p)
        o = orig.get(rel)
        old_h = sha(o) if o else None
        if old_h == new_h:
            continue
        dst = os.path.join(a.out, 'files', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        files[rel] = {'original': old_h, 'patched': new_h, 'size': os.path.getsize(p)}
    if not files:
        sys.exit('no differences found')
    man = {'name': a.name, 'version': a.version, 'files': files}
    with open(os.path.join(a.out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    for fn, body in (('install.py', INSTALL_PY), ('uninstall.py', UNINSTALL_PY),
                     ('install.ps1', INSTALL_PS1), ('uninstall.ps1', UNINSTALL_PS1)):
        with open(os.path.join(a.out, fn), 'w', encoding='utf-8-sig' if fn.endswith('.ps1') else 'utf-8',
                  newline='\r\n' if fn.endswith('.ps1') else '\n') as f:
            f.write(body)
    with open(os.path.join(a.out, 'README_AR.txt'), 'w', encoding='utf-8-sig') as f:
        f.write('%s - الإصدار %s\n\nالتثبيت (ويندوز): انقر بالزر الأيمن على install.ps1 > Run with PowerShell،\n'
                'أو: powershell -ExecutionPolicy Bypass -File install.ps1 "مسار اللعبة"\n'
                'بايثون: python install.py "مسار اللعبة"\n\n'
                'الباتش يتحقق من نسخة اللعبة، ويأخذ نسخة احتياطية في _arabic_patch_backup داخل مجلد اللعبة.\n'
                'الإزالة: uninstall.ps1 أو uninstall.py بنفس الطريقة، أو "التحقق من سلامة الملفات" في Steam.\n'
                'تحديث اللعبة قد يمسح التعريب: أعد التثبيت، وإذا رفض بسبب اختلاف النسخة انتظر تحديث الباتش.\n'
                % (a.name, a.version))
    new = sum(1 for e in files.values() if not e['original'])
    print('patch: %s  (%d changed, %d new files, %.1f MB)' % (a.out, len(files) - new, new,
                                                            sum(e['size'] for e in files.values()) / 1e6))
    big = [r for r, e in files.items() if e['size'] > 50e6]
    if big:
        print('note: large files copied whole (%s) - consider binary diffs (references/qa-release.md)' % ', '.join(big[:3]))


def check(a):
    m = json.load(open(a.manifest, encoding='utf-8'))
    counts = {'original': 0, 'patched': 0, 'other': 0, 'missing': 0}
    for rel, e in m['files'].items():
        p = os.path.join(a.game, rel)
        if not os.path.isfile(p):
            st = 'missing' if e['original'] else 'original'
        else:
            h = sha(p)
            st = 'patched' if h == e['patched'] else ('original' if h == e['original'] else 'other')
        counts[st] += 1
        if st in ('other', 'missing'):
            print('  %-8s %s' % (st, rel))
    print('files: %s' % counts)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Build / check an Arabic patch with backup and uninstall.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--original', required=True)
    b.add_argument('--modified', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--name', default='Arabic patch')
    b.add_argument('--version', default='1.0')
    c = sub.add_parser('check')
    c.add_argument('--game', required=True)
    c.add_argument('--manifest', required=True)
    a = ap.parse_args()
    build(a) if a.cmd == 'build' else check(a)


if __name__ == '__main__':
    main()
