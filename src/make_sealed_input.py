# -*- coding: utf-8 -*-
"""
make_sealed_input.py —— 生成定容"充气压力"对照工况的输入

给定充气压力 P0 (表压) 与气液比 r, 由容器碳守恒解出平衡 CO2 分压:

    C_final(p) = C_init + (P0 - p) * r * V_liq(p) / (R T)

C_init 取自主线算例的初始解; DIC(p) 与 V_liq(p) 由主线算例插值。
外层解用迭代收敛: 每轮用 PHREEQC 实际算出的 (p, DIC) 作为新锚点,
使容器碳守恒残差降到 1e-6 mol/kg water 量级。
"""
import os, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import co2_model as M

IN   = os.path.join(M.PKG, "input")
GAUGE_CHARGE = [0.10, 0.25, 0.50, 1.00, 1.50, 2.00]

SELECTED = """SELECTED_OUTPUT 1
    -file output/sealed_charge.tsv
    -high_precision true
    -reset false
    -simulation true
    -solution true
    -state true
    -pH true
    -alkalinity true
    -ionic_strength true
    -water true
    -charge_balance true
    -percent_error true
    -totals C K Nti
    -molalities CO2 HCO3- CO3-2 KHCO3 (CO2)2 H+ OH- NtiO2- HNtiO2
    -activities H+ CO2 HCO3- CO3-2
    -equilibrium_phases CO2(g)
    -saturation_indices CO2(g)
USER_PUNCH 1
    -headings solution_volume_L water_activity phi_CO2 inferred_pCO2_atm
    -start
    10 phi = PR_PHI("CO2(g)")
    20 IF phi <= 0 THEN phi = 1
    30 PUNCH SOLN_VOL, ACT("H2O"), phi, 10^SI("CO2(g)")/phi
    -end
"""

NITRITE_DEF = """SOLUTION_MASTER_SPECIES
    Nti NtiO2- 0 Nti 14.0067
SOLUTION_SPECIES
    NtiO2- = NtiO2-
        -gamma 3 0
        -Vm 5.5864 5.859 3.4472 -3.0212 1.1847
    NtiO2- + H+ = HNtiO2
        -log_k 3.16
"""

def _interp(xs, ys, x):
    if x <= xs[0]:  return ys[0]
    if x >= xs[-1]: return ys[-1]
    for i in range(len(xs)-1):
        if xs[i] <= x <= xs[i+1]:
            f = (x-xs[i])/(xs[i+1]-xs[i])
            return ys[i] + f*(ys[i+1]-ys[i])

class Curve(object):
    """DIC(p) 与 V_liq(p) 的插值曲线, 锚点可增量加入"""

    def __init__(self, cases):
        self.pts = [(c.p_co2_atm, c.totals["C"], c.soln_vol_L/c.mass_H2O) for c in cases]
        self.pts.sort()

    def add(self, p, C, V):
        self.pts = [q for q in self.pts if abs(q[0]-p) > 1e-9]
        self.pts.append((p, C, V))
        self.pts.sort()

    def C(self, p):
        return _interp([q[0] for q in self.pts], [q[1] for q in self.pts], p)

    def V(self, p):
        return _interp([q[0] for q in self.pts], [q[2] for q in self.pts], p)

def solve_p_eq(curve, P0, ratio, init_C):
    lo, hi = 1e-6, P0
    for _ in range(300):
        mid = 0.5*(lo+hi)
        f  = curve.C(mid) - init_C - (P0-mid)*ratio*curve.V(mid)/M.R_GAS
        f0 = curve.C(lo)  - init_C - (P0-lo) *ratio*curve.V(lo) /M.R_GAS
        if f0*f <= 0: hi = mid
        else:        lo = mid
    return 0.5*(lo+hi)

def write(curve, init_C, gauges=None, nitrite=0.0):
    gauges = gauges or GAUGE_CHARGE
    L = [SELECTED]
    peqs = []
    for i, g in enumerate(gauges, 1):
        p_abs = M.P_ATM + g/M.ATM_MPA
        P0    = p_abs
        p_eq  = solve_p_eq(curve, P0, M.RATIO, init_C)
        peqs.append((g, P0, p_eq))
        L.append("""TITLE 充气表压={g} MPa
SOLUTION {i}
    temp 25
    pressure 1
    units mol/L
    pH 8.3
    K {k}
    Alkalinity 0.2 as HCO3
{nit}    -water 1
REACTION_PRESSURE {i}
    {p_abs:.16g}
EQUILIBRIUM_PHASES {i}
    CO2(g) {lg:.16g} 100
    -force_equality true
END
""".format(g=g, i=i, k="{k}", nit="{nit}", p_abs=p_abs, lg=math.log10(p_eq)))
    body = "\n".join(L)
    body = body.replace("{k}", "0.22" if nitrite else "0.2")
    body = body.replace("{nit}", "    Nti 0.02\n" if nitrite else "")
    if nitrite:
        body = NITRITE_DEF + body
    path = os.path.join(IN, "sealed_charge.pqi")
    open(path, "w", encoding="utf-8", newline="\n").write(body)
    return path, peqs

if __name__ == "__main__":
    cases = M.load_case("equilibrium_co2.tsv")
    init = M.load_initial("equilibrium_co2.tsv")
    init_C = float(init[0]["C"])
    curve = Curve(cases)
    p, peqs = write(curve, init_C)
    print("已生成 %s (%d B)" % (p, os.path.getsize(p)))
    for g, P0, pe in peqs:
        print("   充气表压 %4.2f MPa -> P0 %7.3f atm -> 平衡分压 %7.4f atm" % (g, P0, pe))
