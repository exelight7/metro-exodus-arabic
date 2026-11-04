"""Recover a complete editable workspace from owned, hash-matched game files.

No game path is written. The destination must be new and outside the game/source.
Only the installer differences, licensed sources and local original resources are
used. The game executable is checked/reversed in memory and is never distributed.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, struct, sys, tempfile, zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/foura-dialogue/scripts'))
from foura_dialogue import Archive, FormatError, relative_name as safe_relative


def sha(data):
    return hashlib.sha256(data).hexdigest()


def installer_location():
    # Public source checkout and private authoring workspace share this command.
    for code, resources in [(ROOT/'installer/core.py', ROOT/'installer/resources'),
                            (ROOT/'tools/installer/core.py', ROOT/'06_build/installer_resources')]:
        if code.is_file() and (resources/'profile.json').is_file():
            spec = importlib.util.spec_from_file_location('recovery_installer_core', code)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module, resources
    raise ValueError('Installer resources are missing; use the full project source release.')


def recover(game, destination):
    import bsdiff4
    game = Path(game).expanduser().resolve(strict=True)
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('The destination must not already exist.')
    parent = destination.parent.resolve(strict=True)
    destination = parent / destination.name
    if destination.is_relative_to(game) or destination.is_relative_to(ROOT):
        raise ValueError('Choose a destination outside the game and source checkout.')
    core, resources = installer_location()
    installer = core.Installer(resources)
    try:
        installer.inspect(game)  # read-only: exact original or exact current patch
        original_index, original_exe = installer.originals(game)
        p = installer.profile
        base = [core.read_archive(game, item) for item in p['base_assets']]
        payload = bsdiff4.patch(b''.join(base), installer.resource('payload.bsdiff'))
        patched_index = bsdiff4.patch(original_index, installer.resource('index.forward.bsdiff'))
    except core.InstallError as error:
        raise ValueError(str(error)) from None
    if sha(payload) != p['installed_payload'] or sha(patched_index) != p['installed_index']:
        raise ValueError('Recovered patch hash mismatch.')
    # Check the native recipe without storing an executable in the workspace.
    offset = p['native_offset']; before = bytes.fromhex(p['native_before'])
    after = bytes.fromhex(p['native_after'])
    if original_exe[offset:offset+len(before)] != before:
        raise ValueError('Native recipe does not match the original executable.')
    if sha(original_exe[:offset]+after+original_exe[offset+len(before):]) != p['installed_exe']:
        raise ValueError('Native recipe result hash mismatch.')
    del original_exe
    with tempfile.TemporaryDirectory(prefix='metro-recovery-', dir=parent) as temporary:
        work = Path(temporary)/'workspace'; work.mkdir()
        # Copy authoring data only, never private receipts, raw backups or builds.
        for folder in ['03_translation', '04_fonts/src', '04_fonts/maps', '05_media',
                       'tools', 'skills', 'installer', 'translations', 'docs', 'assets', 'project_seed']:
            source = ROOT/folder
            if source.is_dir():
                shutil.copytree(source, work/folder, ignore=shutil.ignore_patterns(
                    '__pycache__', '*.pyc', 'upstream', '*.zip', '*.exe', '*.dll', '*.pyd', '.venv'))
        for name in ['README.md', 'LICENSE', 'CHANGELOG.md', '.gitignore', 'project.json',
                     'requirements-project.txt', 'AGENTS.md']:
            if (ROOT/name).is_file(): shutil.copy2(ROOT/name, work/name)
        original = work/'01_original/steam_local'; original.mkdir(parents=True)
        (original/'patch_04.vfx').write_bytes(original_index)
        extracted = work/'02_extracted/steam_local'; extracted.mkdir(parents=True)
        for item, raw in zip(p['base_assets'], base):
            target = extracted/'patch_04'/safe_relative(item['path'])
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        # fonts_us.bin is nested inside config.bin, not a loose archive record.
        config = (extracted/'patch_04/content/config.bin').read_bytes()
        expected = zlib.crc32(b'content\\scripts\\fonts_us.bin'); pos = 0; font = None
        while pos < len(config):
            crc, size = struct.unpack_from('<II', config, pos); pos += 8
            if size > len(config)-pos: raise ValueError('Truncated original config.')
            if crc == expected: font = config[pos:pos+size]
            pos += size
        if font is None: raise ValueError('Original font metadata not found.')
        path = extracted/'patch_04/content/scripts/fonts_us.bin'; path.parent.mkdir(parents=True)
        path.write_bytes(font)
        for name in ['speaker_map.json', 'dramatis_records.json']:
            source = ROOT/'project_seed'/name
            if not source.is_file(): source = ROOT/'02_extracted/steam_local'/name
            if not source.is_file(): raise ValueError('Missing authoring metadata: '+name)
            shutil.copy2(source, extracted/name)
        # Legacy builders use this exact indexed-tree JSON layout.
        from metro_archive import index
        (extracted/'patch_04_index.json').write_text(json.dumps(index(original/'patch_04.vfx'), indent=1), encoding='utf-8')
        patch = work/'07_patch/phases/100_final_review_r1'; patch.mkdir(parents=True)
        (patch/'patch_04.vfx').write_bytes(patched_index)
        (patch/p['payload_name']).write_bytes(payload)
        archive = Archive(patch/'patch_04.vfx')
        stage = work/'06_build/stage'
        for item in p['base_assets']:
            entry = next(e for e in archive.entries if e.id == item['id'])
            path = stage/safe_relative(item['path']); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(entry))
        for directory in ['08_qa/audit', '08_qa/shots', '09_release', '04_fonts/build']:
            (work/directory).mkdir(parents=True, exist_ok=True)
        from metro_lng import parse
        chars, pairs = parse((stage/'content/localization/stable_us.lng').read_bytes())
        (work/'04_fonts/build/font_characters.json').write_text(json.dumps(chars), encoding='utf-8')
        font_source = ROOT/'04_fonts/build/noto_arabic_pf.ttf'
        if font_source.is_file(): shutil.copy2(font_source, work/'04_fonts/build/noto_arabic_pf.ttf')
        metadata = dict(schema=1, revision=p['revision'], recovered_from='compatible local game',
                        original_index_sha256=sha(original_index), index_sha256=sha(patched_index),
                        payload_sha256=sha(payload), native_recipe_verified=True,
                        game_written=False, game_launched=False, runtime_entries=len(pairs),
                        original_assets=[dict(path=e['path'], sha256=sha(b)) for e,b in zip(p['base_assets'],base)])
        (work/'08_qa/audit/source_recovery.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        # Final rename only after every byte and dependency has been checked.
        if destination.exists() or destination.is_symlink(): raise ValueError('Destination appeared during recovery.')
        work.rename(destination)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        report = recover(args.game, args.out)
    except (OSError, ValueError, FormatError) as error:
        parser.exit(2, str(error)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
