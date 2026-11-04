"""Matched glyph masks for two native subtitle controls with independent tint.

PUA aliases retain precisely the original advances. This keeps wrapping and
centering identical between the white speech and orange speaker layers.
"""
import json,sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/vendor/game-arabization'))
from ar_shape import Shaper

@lru_cache(maxsize=1)
def aliases():
    names=json.loads((ROOT/'03_translation/speaker_names.json').read_text(encoding='utf-8'))
    overrides=json.loads((ROOT/'03_translation/overrides_by_id.json').read_text(encoding='utf-8'))
    records=json.loads((ROOT/'02_extracted/steam_local/dramatis_records.json').read_text())
    actor_keys={records['strings'][v[2]] for v in records['records']}-{''}
    shape=Shaper(mode='visual',harakat='strip',normalize_persian=True,newline_tokens=['\n','<br>'])
    chars=set(':')
    for key in actor_keys:chars.update(shape.process(overrides[key].strip().rstrip(':').strip()))
    chars.discard(' ')
    return {c:chr(0xE000+i) for i,c in enumerate(sorted(chars))}

def encode_name(text):
    return text.translate(str.maketrans(aliases()))

def decode_name(text):
    return text.translate(str.maketrans({v:k for k,v in aliases().items()}))
