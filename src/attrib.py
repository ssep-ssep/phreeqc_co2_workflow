# -*- coding: utf-8 -*-
"""attrib.py —— CO2* 偏差归因: 络合物 vs 平衡常数取值口径"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import co2_model as M

Ka1a, Ka2 = 10**-6.351, 10**-10.329

def variant(d, use_d, use_kh):
    """在质量衡算中分别计入/不计入 (CO2)2 与 KHCO3, 观察 CO2* 反算值的偏移"""
    aH = d["H"][1]
    g1 = 10**math.log10(d["H1"][1]/d["H1"][0])
    g0 = 10**math.log10(d["CO2"][1]/d["CO2"][0])
    g2 = 10**math.log10(d["H3"][1]/d["H3"][0])
    CT = d["CO2"][0]+d["H1"][0]+d["H3"][0]
    if use_d:  CT += 2*d["D2"][0]
    if use_kh: CT += d["KH"][0]
    lo, hi = 1e-8, 0.5
    for _ in range(300):
        mid = (lo+hi)/2
        f = (aH*mid/Ka1a)/g0 + mid/g1 + (Ka2*mid/aH)/g2 - CT
        if f < 0: lo = mid
        else:     hi = mid
    ah = (lo+hi)/2
    return (aH*ah/Ka1a)/g0

S = M.parse_file(os.path.join(M.OUT, "final2_out.txt"))
print("="*92)
print("  CO2* 反算偏差归因")
print("  路径 1: 质量衡算只含三个主要物种 (CO2*, HCO3-, CO3(2-))")
print("  路径 2: 再计入 (CO2)2 的两个碳")
print("  路径 3: 再计入 KHCO3")
print("="*92)
print("%6s %10s %12s %12s %12s" % ("pCO2", "PHREEQC", "路径1", "路径2", "路径3"))
print("-"*60)
for d in S:
    if d["pCO2"] < 0.5: continue
    print("%6.2f %10.5f %12.5f %12.5f %12.5f"
          % (d["pCO2"], d["CO2"][0],
             variant(d, False, False), variant(d, True, False), variant(d, True, True)))
print()
print("结论: 三个路径之间几乎无差别 -> CO2* 的偏差不来自络合物, 而来自平衡常数口径 (见 chk_const.py)")
