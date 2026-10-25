# -*- coding: utf-8 -*-
"""make_inputs.py —— 生成 PHREEQC 输入文件

主线: 用 EQUILIBRIUM_PHASES 直接规定平衡 CO2 分压 (用户确认的压力口径),
      气相给足余量以保证边界总是可达, 不再需要"用邻近算例替换"。
对照: 定容充气压力工况 (先由容器碳守恒外层解出平衡分压, 再用同样方式定住)。
"""
import os, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG  = os.path.dirname(HERE)
IN   = os.path.join(PKG, "input")

GAUGE = [0.00, 0.10, 0.25, 0.50, 1.00, 1.50, 2.00]   # 表压 MPa
ATM_MPA = 0.101325
P_ATM   = 1.0          # 当地大气压 (atm)
H2O_ATM = 0.03106      # 25 C 水蒸气分压 (atm)
GAS_MOLES = 100.0      # 气相余量, 保证边界可达

NITRITE = """SOLUTION_MASTER_SPECIES
    Nti NtiO2- 0 Nti 14.0067
SOLUTION_SPECIES
    NtiO2- = NtiO2-
        -gamma 3 0
        -Vm 5.5864 5.859 3.4472 -3.0212 1.1847
    NtiO2- + H+ = HNtiO2
        -log_k 3.16
"""

SELECTED = """SELECTED_OUTPUT 1
    -file {tsv}
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

def p_co2_atm(gauge_mpa):
    """给定表压, 返回平衡时的 CO2 分压 (atm)"""
    return (P_ATM + gauge_mpa / ATM_MPA) - H2O_ATM

def build_cases(cases, tsv):
    """cases: [(title, gauge_mpa, p_co2_atm)]"""
    L = [NITRITE if False else "", SELECTED.format(tsv="output/"+tsv)]
    for i, (title, gauge, pco2) in enumerate(cases, 1):
        p_abs = P_ATM + gauge / ATM_MPA
        L.append("""TITLE {t}
SOLUTION {i}
    temp 25
    pressure 1
    units mol/L
    pH 8.3
    K {k}
    Alkalinity 0.2 as HCO3
{nit}    -water 1
REACTION_PRESSURE {i}
    {pabs:.16g}
EQUILIBRIUM_PHASES {i}
    CO2(g) {lg:.16g} {gm}
    -force_equality true
END
""".format(t=title, i=i, k="{k}", nit="{nit}", pabs=p_abs,
           lg=math.log10(pco2), gm=GAS_MOLES))
    return "\n".join(L)

def write_main():
    cases = []
    for g in GAUGE:
        cases.append(("gauge=%g MPa" % g, g, p_co2_atm(g)))
    body = build_cases(cases, "equilibrium_co2.tsv")
    body = body.replace("{k}", "0.2").replace("{nit}", "")
    open(os.path.join(IN, "equilibrium_co2.pqi"), "w", encoding="utf-8", newline="\n").write(body)

def write_kno2():
    cases = []
    for g in GAUGE:
        cases.append(("gauge=%g MPa KNO2" % g, g, p_co2_atm(g)))
    body = build_cases(cases, "equilibrium_co2_kno2.tsv")
    body = body.replace("{k}", "0.22").replace("{nit}", "    Nti 0.02\n")
    body = NITRITE + body
    open(os.path.join(IN, "equilibrium_co2_kno2.pqi"), "w", encoding="utf-8", newline="\n").write(body)

if __name__ == "__main__":
    os.makedirs(IN, exist_ok=True)
    write_main()
    write_kno2()
    print("已生成:")
    for f in sorted(os.listdir(IN)):
        print("   input/%-32s %6d B" % (f, os.path.getsize(os.path.join(IN, f))))
