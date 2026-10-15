"""Parse the deliberately small SVG path subset into editable DrawingML commands."""
import math,re
TOKEN=re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
ARITY={"M":2,"L":2,"C":6,"Q":4,"Z":0}
def parse_path(data):
    if not isinstance(data,str) or not data.strip():raise ValueError("path.d must be nonempty")
    tokens=TOKEN.findall(data)
    residue=TOKEN.sub("",data)
    if residue.strip(" ,\t\r\n"):raise ValueError("Invalid path syntax")
    out=[];i=0;command=None;cursor=[0.,0.];origin=cursor[:]
    while i<len(tokens):
        if tokens[i].isalpha():
            command=tokens[i];i+=1
            if command.upper() not in ARITY:raise ValueError("Only M/L/C/Q/Z paths are supported")
            if command.upper()=="Z":
                out.append({"op":"Z","points":[]});cursor=origin[:];command=None;continue
        if command is None:raise ValueError("Path command expected")
        op=command.upper();n=ARITY[op]
        if i+n>len(tokens) or any(t.isalpha() for t in tokens[i:i+n]):raise ValueError("Incomplete path command")
        values=[float(v) for v in tokens[i:i+n]];i+=n
        if not all(math.isfinite(v) for v in values):raise ValueError("Nonfinite path coordinate")
        pts=[values[k:k+2] for k in range(0,n,2)]
        if command.islower():pts=[[p[0]+cursor[0],p[1]+cursor[1]] for p in pts]
        if not out and op!="M":raise ValueError("Path must start with M")
        out.append({"op":op,"points":pts});cursor=pts[-1][:]
        if op=="M":origin=cursor[:];command="l" if command.islower() else "L"
    if command is not None and tokens and tokens[-1].isalpha():raise ValueError("Incomplete path command")
    return out

def path_string(commands):
    return " ".join(c["op"]+(" "+" ".join(f"{v:.6f}" for p in c["points"] for v in p) if c["points"] else "") for c in commands)

