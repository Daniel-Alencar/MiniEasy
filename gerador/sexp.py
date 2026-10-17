import sys, re

def tokenize(s):
    out=[]; i=0; n=len(s)
    while i<n:
        c=s[i]
        if c in '()':
            out.append(c); i+=1
        elif c.isspace():
            i+=1
        elif c=='"':
            j=i+1; buf=[]
            while j<n:
                if s[j]=='\\':
                    buf.append(s[j:j+2]); j+=2
                elif s[j]=='"':
                    break
                else:
                    buf.append(s[j]); j+=1
            out.append('"'+''.join(buf)+'"'); i=j+1
        else:
            j=i
            while j<n and not s[j].isspace() and s[j] not in '()"':
                j+=1
            out.append(s[i:j]); i=j
    return out

def parse(tokens, pos=0):
    assert tokens[pos]=='('
    pos+=1; node=[]
    while tokens[pos]!=')':
        if tokens[pos]=='(':
            sub,pos=parse(tokens,pos)
            node.append(sub)
        else:
            node.append(tokens[pos]); pos+=1
    return node, pos+1

def load(path):
    return parse(tokenize(open(path,encoding='utf-8').read()))[0]

def unq(t):
    return t[1:-1] if isinstance(t,str) and t.startswith('"') else t

def find_symbol(lib, name):
    for n in lib:
        if isinstance(n,list) and n and n[0]=='symbol' and unq(n[1])==name:
            return n
    return None

def dump(node, indent=0):
    sp='  '*indent
    if isinstance(node,str):
        return sp+node
    head=node[0] if node and isinstance(node[0],str) else ''
    simple=all(isinstance(x,str) for x in node)
    if simple:
        return sp+'('+' '.join(node)+')'
    parts=[sp+'('+head]
    for x in node[1:]:
        if isinstance(x,str):
            parts[-1]+=' '+x
        else:
            parts.append(dump(x,indent+1))
    parts.append(sp+')')
    return '\n'.join(parts)

def pins(sym):
    res=[]
    for sub in sym:
        if isinstance(sub,list) and sub[0]=='symbol':
            for p in sub:
                if isinstance(p,list) and p[0]=='pin':
                    etype=p[1]; num=None; nm=None; at=None
                    for q in p:
                        if isinstance(q,list):
                            if q[0]=='number': num=unq(q[1])
                            elif q[0]=='name': nm=unq(q[1])
                            elif q[0]=='at': at=(q[1],q[2],q[3] if len(q)>3 else '0')
                    res.append((num,nm,etype,at))
    def key(t):
        try: return (0,int(t[0]))
        except: return (1,t[0])
    return sorted(res,key=key)

def base_of(sym):
    for q in sym:
        if isinstance(q,list) and q[0]=='extends':
            return unq(q[1])
    return None

def resolve(lib, name):
    sym=find_symbol(lib,name)
    seen=set()
    while sym is not None:
        b=base_of(sym)
        if b is None or b in seen: break
        seen.add(b); sym=find_symbol(lib,b)
    return sym

if __name__=='__main__':
    lib=load(sys.argv[1]); sym=resolve(lib, sys.argv[2])
    if sym is None: sys.exit('not found')
    if len(sys.argv)>3 and sys.argv[3]=='--dump':
        print(dump(sym))
    else:
        for num,nm,et,at in pins(sym):
            print(f"{num:>4}  {nm:<18} {et:<14} {at}")
