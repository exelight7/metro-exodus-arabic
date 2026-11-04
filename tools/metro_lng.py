"""Lossless Metro LNG chunks and variable-width character-table codec.
Format reference: tsnest/MetroTools/src/metro/MetroLocalization.cpp.
The upstream repository declares no license; its source is not bundled here.
"""
import struct

def chunks(b):
    p=0; result=[]
    while p<len(b):
        tag,n=struct.unpack_from('<II',b,p);p+=8
        assert p+n<=len(b)
        result.append((tag,b[p:p+n]));p+=n
    return result

def decode(raw,chars):
    out=[];i=0
    while i<len(raw):
        c=raw[i];i+=1
        if c>=224:
            c=c*255+raw[i]-0xDE41;i+=1
        out.append(chars[c])
    return ''.join(out)

def encode(text,chars):
    lookup={c:i for i,c in reversed(list(enumerate(chars)))};out=bytearray()
    for c in text:
        n=lookup[c]
        assert n!=0,'Embedded null is not allowed'
        if n<224:out.append(n)
        else:
            q=(n-224)//255;out.extend((224+q,(n-224)%255+1))
    return bytes(out)

def parse(b):
    cs=chunks(b);chars=next(data for tag,data in cs if tag==1).decode('utf-16le');pairs=[]
    data=next(data for tag,data in cs if tag==2);parts=data.split(b'\0');assert parts[-1]==b'' and len(parts)%2==1
    for i in range(0,len(parts)-1,2):pairs.append((parts[i].decode('utf-8'),decode(parts[i+1],chars)))
    return chars,pairs

def build(original,chars,pairs):
    body=b''.join(k.encode()+b'\0'+encode(v,chars)+b'\0' for k,v in pairs)
    return b''.join(struct.pack('<II',tag,len(data))+data for tag,data in
        [(tag,chars.encode('utf-16le') if tag==1 else body if tag==2 else data) for tag,data in chunks(original)])
