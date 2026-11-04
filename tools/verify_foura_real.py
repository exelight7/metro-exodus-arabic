"""Read-only real Exodus verification plus a private repack/CSV fixture."""
from pathlib import Path
import importlib.util,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'skills/foura-dialogue/scripts'
sys.path.insert(0,str(SKILL));import foura_dialogue as f
from metro_archive import index as old_index,extract as old_extract
from metro_lng import parse as old_parse

def main():
    game=Path(r'C:/Program Files (x86)/Steam/steamapps/common/Metro Exodus')
    source=ROOT/'01_original/steam_local/patch_04.vfx';archive=f.Archive(source)
    # The original index is a local snapshot; its unmodified VFS data stay in the
    # Steam install. This test only reads them and never links/writes live files.
    archive.root=game.resolve();baseline=old_index(source)
    checked=[]
    for e in archive.matching():
        raw=archive.read(e);other=old_extract(game,baseline,baseline['entries'][e.id])
        assert raw==other
        parsed=f.LNG(raw);chars,pairs=old_parse(raw)
        assert parsed.chars==chars and list(parsed.texts.items())==pairs
        assert parsed.rebuild({})==raw
        checked.append(dict(path=e.path,records=len(parsed.texts),sha256=f.sha(raw)))
    current=f.Archive(game/'patch_04.vfx');entry=next(e for e in current.matching() if e.name=='stable_us.lng')
    patched=current.read(entry);assert f.LNG(patched).rebuild({})==patched
    with tempfile.TemporaryDirectory(prefix='foura-real-',dir=ROOT/'06_build') as temp:
        private=Path(temp).resolve();assert private.is_relative_to((ROOT/'06_build').resolve())
        out=private/'extracted';report=f.extract_archive(archive,out,'*/stable_us.lng')
        rawpath=out/'content/localization/stable_us.lng';table=private/'strings.csv'
        f.export_lng(rawpath,table);f.import_lng(rawpath,table,private/'roundtrip.lng')
        assert rawpath.read_bytes()==(private/'roundtrip.lng').read_bytes()
        # Repack the already-built translation using the original index without
        # accessing any unrelated live payload, then compare the written bytes.
        replacement=private/'replacement/content/localization';replacement.mkdir(parents=True)
        (replacement/'stable_us.lng').write_bytes(patched)
        repack=f.pack_archive(archive,private/'replacement',private/'patch')
        new=f.Archive(private/'patch/patch_04.vfx');e=next(e for e in new.matching() if e.name=='stable_us.lng')
        assert new.read(e)==patched
    result=dict(tool_version=f.VERSION,real_game='Metro Exodus Steam Windows',localization_files=len(checked),
                original_lng_roundtrips=True,current_patched_lng_roundtrip=True,private_csv_roundtrip=True,
                private_repack_verified=True,unrelated_records_preserved=repack['unrelated_records_preserved'],
                legacy_real_games_tested=False,game_launched=False,live_game_written=False,files=checked)
    (ROOT/'08_qa/audit/foura_real_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if __name__=='__main__':main()
