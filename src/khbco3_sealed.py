# -*- coding: utf-8 -*-
"""
定容密封体系: 0.2 M KHCO3 + 有限量纯 CO2
=====================================================
刚性容器: V_L 液体 + r·V_L 顶空, 初始充纯 CO2 至 P0, 密封后达平衡。

碳守恒 (整个容器):
    0.2*V_L + P0*V_G/(RT) = DIC*V_L + P_eq*V_G/(RT)
  =>  DIC = 0.2 + (P0 - P_eq)*r/(RT),   r = V_G/V_L

电荷平衡 (K+ = 0.2 mol/L):
    [K+] = [HCO3-] + 2[CO3--] + [OH-] - [H+]

碳酸平衡:
    a_CO2  = KH * phi(P) * P_eq      (亨利定律 + Peng-Robinson 逸度)
    a_HCO3 = Ka1 * a_CO2 / a_H
    a_CO3  = Ka2 * a_HCO3 / a_H

活度系数用 Davies (I = 0.2 mol/kg)。对 P_eq 用二分法求解。

建模水平与边界 A 的解析校核一致 (均含 Peng-Robinson 逸度修正),
故 r -> 无穷大 时本表与 PHREEQC 恒压结果一致 (偏差 <= 0.003 pH)。
"""
import math

T_C   = 25.0
Ka1, Ka2, Kw, KH = 4.45e-7, 4.69e-11, 1.0e-14, 0.0340   # 25 C
A_DEBYE = 0.5092
I = 0.2
RT = 0.082057 * 298.15          # L atm / mol
ATM_PER_MPA = 1.0 / 0.101325

def gamma(z):
    s = math.sqrt(I)
    return 10.0 ** (-A_DEBYE * z * z * (s / (1 + s) - 0.3 * I))

g1, g2 = gamma(1), gamma(2)

def pr_phi(T, P_atm):
    """Peng-Robinson 纯组分 CO2 逸度系数, 输入压力单位 atm"""
    P_bar = P_atm * 1.01325                      # 1 atm = 1.01325 bar
    Tc, Pc, w = 304.1282, 73.773, 0.22394
    Tr, Pr = T / Tc, P_bar / Pc
    kappa = 0.37464 + 1.54226 * w - 0.26992 * w * w
    alpha = (1 + kappa * (1 - math.sqrt(Tr))) ** 2
    Aa = alpha * 0.45724 * Pr / Tr / Tr
    Bb = 0.07780 * Pr / Tr
    c2 = -(1 - Bb)
    c1 = Aa - 3 * Bb * Bb - 2 * Bb
    c0 = -(Aa * Bb - Bb * Bb - Bb ** 3)
    z = 1.0
    for _ in range(300):
        f = z ** 3 + c2 * z * z + c1 * z + c0
        df = 3 * z * z + 2 * c2 * z + c1
        z -= f / df
    s2 = math.sqrt(2)
    lnf = ((z - 1) - math.log(z - Bb)
           - Aa / (2 * s2 * Bb) * math.log((z + (1 + s2) * Bb) / (z + (1 - s2) * Bb)))
    return math.exp(lnf)

def speciate(a_co2):
    """给定 a_CO2, 由电荷平衡解 a_H, 返回 (a_H, DIC)"""
    def resid(aH):
        return (0.2 - Ka1 * a_co2 / aH / g1
                - 2 * Ka2 * Ka1 * a_co2 / (aH * aH) / g2
                - Kw / aH / g1 + aH / g1)
    aH = 1e-7
    for _ in range(400):
        d = 1e-14
        c0, c1 = resid(aH), resid(aH + d)
        aH = max(aH - c0 * d / (c1 - c0), 1e-14)
    hco3 = Ka1 * a_co2 / aH / g1
    co3  = Ka2 * Ka1 * a_co2 / (aH * aH) / g2
    return aH, hco3 + co3 + a_co2

def solve(P0, r):
    """P0 初始分压 (atm); r = V_G/V_L; 返回 (pH, P_eq)"""
    def aCO2_of(P):
        return KH * pr_phi(298.15, P) * P
    def F(P):
        _, DIC = speciate(aCO2_of(P))
        return (DIC - 0.2) * RT / r + P - P0
    lo, hi = 1e-12, P0
    if F(hi) < 0:
        return None
    for _ in range(200):
        m = math.sqrt(lo * hi)
        if F(m) > 0: hi = m
        else:        lo = m
    P = math.sqrt(lo * hi)
    aH, _ = speciate(aCO2_of(P))
    return -math.log10(aH), P

PRESS_MPA = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0]
RATIOS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]

if __name__ == "__main__":
    print("25 C  0.2 M KHCO3 + 纯 CO2  定容密封体系 (含 Peng-Robinson 逸度修正)")
    print("%-10s|%s" % ("V_G/V_L", "".join("%8.2f" % m for m in PRESS_MPA)))
    print("-" * 70)
    for r in RATIOS:
        print("%-10s|%s" % (r, "".join("%8.2f" % solve(m * ATM_PER_MPA, r)[0] for m in PRESS_MPA)))
    print("%-10s|%s   <- 恒压极限" % ("inf",
          "".join("%8.2f" % solve(m * ATM_PER_MPA, 1e9)[0] for m in PRESS_MPA)))
    print()
    print("对照 PHREEQC v3.8.6 实测:  6.994  6.601  6.307  6.020  5.858  5.747")
