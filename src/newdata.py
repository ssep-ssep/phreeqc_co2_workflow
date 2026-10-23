# -*- coding: utf-8 -*-
"""新报告数据层: 从 PHREEQC 输出 + 解析模块 汇总全部 13 个算例"""
import re, sys, math, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
import os
from config import OUT as _OUT, SRC as _SRC
B=_OUT
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
se=load("se", os.path.join(_SRC,"khbco3_sealed.py"))
an=load("an", os.path.join(_SRC,"khbco3_pH_analytic.py"))

KH=1.70e-3
R=0.6; RT=0.082057*298.15
MPA2ATM=1/0.101325; PATM=1.0; PH2O=0.03106
GAUGE=[0.10,0.25,0.50,1.00,1.50,2.00]
SPEC=[("CO2",r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("D2",r"^\s+\(CO2\)2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("H1",r"^\s+HCO3-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("H3",r"^\s+CO3-2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("KH",r"^\s+KHCO3\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("OH",r"^\s+OH-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
      ("H", r"^\s+H\+\s+([\d.eE+-]+)\s+([\d.eE+-]+)")]

txt=open(os.path.join(B,"final2_out.txt"),encoding="utf-8",errors="ignore").read()
parts=re.split(r"Initial solution (\d+)\.",txt)
S=[]
for i in range(1,len(parts),2):
    b=parts[i+1]; d={}
    for k,pat in SPEC:
        m=re.findall(pat,b,re.M)
        if m: d[k]=(float(m[-1][0]),float(m[-1][1]))
    ph=re.findall(r"([\d.]+)\s+Charge balance",b)
    pg=re.findall(r"CO2\(g\).*?Pressure\s+([\d.]+)",b)
    tt=re.findall(r"Total CO2 \(mol/kg\)\s+=\s+([\d.eE+-]+)",b)
    if ph and d:
        d["pH"]=float(ph[-1]); d["pCO2"]=float(pg[-1]) if pg else 0.0
        d["TOT"]=float(tt[-1]) if tt else None
        S.append(d)

def enrich(d):
    # H2CO3 已由 PHREEQC 合并进表观物种 CO2*; 此处只作拆分比例参考, 不再计入总碳
    d["H2"]=d["CO2"][0]*KH
    # 总无机碳 = 物种和 (含 (CO2)2 的两个碳), 与 PHREEQC 的 "Total CO2" 一致
    # 总无机碳 = 物种和 (含 (CO2)2 的两个碳); 不再额外计入 H2CO3 (已并入表观 CO2*)
    # 用物种和而非 PHREEQC 打印的 "Total CO2", 因后者只有 4 位有效数字
    d["DIC"]=d["CO2"][0]+d["H1"][0]+d["H3"][0]+d["KH"][0]+2*d["D2"][0]
    d["Alk"]=d["H1"][0]+2*d["H3"][0]+d["OH"][0]-d["H"][0]
    return d
for d in S: enrich(d)

# 解析校核
def recon(d, Ka1a, Ka2):
    aH=d["H"][1]
    g1=10**math.log10(d["H1"][1]/d["H1"][0])
    g0=10**math.log10(d["CO2"][1]/d["CO2"][0])
    g2=10**math.log10(d["H3"][1]/d["H3"][0])
    CT=d["CO2"][0]+d["H1"][0]+d["H3"][0]
    lo,hi=1e-8,0.5
    for _ in range(300):
        mid=(lo+hi)/2
        f=(aH*mid/Ka1a)/g0+mid/g1+(Ka2*mid/aH)/g2-CT
        if f<0: lo=mid
        else: hi=mid
    ah=(lo+hi)/2
    return (aH*ah/Ka1a)/g0, ah/g1, (Ka2*ah/aH)/g2

def analytic_const(P_atm):
    return an.pH_open(298.15, P_atm*0.101325, True, True)["pH"]
def analytic_sealed(P0_atm):
    r = se.solve(P0_atm, R)
    return r[0] if isinstance(r, tuple) else r

GRP1=[S[0]]
GRP2=[S[7+k] for k in range(6)]   # 定容-充气
GRP3=[S[1+k] for k in range(6)]   # 定容-平衡
ABS={g: g*MPA2ATM+PATM for g in GAUGE}

def rows(gauge_list, case_list, mode):
    out=[]
    for k,g in enumerate(gauge_list):
        d=case_list[k]
        if mode=="charge":
            pH_an = analytic_sealed(ABS[g])
        else:
            pH_an = analytic_const(ABS[g])
        K1a=d["H"][1]*d["H1"][1]/d["CO2"][1]
        K2a=d["H"][1]*d["H3"][1]/d["H1"][1]
        c2n,_,_=recon(d,10**-6.351,10**-10.329)
        c2r,h1r,h3r=recon(d,K1a,K2a)
        out.append(dict(g=g, Pabs=ABS[g], pCO2=d["pCO2"], pH=d["pH"],
            pH_an=pH_an, DIC=d["DIC"], CO2=d["CO2"][0], H1=d["H1"][0],
            H3=d["H3"][0], KHc=d["KH"][0], D2=d["D2"][0], H2=d["H2"],
            Alk=d["Alk"], c2n=c2n, c2r=c2r, h1r=h1r, h3r=h3r))
    return out

if __name__=="__main__":
    for nm,cs,md in [("组1 恒压",GRP1,"const"),("组2 定容-充气",GRP2,"charge"),("组3 定容-平衡",GRP3,"const")]:
        print("=== %s ===" % nm)
        for g,d in zip([0.0] if cs is GRP1 else GAUGE, cs):
            Pa = PATM if cs is GRP1 else ABS[g]
            pHan = analytic_const(Pa) if md=="const" else analytic_sealed(Pa)
            print("  g=%4.2f  Pabs=%6.3f atm  pCO2=%6.3f  pH=%6.3f  解析=%6.3f  d=%+.3f  DIC=%.5f  CO2*=%.5f"
                  % (g, Pa, d["pCO2"], d["pH"], pHan, d["pH"]-pHan, d["DIC"], d["CO2"][0]))
