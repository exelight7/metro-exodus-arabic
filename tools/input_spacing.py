"""Separate Arabic words from real input icons before Arabic shaping.

Only known input tags are eligible. Timing, formatting and voice annotations
are deliberately excluded, and existing whitespace is retained.
"""
import re
INPUT=re.compile(r'<(?:#?(?:wpn_[a-z0-9_]+|sprint|crouch_toggle)|menu_[a-z0-9_]+|xpad_[a-z0-9_]+|stick_[a-z0-9_]+|popup_[a-z0-9_]+|k(?:[a-zA-Z]|Space|Return|UP|LEFT|DOWN|RIGHT)|mouse[01]|use|USE|map|rui|crouch|jump|medkit|forward|back|rstrafe|lstrafe|filter|special|lighter|start|nightvision|changemenumap|inventory|gasmask|photo_mode|charger|binoculars)>')
WORD=re.compile(r'[\w\u0600-\u06ff]',re.UNICODE)

def normalize_input_spacing(key,text):
    if key.startswith('voices\\') or not re.search('[\u0600-\u06ff]',text):return text
    def separate(m):
        before=text[m.start()-1:m.start()] if m.start() else ''
        after=text[m.end():m.end()+1]
        left=' ' if before and WORD.fullmatch(before) else ''
        right=' ' if after and WORD.fullmatch(after) else ''
        return left+m[0]+right
    return INPUT.sub(separate,text)
