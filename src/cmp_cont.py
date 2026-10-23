# -*- coding: utf-8 -*-
import re, sys, math
sys.stdout.reconfigure(encoding="utf-8")
import os
from config import OUT as B
def show(fn,tag):
    txt=open(os.path.join(B,fn),encoding="utf-8",errors="ignore").read()
    parts=re.split(r"Initial solution (\d+)\.",txt)
    print("=== %s ===" % tag)
    print("%8s %10s %9s %9s" % ("pCO2 atm","m_CO2","DIC","pH"))
    for i in range(1,len(parts),2):
        b=parts[i+1]
        pg=re.findall(r"CO2\(g\).*?Pressure\s+([\d.]+)",b)
        m=re.findall(r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)",b,re.M)
        tot=re.findall(r"Total CO2 \(mol/kg\)\s+=\s+([\d.eE+-]+)",b)
        ph=re.findall(r"([\d.]+)\s+Charge balance",b)
        if not (pg and m): continue
        print("%8.2f %10.5f %9.5f %9.3f"
              % (float(pg[-1]), float(m[-1][0]), float(tot[-1]), float(ph[-1])))
    print()
show("hp_cont_out.txt","连续化法 SAVE/USE")
show("hp_fine_out.txt","独立算例 (对照)")
