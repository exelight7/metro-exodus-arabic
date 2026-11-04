"""Version-locked loading-text completion patch; never launches the game.

Only replaces the loading renderer's increment/read pair with a bounded display
budget. The existing record-count checks and completion path remain unchanged.
"""
import hashlib
import json
from pathlib import Path

REVISION = 'loading_complete_r1'
ORIGINAL_SHA256 = 'd4ab0e9b076d324f6b8ddad601fd9dda68c0c593adb7b0019944d560bc9875a5'
OFFSET = 7513870
RVA = 0x72b30e
BEFORE = bytes.fromhex('ff83340200008b8334020000')
# mov eax,1048576; mov [rbx+0x234],eax; nop. Same 12-byte span.
AFTER = bytes.fromhex('b80000100089833402000090')
BUDGET = 1048576

def digest(data):
    return hashlib.sha256(data).hexdigest()

def build(original):
    assert digest(original) == ORIGINAL_SHA256, 'Unsupported or modified executable'
    assert original[OFFSET:OFFSET+len(BEFORE)] == BEFORE
    assert len(BEFORE) == len(AFTER)
    result = original[:OFFSET] + AFTER + original[OFFSET+len(BEFORE):]
    assert result[:OFFSET] == original[:OFFSET]
    assert result[OFFSET+len(AFTER):] == original[OFFSET+len(BEFORE):]
    return result

def verified_original(game_exe,root):
    """Read clean source after installation without undoing the live repair."""
    raw=Path(game_exe).read_bytes()
    if digest(raw)==ORIGINAL_SHA256:return raw
    receipt=json.loads((Path(root)/'00_admin/loading_native_receipt.json').read_text())
    assert not receipt.get('restored') and digest(raw)==receipt['installed_sha256']
    clean=Path(receipt['backup']).read_bytes()
    assert digest(clean)==ORIGINAL_SHA256 and build(clean)==raw
    return clean
