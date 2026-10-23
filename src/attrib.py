# -*- coding: utf-8 -*-
"""归因: 分析反算分别计入/不计入 (CO2)2 与 KHCO3, 看 CO2* 偏差变化"""
import re, sys, math
sys.stdout.reconfigure(encoding="utf-8")
KH=1.70e-3
Ka1a=10**-6.351; Ka2=10**-10.329; Kw=1.0e-14
KD=10**-1.73          # 2CO2=(CO2)2
import os
from config import OUT as B
PAT=[("CO2",r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("(CO2)2",r"^\s+\(CO2\)2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("HCO3-",r"^\s+HCO3-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("CO3-2",r"^\s+CO3-2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("KHCO3",r"^\s+KHCO3\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
     ("K+",r"^\s+K\+\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
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

def reconstruct(x, aH, g1, g0, g2, gd, CT, use_d, use_kh, Kkhco3, aK):
    aCO2 = aH*x/Ka1a
    dim  = (KD*aCO2*aCO2/gd) if use_d else 0.0
    kh   = (Kkhco3*aK*x)      if use_kh else 0.0
    return aCO2/g0 + x/g1 + (Ka2*x/aH)/g2 + 2*dim + kh - CT

def variant(x, use_d, use_kh):
    aH=x["H+"][1]
    g0=10**math.log10(x["CO2"][1]/x["CO2"][0])
    g1=10**math.log10(x["HCO3-"][1]/x["HCO3-"][0])
    g2=10**math.log10(x["CO3-2"][1]/x["CO3-2"][0])
    gd=10**math.log10(x["(CO2)2"][1]/x["(CO2)2"][0]) if "(CO2)2" in x else 1.0
    aK=x["K+"][1]
    Kkh=x["KHCO3"][0]/(x["K+"][1]*x["HCO3-"][1])     # 由输出反推络合常数
    CT=x["CO2"][0]+x["HCO3-"][0]+x["CO3-2"][0]
    if use_d: CT += 2*x["(CO2)2"][0]
    if use_kh: CT += x["KHCO3"][0]
    lo,hi=1e-8,0.5
    for _ in range(300):
        mid=(lo+hi)/2
        if reconstruct(mid,aH,g1,g0,g2,gd,CT,use_d,use_kh,Kkh,aK)<0: lo=mid
        else: hi=mid
    ah=(lo+hi)/2
    return (aH*ah/Ka1a)/g0, ah/g1, (Ka2*ah/aH)/g2

for tag,path,pres in [("口径A", B+r"\round2_out.txt",[0.10,0.25,0.50,1.00,1.50,2.00]),
                      ("口径B", B+r"\round3_out.txt",[0.10,0.25,0.50,1.00,1.50,2.00])]:
    R=blocks(path); print("="*94); print("  %s   CO2* 分析反算的偏差 (负=高于PHREEQC)" % tag); print("="*94)
    print("%6s %11s %13s %13s %13s"
          % ("MPa","PHREEQC [CO2*]","①不含络合物","②计入(CO2)2","③计入(CO2)2+KHCO3"))
    print("-"*66)
    for m,x in zip(pres,R):
        p=x["CO2"][0]
        c1,_,_ = variant(x, False, False)
        c2,_,_ = variant(x, True , False)
        c3,_,_ = variant(x, True , True)
        pcv=lambda v: 100*(v-p)/p
        print("%6.2f %11.5f %12.2f%% %12.2f%% %12.2f%%" % (m,p,pcv(c1),pcv(c2),pcv(c3)))
    print()
