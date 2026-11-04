---
name: foura-dialogue
description: Extract, decode, edit and rebuild dialogue/localization files from 4A Engine games using format-aware VFX/LZ4 and LNG tools. Use for Metro Exodus, Metro Redux or matching 4A resource formats; determine compatibility from the file, not only the game name.
---

# 4A dialogue and localization

Use the bundled `scripts/foura_dialogue.py` to inspect archives, remove XOR filename
obfuscation, decompress supported LZ4 streams and decode LNG character tables.
These are resource-format operations. They do not supply a game, transcribe audio,
launch a game, install a patch or unlock protected executable content.

## Select the actual format

Resolve this skill's directory and invoke the script by its real path. `probe`
and LNG commands use Python's standard library; compressed extraction additionally
needs `python -m pip install -r scripts/requirements.txt` in the chosen environment.

```sh
python scripts/foura_dialogue.py probe "/path/to/Metro Exodus"
python scripts/foura_dialogue.py list "/path/to/game/patch_04.vfx" --pattern "*.lng"
```

Inspect the reported version/profile before choosing a workflow. Read
[references/formats.md](references/formats.md) when the format is unfamiliar or
the request involves another 4A game. VFX versions 1/2/3 have implementations;
Exodus v3 has real-file validation. Redux/Arktika variants have synthetic-fixture
validation, not a blanket real-game guarantee. Known original Last Light GUIDs
use QuickLZ rather than the supported LZ4 codec. VFI/UPK are recognized only.
Stop unsupported decoding without interpreting arbitrary bytes as dialogue.

## Extract and edit

Choose a new working directory outside the game directory. Paths inside the index
are data: traversal, absolute paths, device names and links are not valid outputs.
Only select the localization resources needed for the task; the default is `*.lng`.

```sh
python scripts/foura_dialogue.py extract "/game/patch_04.vfx" --pattern "*/stable_us.lng" --out "/work/extracted"
python scripts/foura_dialogue.py verify-lng "/work/extracted/content/localization/stable_us.lng"
python scripts/foura_dialogue.py export-lng "/work/extracted/content/localization/stable_us.lng" --out "/work/strings.csv"
```

The CSV contains `id,source,target`. Initially target equals source for a no-edit
roundtrip. Use `--dialogue-only` when the task is limited to `voices\` keys and
timed records; omit it for complete localization. Edit target, retain identifiers
and source. Read [references/workflow.md](references/workflow.md) for repacking,
partial tables and concrete failure recovery.

For a newly encountered format, export/import an unchanged table and compare file
SHA256 before producing a translated archive. Import preserves record order,
untouched encoded strings and unknown LNG chunks. It refuses stale source columns,
duplicate IDs and protected-tag/variable/timing changes. Do not enable
`--allow-format-changes` just to silence a failure; use it only for an intentional
format change that is part of the user's request.

## Arabic-specific work

Keep authored Arabic logical and readable in the table. Codec support is distinct
from glyph coverage, shaping, bidi layout, line wrapping and reveal animation.
Do not infer native RTL support from successfully storing Unicode. Determine the
renderer behavior and font coverage before selecting pre-shaping or visual order.
Wrap logical text against actual font metrics before visual reordering when the
renderer needs it. Preserve input placeholders, speaker identity and timing.

Prefer meaningful formal Arabic for gameplay concepts. Preserve established proper
names and any technology names the user chose to keep in English. The CLI itself
does no translation or Arabic presentation conversion and should remain useful for
other languages.

## Build a separate patch

```sh
python scripts/foura_dialogue.py import-lng "/work/extracted/content/localization/stable_us.lng" --table "/work/strings.csv" --out "/work/replacements/content/localization/stable_us.lng"
python scripts/foura_dialogue.py pack-vfx "/game/patch_04.vfx" --from "/work/replacements" --out "/work/new-patch" --pak-name "my_arabic_01.vfs0"
```

The output is an index plus a supplemental VFS and hash manifest, in a new external
folder. No source/game file is replaced. Repacking requires a supported non-legacy
index with zero duplicate records and a known trailer. Untouched index records
remain byte-identical. Inherited/global package references are preserved but are
not independently mounted by this tool; select a locally resolvable record or
use the complete upstream filesystem implementation for that case.

Before any separately authorized deployment, use the appropriate game/version
installer with originals and rollback. Extraction, codec tests and static previews
are not proof of in-game rendering. State what was actually tested. Publish the
translation, licensed fonts, differences and tool sources; recover original game
assets from the user's compatible installation.

## Validate the helper

```sh
python scripts/test_foura_dialogue.py
```

This suite uses fabricated data in temporary directories. It covers codec
boundaries, unknown chunks, protected timing, traversal, malformed data, LZ4
history, VFX 1/2/3 and repack preservation. See the compatibility reference for the
separate real-file evidence and attribution.
