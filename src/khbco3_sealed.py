# -*- coding: utf-8 -*-
"""
khbco3_sealed.py —— 定容密封体系的独立解析解 (不依赖 PHREEQC)

刚性容器: V_L 液体 + r*V_L 顶空, 初始充纯 CO2 至 P0 (atm), 密封后达平衡。

容器碳守恒:
    0.2*V_L + P0*V_G/(RT) = DIC*V_L + P_eq*V_G/(RT)
  =>  DIC = 0.2 + (P0 - P_eq)*r/(RT),     r = V_G/V_L

电荷平衡 (总 K+ = k_kgw):
    [K+] = [HCO3-] + 2[CO3--] + [OH-] - [H+]

碳酸平衡:
    a_CO2  = KH * phi(P_eq) * P_eq        (亨利定律 + Peng-Robinson 逸度)
    a_HCO3 = Ka1 * a_CO2 / a_H
    a_CO3  = Ka2 * a_HCO3 / a_H

离子强度 I 由物种电荷迭代求出 (不用碱度代替); 基准 mol/kg water。
修正记录 (2026-10-24 代码审查): I 原固定为 0.2, 现由物种电荷实时迭代。
"""
import math
import khbco3_pH_analytic as A

T_C   = 25.0
Ka1, Ka2, Kw, KH = 4.45e-7, 4.69e-11, 1.0e-14, 0.0340   # 25 C
RT = 0.082057 * 298.15          # L atm / mol
ATM_PER_MPA = 1.0 / 0.101325
DEBYE_A = 0.5092

def _gamma(z, I):
    s = math.sqrt(I)
    return 10.0 ** (-DEBYE_A * z * z * (s / (1 + s) - 0.3 * I))

def speciate(a_co2, alk_kgw=0.2, k_kgw=None, nitrite=0.0):
    """给定 a_CO2, 由电荷平衡解 a_H, 返回 (a_H, DIC, I)"""
    if k_kgw is None:
        k_kgw = alk_kgw
    I = max(alk_kgw, 1e-6)
    for _ in range(200):
        g1, g2 = _gamma(1, I), _gamma(2, I)
        def resid(aH):
            H    = aH/g1
            OH   = Kw/aH/g1
            HCO3 = Ka1*a_co2/aH/g1
            CO3  = Ka2*Ka1*a_co2/(aH*aH)/g2
            no2  = nitrite/(1 + aH*g1/10**-3.16) if nitrite else 0.0
            return (k_kgw + H) - (HCO3 + 2*CO3 + OH + no2)
        aH = 1e-7
        for _ in range(400):
            d = 1e-14
            c0, c1 = resid(aH), resid(aH+d)
            aH = max(aH - c0*d/(c1-c0), 1e-14)
        H    = aH/g1
        OH   = Kw/aH/g1
        HCO3 = Ka1*a_co2/aH/g1
        CO3  = Ka2*Ka1*a_co2/(aH*aH)/g2
        I_new = 0.5*(k_kgw + H + OH + HCO3 + 4*CO3)
        if abs(I_new - I) < 1e-13:
            I = I_new; break
        I = 0.5*(I_new + I)
    return aH, HCO3 + CO3 + a_co2, I

def solve(P0, r, alk_kgw=0.2, k_kgw=None, nitrite=0.0):
    """P0 初始 CO2 分压 (atm); r = V_G/V_L; 返回 (pH, P_eq)"""
    def aCO2_of(P):
        return KH * A.pr_phi(298.15, P) * P
    def F(P):
        _, DIC, _ = speciate(aCO2_of(P), alk_kgw, k_kgw, nitrite)
        return (DIC - 0.2) * RT / r + P - P0
    lo, hi = 1e-12, P0
    if F(hi) < 0:
        return None
    for _ in range(200):
        m = math.sqrt(lo*hi)
        if F(m) > 0: hi = m
        else:        lo = m
    P = math.sqrt(lo*hi)
    aH, _, _ = speciate(aCO2_of(P), alk_kgw, k_kgw, nitrite)
    return -math.log10(aH), P

if __name__ == "__main__":
    print("定容密封体系 (含 Peng-Robinson 逸度修正), 25 C")
    PRESS_MPA = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0]
    RATIOS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
    print("%-10s|%s" % ("V_G/V_L", "".join("%8.2f" % m for m in PRESS_MPA)))
    print("-" * 70)
    for r in RATIOS:
        print("%-10s|%s" % (r, "".join("%8.3f" % solve(m*ATM_PER_MPA, r)[0] for m in PRESS_MPA)))
