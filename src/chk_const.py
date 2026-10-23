# -*- coding: utf-8 -*-
"""检验: 偏差是否源于 PHREEQC 用解析式常数而反算用标称 log_k"""
import re, sys, math
sys.stdout.reconfigure(encoding="utf-8")
Ka2n=10**-10.329
import os
from config import OUT as B
PAT=[("CO2",r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("HCO3-",r"^\s+HCO3-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("CO3-2",r"^\s+CO3-2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("OH-",r"^\s+OH-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("H+",r"^\s+H\+\s+([\d.eE+-]+)\s+([\d.eE+-]+)")]
def blocks(path):
    t=open(path,encoding="utf-8",errors="ignore").read()
    parts=re.split(r"Initial solution (\d+)\.",t); out=[]
    for i in range(1,len(parts),2):
        b=parts[i+1]; d={}
        for n,pat in PAT:
            m=re.findall(pat,b,re.M)
            if m: d[n]=(float(m[-1][0]),float(m[-1][1]))
        if d: out.append(d)
    return out

def solve(x, Ka1a, Ka2):
    aH=x["H+"][1]
    g1=10**math.log10(x["HCO3-"][1]/x["HCO3-"][0])
    g0=10**math.log10(x["CO2"][1]/x["CO2"][0])
    g2=10**math.log10(x["CO3-2"][1]/x["CO3-2"][0])
    CT=x["CO2"][0]+x["HCO3-"][0]+x["CO3-2"][0]
    lo,hi=1e-8,0.5
    for _ in range(300):
        mid=(lo+hi)/2
        f=(aH*mid/Ka1a)/g0 + mid/g1 + (Ka2*mid/aH)/g2 - CT
        if f<0: lo=mid
        else: hi=mid
    ah=(lo+hi)/2
    return (aH*ah/Ka1a)/g0, ah/g1, (Ka2*ah/aH)/g2

for tag,path,pres in [("口径A", B+r"\round2_out.txt",[0.10,0.25,0.50,1.00,1.50,2.00]),
                      ("口径B", B+r"\round3_out.txt",[0.10,0.25,0.50,1.00,1.50,2.00])]:
    print("="*100); print("  %s" % tag); print("="*100)
    print("%6s %13s %13s %13s %13s"
          % ("MPa","标称pKa1","偏差(标称)","PHREEQC实际pKa1","偏差(实际常数)"))
    print("-"*70)
    for m,x in zip(pres, blocks(path)):
        p=x["CO2"][0]
        Ka1_nom=10**-6.351
        c_nom,_,_ = solve(x, Ka1_nom, Ka2n)
        # 由 PHREEQC 自身活度反算实际常数
        Ka1_act = x["H+"][1]*x["HCO3-"][1]/x["CO2"][1]
        Ka2_act = x["H+"][1]*x["CO3-2"][1]/x["HCO3-"][1]
        c_act,_,_ = solve(x, Ka1_act, Ka2_act)
        pc=lambda v:100*(v-p)/p
        print("%6.2f %13.3f %12.2f%% %13.3f %12.2f%%"
              % (m, -math.log10(Ka1_nom), pc(c_nom),
                 -math.log10(Ka1_act), pc(c_act)))
    print()
