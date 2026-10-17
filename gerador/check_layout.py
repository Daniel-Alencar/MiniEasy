import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sexp import load,unq
doc=load(sys.argv[1])
libbox={}
for n in doc:
    if isinstance(n,list) and n[0]=='lib_symbols':
        for s in n[1:]:
            name=unq(s[1]); xs=[];ys=[]
            def walk(nd):
                if not isinstance(nd,list):return
                if nd and nd[0] in ('rectangle','polyline','circle','arc','pin'):
                    for q in nd:
                        if isinstance(q,list) and q[0] in ('start','end','mid','center','at'):
                            xs.append(float(q[1]));ys.append(float(q[2]))
                        if isinstance(q,list) and q[0]=='pts':
                            for r in q[1:]:
                                xs.append(float(r[1]));ys.append(float(r[2]))
                for q in nd:
                    if isinstance(q,list): walk(q)
            walk(s)
            libbox[name]=(min(xs),min(ys),max(xs),max(ys)) if xs else (0,0,0,0)
boxes=[]
for n in doc:
    if isinstance(n,list) and n[0]=='symbol' and any(isinstance(q,list) and q[0]=='lib_id' for q in n):
        lid=at=ref=None
        for q in n:
            if isinstance(q,list) and q[0]=='lib_id': lid=unq(q[1])
            elif isinstance(q,list) and q[0]=='at': at=(float(q[1]),float(q[2]))
            elif isinstance(q,list) and q[0]=='property' and unq(q[1])=='Reference': ref=unq(q[2])
        x0,y0,x1,y1=libbox[lid]
        boxes.append((ref,(at[0]+x0,at[1]-y1,at[0]+x1,at[1]-y0)))
def ov(a,b,m=0.0):
    return not (a[2]<=b[0]+m or b[2]<=a[0]+m or a[3]<=b[1]+m or b[3]<=a[1]+m)
bad=[(boxes[i][0],boxes[j][0]) for i in range(len(boxes)) for j in range(i+1,len(boxes)) if ov(boxes[i][1],boxes[j][1])]
labs=[]
for n in doc:
    if isinstance(n,list) and n[0]=='label':
        txt=unq(n[1])
        for q in n:
            if isinstance(q,list) and q[0]=='at': x,y,a=float(q[1]),float(q[2]),float(q[3])
        w=len(txt)*0.95+0.8; h=1.8
        bb={0:(x,y-h,x+w,y),180:(x-w,y-h,x,y),90:(x,y-w,x+h,y)}.get(a,(x-h,y,x,y+w))
        labs.append((txt,bb))
clash=[(t,ref) for t,bb in labs for ref,bx in boxes if ov(bb,bx,0.3)]
lab2=[(labs[i][0],labs[j][0]) for i in range(len(labs)) for j in range(i+1,len(labs)) if ov(labs[i][1],labs[j][1],0.3)]
oob=[(r,b) for r,b in boxes if b[0]<8 or b[1]<8 or b[2]>586 or b[3]>412]
print("sobreposicao corpo-corpo:",len(bad),bad[:10])
print("rotulo sobre corpo:",len(clash),clash[:10])
print("rotulo sobre rotulo:",len(lab2),lab2[:10])
print("fora da folha A2:",len(oob),oob[:5])
