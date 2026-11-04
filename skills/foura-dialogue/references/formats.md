# Format support and evidence

| Format/profile | Read/list/extract | Rebuild | Evidence |
|---|---|---|---|
| VFX v3, LZ4 / Metro Exodus | XOR names, local VFS files, chained LZ4 | Separate supplemental VFS, zero-duplicate index | Real Steam Exodus files + synthetic malformed inputs |
| VFX v1, non-legacy / Redux family | Implemented | Same constraints | Synthetic fixtures derived from upstream layout; real Redux installation not tested |
| VFX v2 / Arktika.1 family | Implemented | Same constraints | Synthetic fixtures; real Arktika.1 installation not tested |
| Known original Last Light GUIDs | Index and uncompressed records; compressed QuickLZ explicitly refused | Refused | Upstream profile recognition + fabricated fixtures |
| Original Metro 2033 VFI, UPK | Extension recognition only | Not implemented | Use upstream MetroTools for these containers |
| Chunked LNG, tags 1/2 | Custom character-table codec, UTF-8 IDs | Preserve unknown chunks, key order and unchanged encoded bytes | Real Exodus original and patched LNG files; all 15 original localization files checked separately |
| Other 4A formats/editions | Probe only until identified | Refuse unknown format | No implied support from engine name |

## VFX layout

Little-endian u32 version and compression field, optional content-version string
for v3, 16-byte GUID, package/file/duplicate counts, packages, indexed tree records.
Normal file records have flags:u16, pak:u16, offset/usize/csize:u32. Folder records
have flags:u16, count:u16, first:u32. Names have byte count, XOR mask, obfuscated
bytes and an unmodified trailing null. A folder name may contain a full relative
virtual path in patch indexes. Normalization must still reject escapes and device
aliases.

VFX patch files can contain inherited references to packages outside their own
package table. An Exodus patch_04 fixture contains 1,956 such records. Do not treat
the whole index as corrupt or guess a package filename. Read a selected record
only when its package reference is locally resolvable. Repacking preserves other
records without resolving their data.

LZ4 streams use repeated u32 packet size (including 8-byte header), u32 decoded
size and compressed payload, with up to 64 KiB of preceding decoded history.
Equal compressed/uncompressed sizes indicate stored bytes rather than this stream.
Original Last Light has a distinct GUID-selected QuickLZ path.

## LNG layout

Repeated u32 tag, u32 payload length, payload. Tag 1 is UTF-16LE character table;
tag 2 is null-separated UTF-8 key/custom-encoded value pairs. Character codes below
224 occupy one byte. A lead byte >=224 consumes a second nonzero byte; decoded
index = lead*255 + second - 0xDE41. The representable table limit is 8,384 entries.
The helper supports BMP characters and rejects embedded null/non-BMP targets.

Do not drop unknown chunks, merge repeated keys silently, normalize native line
break tokens or rewrite unchanged encoded values when a character table contains
duplicate characters. A successful codec rebuild does not create font glyphs.

## Primary format references

- [ShokerStlk/MetroEX](https://github.com/ShokerStlk/MetroEX), MIT, VFX and LZ4 implementation.
- [tsnest/MetroTools VFXReader](https://github.com/tsnest/MetroTools/blob/main/src/metro/VFXReader.cpp) and [header](https://github.com/tsnest/MetroTools/blob/main/src/metro/VFXReader.h), profile/GUID differences.
- [MetroLocalization](https://github.com/tsnest/MetroTools/blob/main/src/metro/MetroLocalization.cpp), chunked LNG and variable-width character table.
- [MetroCompression](https://github.com/tsnest/MetroTools/blob/main/src/metro/MetroCompression.cpp), LZ4 versus legacy QuickLZ.

This helper is independently written Python. The upstream projects are references,
not bundled engine SDKs. No universal decryption key or executable patch for other
4A games is supplied. The Metro Exodus loading EXE recipe belongs to that exact
project/version and must not be reused for a different game.
