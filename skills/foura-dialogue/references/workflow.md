# Working examples and recovery

Use the helper path relative to the skill directory; all paths below are examples.
On Windows quote full paths, e.g. `"D:/Games/Metro Exodus/patch_04.vfx"`.

1. Probe/list the local index. If the files use VFI, QuickLZ or an unsupported
   version, use a compatible upstream reader or report the limitation. Do not
   rename the extension to force a decoder.
2. Extract `*.lng` to a new directory outside the installation. To resolve a patch
   and its VFS packages, use the index in its real package directory. An index
   copied alone into an originals folder does not carry its packages with it.
3. Export a full CSV or a dialogue subset. Target initially matches source.
4. Reimport the unchanged CSV into a separate LNG and compare SHA256. This checks
   the actual source format, including unknown chunks and ambiguous code values.
5. Edit target only. An omitted row in a partial CSV retains its original bytes;
   an explicitly empty target empties that string. Preserve IDs and source.
6. Put rebuilt files under matching virtual paths in a clean replacement tree.
   Do not put CSVs/reports into that tree: unknown replacement paths are refused.
7. `pack-vfx` creates a new index+VFS+manifest folder. Verify it and handle game
   installation as a distinct, authorized task with originals/backup/restore.

## Commands

```sh
python scripts/foura_dialogue.py probe "/game/patch_04.vfx"
python scripts/foura_dialogue.py list "/game/patch_04.vfx" --pattern "*.lng"
python scripts/foura_dialogue.py extract "/game/patch_04.vfx" --pattern "*/stable_us.lng" --out "/work/extracted"
python scripts/foura_dialogue.py export-lng "/work/extracted/content/localization/stable_us.lng" --out "/work/dialogue.csv" --dialogue-only
python scripts/foura_dialogue.py import-lng "/work/extracted/content/localization/stable_us.lng" --table "/work/dialogue.csv" --out "/work/replacements/content/localization/stable_us.lng"
python scripts/foura_dialogue.py verify-lng "/work/replacements/content/localization/stable_us.lng"
python scripts/foura_dialogue.py pack-vfx "/game/patch_04.vfx" --from "/work/replacements" --out "/work/patch-01" --pak-name "my_dialogue_01.vfs0"
```

## Expected failures

- Existing output: select a new output name/directory. Inputs are never overwritten.
- Stale source column: export from the actual LNG being edited, then merge targets
  by identifier after reviewing the version difference.
- Protected token/timing mismatch: inspect the source and intended translation.
  Do not remove a variable or timestamp to make validation pass.
- Character outside native font: code-table support and bitmap/font support are
  separate; supply and validate glyphs using the game's font format.
- Inherited package reference: the selected file needs a wider filesystem mount
  than this standalone index. Use the owning index or an upstream filesystem tool.
- Unsupported compression, duplicates or trailer: keep the source and report the
  exact detected format. Do not emit a speculative index or install partial data.
