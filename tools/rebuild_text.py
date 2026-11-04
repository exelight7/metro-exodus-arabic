"""Render the current logical CSV without replacing edits from old draft memory.

Requires a workspace produced by recover_project.py. Keeps all non-text assets
from the verified current patch. New characters need a separate font rebuild.
"""
from pathlib import Path
import argparse, csv, hashlib, json, re, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive, LNG, pack_archive
from metro_lng import parse, build
from subtitle_layout import GameRenderer


def render():
    original = (ROOT/'02_extracted/steam_local/patch_04/content/localization/stable_us.lng').read_bytes()
    _, source_pairs = parse(original)
    with (ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(source_pairs): raise ValueError('CSV record count differs from the original.')
    renderer = GameRenderer(); output = []
    for row, (key, source) in zip(rows, source_pairs):
        if row['id'] != key or row['source'] != source: raise ValueError('Stale CSV source or ID: '+key)
        if source.strip() and not row['target'].strip(): raise ValueError('Empty translation: '+key)
        output.append((key, renderer.render(key, row['target'])))
    known = {key for key,_ in output}
    for row in json.loads((ROOT/'03_translation/supplemental_entries.json').read_text(encoding='utf-8')):
        if row['id'] in known: raise ValueError('Duplicate supplemental ID.')
        known.add(row['id']); output.append((row['id'], renderer.render(row['id'], row['target'])))
    current = ROOT/'06_build/stage/content/localization/stable_us.lng'
    chars, _ = parse(current.read_bytes())
    missing = set(''.join(value for _,value in output))-set(chars)
    if missing: raise ValueError('Rebuild font coverage first; missing characters: '+ascii(''.join(sorted(missing))))
    data = build(original, chars, output)
    if list(LNG(data).texts.items()) != output: raise ValueError('LNG roundtrip mismatch.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='New separate patch folder')
    args = parser.parse_args(); destination = args.out.expanduser().absolute()
    if destination.exists() or destination.is_symlink(): parser.error('Output must be new.')
    data = render()
    with tempfile.TemporaryDirectory(prefix='metro-text-', dir=ROOT/'06_build') as temporary:
        replacements = Path(temporary)/'replacements'; replacements.mkdir()
        import shutil
        shutil.copytree(ROOT/'06_build/stage', replacements, dirs_exist_ok=True)
        (replacements/'content/localization/stable_us.lng').write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        report = pack_archive(Archive(ROOT/'01_original/steam_local/patch_04.vfx'), replacements,
                              destination, 'metro_arabic_dev_'+digest[:12]+'.vfs0')
    print(json.dumps(dict(lng_sha256=digest, records=len(LNG(data).texts),
                         live_game_written=False, patch=report), indent=2))


if __name__ == '__main__': main()
