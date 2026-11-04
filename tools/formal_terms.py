"""Formal Arabic gameplay vocabulary, guarded by the English source context."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'03_translation/formal_terms.json').read_text(encoding='utf-8'))
DATA['labels'].update(json.loads((ROOT/'03_translation/comprehensive_r2_labels.json').read_text(encoding='utf-8')))
DATA.setdefault('voice_labels',{}).update(json.loads((ROOT/'03_translation/comprehensive_voice_review.json').read_text(encoding='utf-8')))
DATA['voice_labels'].update(json.loads((ROOT/'03_translation/comprehensive_r2_voice.json').read_text(encoding='utf-8')))
for filename in ['formal_terms_r2_context.json','formal_terms_r3_context.json','formal_terms_r4_context.json','comprehensive_context_review.json','comprehensive_r2_context.json','comprehensive_r3_context.json','final_review_r1_context.json']:
    review=ROOT/'03_translation'/filename
    if review.exists():DATA.setdefault('contextual',{}).update(json.loads(review.read_text(encoding='utf-8')))
TAG=re.compile('<[^>]+>')

def formal_terms(key,source,target):
    if 'credits' in key or any(x in key.lower() for x in ['eula','legal','license','copyright']):return target
    plain=TAG.sub('',source).strip()
    if key in DATA.get('contextual',{}):
        target=DATA['contextual'][key]
        assert sorted(TAG.findall(target))==sorted(TAG.findall(source)),key
    label=DATA['labels'].get(plain.casefold()) if not key.startswith('voices\\') else None
    if key.startswith('voices\\'):label=DATA.get('voice_labels',{}).get(plain)
    if label:
        if plain.casefold() in ['fire','stock'] and not re.search('wpn|weapon|custom|ctrl|gp_',key):label=None
    if label:
        # Replace the single text span without touching dynamically bound icons.
        chunks=re.split('(<[^>]+>)',source)
        spans=[i for i,s in enumerate(chunks) if s.strip() and not s.startswith('<')]
        if len(spans)==1:
            chunks[spans[0]]=' '+label+' ';target=''.join(chunks).strip()
    for rule in DATA['rules']:
        if rule.get('ui_only') and key.startswith('voices\\'):continue
        if rule.get('keys') and not re.search(rule['keys'],key,re.I):continue
        if not re.search(rule['source'],plain,re.I):continue
        for old,new in rule['replace'].items():
            pat=re.compile(r'(?<![\u0621-\u064a])'+re.escape(old)+r'(?![\u0621-\u064a])')
            target=''.join(s if s.startswith('<') else pat.sub(new,s) for s in re.split('(<[^>]+>)',target))
    return target
