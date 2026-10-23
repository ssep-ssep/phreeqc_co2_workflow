# -*- coding: utf-8 -*-
"""生成新版报告 (三组结构)"""
import sys, re, math, os, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
import os
from config import SRC
exec(open(os.path.join(SRC,"build_docx.py"), encoding="utf-8").read())
exec(open(os.path.join(SRC,"newdata.py"), encoding="utf-8").read())

# --- 取高压段的稳定解 (hp_fine 中 20.70 atm 独立算例) ---
def load_blocks(fn):
    t=open(B+"\\"+fn,encoding="utf-8",errors="ignore").read()
    parts=re.split(r"Initial solution (\d+)\.",t)
    out=[]
    for i in range(1,len(parts),2):
        b=parts[i+1]; d={}
        for k,pat in SPEC:
            m=re.findall(pat,b,re.M)
            if m: d[k]=(float(m[-1][0]),float(m[-1][1]))
        ph=re.findall(r"([\d.]+)\s+Charge balance",b)
        pg=re.findall(r"CO2\(g\).*?Pressure\s+([\d.]+)",b)
        if ph and d:
            d["pH"]=float(ph[-1]); d["pCO2"]=float(pg[-1]) if pg else 0.0
            out.append(enrich(d))
    return out
hf=load_blocks("hp_fine_out.txt")
stable=[d for d in hf if abs(d["pCO2"]-20.70)<0.02][0]
GRP3[5]=stable                       # 组3 最后一档改用稳定解
print("组3 2.00MPa 改用稳定解: pH=%.3f DIC=%.5f CO2*=%.5f (原 %.3f/%.5f/%.5f)"
      % (stable["pH"],stable["DIC"],stable["CO2"][0],
         S[6]["pH"], S[6]["DIC"], S[6]["CO2"][0]))

def rows(group, gauges, mode):
    out=[]
    for k,g in enumerate(gauges):
        d=group[k]
        pHan = analytic_const(ABS[g]) if mode=="const" else analytic_sealed(ABS[g])
        K1a=d["H"][1]*d["H1"][1]/d["CO2"][1]; K2a=d["H"][1]*d["H3"][1]/d["H1"][1]
        c2r,h1r,h3r=recon(d,K1a,K2a)
        out.append(dict(g=g,Pabs=ABS[g],pCO2=d["pCO2"],pH=d["pH"],pHan=pHan,
                        DIC=d["DIC"],CO2=d["CO2"][0],H1=d["H1"][0],H3=d["H3"][0],
                        KHc=d["KH"][0],D2=d["D2"][0],H2=d["H2"],Alk=d["Alk"],
                        c2r=c2r,h1r=h1r,h3r=h3r))
    return out
ABS[0.0]=PATM
R1=rows(GRP1,[0.0],"const")
R2=rows(GRP2,GAUGE,"charge")
R3=rows(GRP3,GAUGE,"const")
P3=f3=lambda xs:["%.3f"%x for x in xs]
PM2=["%.2f"%g for g in GAUGE]
