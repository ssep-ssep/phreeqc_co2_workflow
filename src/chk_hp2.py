# -*- coding: utf-8 -*-
import re, sys, math
sys.stdout.reconfigure(encoding="utf-8")
import os
from config import OUT as B
txt=open(os.path.join(B,"hp_fine_out.txt"),encoding="utf-8",errors="ignore").read()
parts=re.split(r"Initial solution (\d+)\.",txt)
print("%4s %8s %10s %10s %9s %8s %9s"
      % ("解","pCO2atm","m_CO2","a_CO2","DIC","pH","隐含KHphi"))
print("-"*66)
for i in range(1,len(parts),2):
    b=parts[i+1]
    pg=re.findall(r"CO2\(g\).*?Pressure\s+([\d.]+)",b)
    m=re.findall(r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)",b,re.M)
    tot=re.findall(r"Total CO2 \(mol/kg\)\s+=\s+([\d.eE+-]+)",b)
    ph=re.findall(r"([\d.]+)\s+Charge balance",b)
    if not (pg and m): continue
    p=float(pg[-1]); c2=float(m[-1][0]); a2=float(m[-1][1])
    print("%4s %8.2f %10.5f %10.5f %9.5f %8.3f %9.5f"
          % (parts[i], p, c2, a2, float(tot[-1]), float(ph[-1]), a2/p))
print()
def pr_phi(T,Pbar):
    Tc,Pc,w=304.1282,73.773,0.22394
    Tr,Pr=T/Tc,Pbar/Pc
    kap=0.37464+1.54226*w-0.26992*w*w
    al=(1+kap*(1-math.sqrt(Tr)))**2
    Aa=al*0.45724*Pr/Tr/Tr; Bb=0.07780*Pr/Tr
    c2v,c1v,c0v=-(1-Bb),Aa-3*Bb*Bb-2*Bb,-(Aa*Bb-Bb*Bb-Bb**3)
    z=1.0
    for _ in range(200):
        f=z**3+c2v*z*z+c1v*z+c0v; df=3*z*z+2*c2v*z+c1v; z-=f/df
    s2=math.sqrt(2)
    return math.exp((z-1)-math.log(z-Bb)-Aa/(2*s2*Bb)*math.log((z+(1+s2)*Bb)/(z+(1-s2)*Bb)))
print("理论 KH*phi (亨利 0.034 x PR逸度):")
for p in [19,20,20.3,20.5,20.7,21,21.5,22]:
    print("  %5.2f atm -> %.5f" % (p, 0.034*pr_phi(298.15, p*1.01325)))
