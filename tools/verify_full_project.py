"""Verify a recovered workspace and an isolated text rebuild without game writes."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--rebuilt',required=True,type=Path)
    parser.add_argument('--game',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args();work=args.workspace.resolve();game=args.game.resolve()
    p=json.loads((work/'installer/resources/profile.json').read_text(encoding='utf-8'))
    recovery=json.loads((work/'08_qa/audit/source_recovery.json').read_text(encoding='utf-8'))
    final=work/'07_patch/phases/100_final_review_r1'
    assert digest(final/'patch_04.vfx')==p['installed_index']
    assert digest(final/p['payload_name'])==p['installed_payload']
    rebuilt=json.loads((args.rebuilt/'patch-manifest.json').read_text(encoding='utf-8'))
    payload=next(name for name in rebuilt['files'] if name.endswith('.vfs0'))
    assert digest(args.rebuilt/payload)==p['installed_payload']
    assert rebuilt['unrelated_records_preserved'] and rebuilt['replaced_files']==12
    baseline={name:digest(game/name) for name in ['patch_04.vfx','MetroExodus.exe',p['payload_name']]}
    assert baseline['patch_04.vfx']==p['installed_index'] and baseline['MetroExodus.exe']==p['installed_exe']
    spec=importlib.util.spec_from_file_location('recovery_check',ROOT/'tools/recover_project.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='metro-recovery-negative-') as temporary:
        temporary=Path(temporary)
        existing=temporary/'existing';existing.mkdir();(existing/'sentinel').write_bytes(b'keep')
        try: module.recover(game,existing)
        except ValueError: pass
        else: raise AssertionError('Existing output accepted')
        assert (existing/'sentinel').read_bytes()==b'keep'
        try: module.recover(game,game/'must-not-be-created-by-recovery')
        except ValueError: pass
        else: raise AssertionError('Game-contained output accepted')
        assert not (game/'must-not-be-created-by-recovery').exists()
        fake=temporary/'unsupported';fake.mkdir();(fake/'MetroExodus.exe').write_bytes(b'MZunsupported')
        (fake/'patch_04.vfx').write_bytes(b'unsupported');out=temporary/'must-not-exist'
        try: module.recover(fake,out)
        except (ValueError,RuntimeError): pass
        else: raise AssertionError('Unsupported game accepted')
        assert not out.exists()
    assert {name:digest(game/name) for name in baseline}==baseline
    report=dict(recovered_index_exact=True,recovered_payload_exact=True,native_recipe_verified=recovery['native_recipe_verified'],
                current_csv_rebuild_payload_exact=True,all_12_assets_reproduced=True,unrelated_index_records_preserved=True,
                existing_output_refused=True,game_directory_output_refused=True,unsupported_version_refused=True,
                live_game_hashes_unchanged=True,game_launched=False,
                payload_sha256=p['installed_payload'],original_assets_recovered=len(recovery['original_assets']))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
