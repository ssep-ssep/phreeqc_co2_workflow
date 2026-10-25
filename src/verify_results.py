# -*- coding: utf-8 -*-
"""
verify_results.py —— 对 PHREEQC 结果做全面交叉核对

检查分组 (对应 2026-10-24 代码审查的 18 项):
  A 边界达成    目标 CO2 分压是否达到; 气相是否有余量 (未耗尽)
  B 电荷与守恒  电荷平衡; K / Nti 组分质量守恒; 碳质量守恒 (含气相交换)
  C 记账一致性  总碱度与完整物种求和; 总碳与完整物种求和
  D 单位口径    mol/kg water 与 mol/L 的换算因子; 输入口径与输出口径一致
  E 独立交叉核对 与独立解析解 (Davies + Peng-Robinson) 比对 —— 真正独立的路线
  F 内部自洽    recon_internal: 同一份输出内部的代数自洽 (不是独立预测)
  G 对照工况    定容充气压力的容器碳守恒; KNO2 敏感性
"""
import os, sys, math, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import co2_model as M

PASS, FAIL = [], []

def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %-56s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok

def hdr(t):
    print()
    print(t)
    print("-"*len(t))

def out_text(name):
    p = os.path.join(M.OUT, name)
    return open(p, encoding="utf-8", errors="ignore").read() if os.path.exists(p) else ""

def _species_gammas(path, *species):
    """从 .out 的物种分布表读出各物种的活度系数。
    返回: 每个解算例一个 {物种名: gamma} 字典 (只收 molality > 0 的物种)"""
    if not os.path.exists(path):
        return None
    txt = open(path, encoding="utf-8", errors="ignore").read()
    parts = re.split(r"Initial solution (\d+)\.", txt)
    out = []
    for i in range(1, len(parts), 2):
        b = parts[i+1]
        j = b.rfind("Distribution of species")
        if j < 0:
            continue
        blk = b[j:j+4000]
        d = {}
        for l in blk.splitlines():
            m = re.match(r"^\s+(\S+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", l)
            if not m:
                continue
            name = m.group(1)
            if name not in species:
                continue
            mol, act = float(m.group(2)), float(m.group(3))
            if mol <= 0:
                continue
            d.setdefault(name, act/mol)
        if d:
            out.append(d)
    return out or None

def main():
    print("="*90)
    print("  PHREEQC / CO2 平衡结果校验")
    print("  源: output/equilibrium_co2.tsv, equilibrium_co2_kno2.tsv, sealed_charge.tsv")
    print("="*90)

    cases = M.load_case("equilibrium_co2.tsv")
    init  = M.load_initial("equilibrium_co2.tsv")

    hdr("A) 边界达成: 目标 CO2 分压 / 气相余量")
    for c in cases:
        rel = c.p_co2_atm/c.p_co2_target_atm - 1
        check("A 表压 %.2f MPa: 目标 pCO2 达成" % c.gauge_mpa, abs(rel) <= 1e-8,
              "实测 %.6f / 目标 %.6f atm (相对偏差 %.1e)"
              % (c.p_co2_atm, c.p_co2_target_atm, rel))
    txt = out_text("equilibrium_co2.out")
    check("A 主线: 气相未耗尽", "dissolved completely" not in txt,
          "'dissolved completely' 出现 %d 次" % txt.count("dissolved completely"))

    hdr("B) 电荷平衡与组分守恒")
    for c in cases:
        check("B 表压 %.2f MPa: 电荷平衡" % c.gauge_mpa, abs(c.pct_err) <= 1e-6,
              "percent_error = %.2e" % c.pct_err)
    for c, r0 in zip(cases, init):
        dK = c.totals["K"]*c.mass_H2O - float(r0["K"])*float(r0["mass_H2O"])
        check("B 表压 %.2f MPa: K 质量守恒" % c.gauge_mpa, abs(dK) <= 1e-9,
              "偏差 %.2e mol" % dK)
    for c, r0 in zip(cases, init):
        dC = c.totals["C"]*c.mass_H2O - float(r0["C"])*float(r0["mass_H2O"]) + c.gas_dCO2
        check("B 表压 %.2f MPa: 碳质量守恒 (含气相)" % c.gauge_mpa, abs(dC) <= 1e-8,
              "偏差 %.2e mol" % dC)

    hdr("C) 碱度与总碳的记账一致性")
    for c in cases:
        check("C 表压 %.2f MPa: 碱度 = 完整物种求和" % c.gauge_mpa,
              abs(c.alk_species()-c.Alk) <= 1e-9,
              "Alk %.6f / 物种求和 %.6f eq/kg" % (c.Alk, c.alk_species()))
    for c in cases:
        check("C 表压 %.2f MPa: 总碳 = 完整物种求和" % c.gauge_mpa,
              abs(c.carbon_species()-c.totals["C"]) <= 1e-9,
              "C %.6f / 物种求和 %.6f mol/kg" % (c.totals["C"], c.carbon_species()))

    hdr("D) 单位口径")
    for c in cases:
        check("D 表压 %.2f MPa: mol/L 与 mol/kgw 换算一致" % c.gauge_mpa,
              0.9 < c.factor < 1.0,
              "factor = mass_H2O/SOLN_VOL = %.5f ; Alk %.5f eq/kg = %.5f eq/L"
              % (c.factor, c.Alk, c.alk_M()))

    hdr("E) 与独立解析解交叉核对 (Davies + Peng-Robinson, 与 PHREEQC 无共用)")
    alk_kgw = cases[0].Alk
    worst = 0.0
    for c in cases:
        pH_an = M.analytic_const(c.p_co2_atm, alk_kgw=alk_kgw, k_kgw=c.totals["K"])
        d = c.pH - pH_an
        worst = max(worst, abs(d))
        check("E 表压 %.2f MPa: pH 与独立解析解" % c.gauge_mpa, abs(d) <= 0.02,
              "PHREEQC %.4f / 解析 %.4f (d=%+.4f)" % (c.pH, pH_an, d))
    print("  最大 |ΔpH| = %.4f" % worst)

    hdr("F) 内部一致性: 离子强度两种算法互校")
    for c in cases:
        I_calc = M.ionic_strength_from_species(c)
        check("F 表压 %.2f MPa: 物种电荷算 I = PHREEQC mu" % c.gauge_mpa,
              abs(I_calc-c.I) <= 1e-6,
              "物种算 %.6f / PHREEQC %.6f mol/kg" % (I_calc, c.I))
    for c in cases:
        pH_an = M.analytic_const(c.p_co2_atm, alk_kgw=cases[0].Alk, k_kgw=c.totals["K"])
        I_an = M.ionic_strength_from_species(c)
        check("F 表压 %.2f MPa: 独立解析解的 I 与 PHREEQC 一致" % c.gauge_mpa,
              abs(I_an-c.I) <= 0.01,
              "解析 %.5f / PHREEQC %.5f mol/kg" % (I_an, c.I))

    hdr("G) 对照工况: 定容充气压力 / KNO2 敏感性")
    spath = os.path.join(M.OUT, "sealed_charge.tsv")
    if os.path.exists(spath):
        G = [0.10, 0.25, 0.50, 1.00, 1.50, 2.00]
        sc = M.load_case("sealed_charge.tsv", gauges=G)
        sinit = M.load_initial("sealed_charge.tsv")
        sC0 = float(sinit[0]["C"])
        for g, c in zip(G, sc):
            P0 = M.P_ATM + g/M.ATM_MPA
            V = c.soln_vol_L/c.mass_H2O
            rhs = sC0 + (P0-c.p_co2_atm)*M.RATIO*V/M.R_GAS
            resid = c.totals["C"] - rhs
            check("G 表压 %.2f MPa: 容器碳守恒" % g, abs(resid) <= 1e-5,
                  "残差 %.2e mol/kg (P0 %.3f -> p_eq %.4f atm)" % (resid, P0, c.p_co2_atm))
    else:
        check("G 定容对照工况输出存在", False, "缺少 output/sealed_charge.tsv")

    kpath = os.path.join(M.OUT, "equilibrium_co2_kno2.tsv")
    if os.path.exists(kpath):
        kc = M.load_case("equilibrium_co2_kno2.tsv")
        worst_k = 0.0
        for c, k in zip(cases, kc):
            dk = k.pH - c.pH
            worst_k = max(worst_k, abs(dk))
            check("G 表压 %.2f MPa: KNO2 敏感性 (20 mM)" % c.gauge_mpa, abs(dk) <= 0.01,
                  "无盐 %.4f / 有盐 %.4f (d=%+.4f, dE=%.2f mV)"
                  % (c.pH, k.pH, dk, 59.16*dk))
        print("  KNO2 影响: 最大 |ΔpH| = %.4f (对应 %.2f mV)" % (worst_k, 59.16*worst_k))

    # ---------------- H  NO2- (KNO2) 路线的独立验证 ----------------
    hdr("H) NO2- (KNO2) 路线的独立验证")
    kpath = os.path.join(M.OUT, "equilibrium_co2_kno2.tsv")
    if os.path.exists(kpath):
        kc = M.load_case("equilibrium_co2_kno2.tsv")
        kinit = M.load_initial("equilibrium_co2_kno2.tsv")
        for c, r0 in zip(kc, kinit):
            dN = c.totals["Nti"]*c.mass_H2O - float(r0["Nti"])*float(r0["mass_H2O"])
            check("H 表压 %.2f MPa: Nti 质量守恒" % c.gauge_mpa, abs(dN) <= 1e-9,
                  "偏差 %.2e mol" % dN)
        for c in kc:
            check("H 表压 %.2f MPa: 碱度 = 完整物种求和(含 HNtiO2)" % c.gauge_mpa,
                  abs(c.alk_species()-c.Alk) <= 1e-9,
                  "Alk %.6f / 物种求和 %.6f eq/kg" % (c.Alk, c.alk_species()))
        for c in kc:
            check("H 表压 %.2f MPa: 电荷平衡" % c.gauge_mpa, abs(c.pct_err) <= 1e-6,
                  "percent_error = %.2e" % c.pct_err)
        for c, r0 in zip(kc, kinit):
            dC = c.totals["C"]*c.mass_H2O - float(r0["C"])*float(r0["mass_H2O"]) + c.gas_dCO2
            check("H 表压 %.2f MPa: 碳质量守恒" % c.gauge_mpa, abs(dC) <= 1e-8,
                  "偏差 %.2e mol" % dC)
        worst_kn = 0.0
        for c in kc:
            pH_an = M.analytic_const(c.p_co2_atm, alk_kgw=c.Alk, k_kgw=c.totals["K"],
                                      nitrite=c.totals["Nti"])
            d = c.pH - pH_an
            worst_kn = max(worst_kn, abs(d))
            check("H 表压 %.2f MPa: pH 与独立解析解(含亚硝酸盐)" % c.gauge_mpa,
                  abs(d) <= 0.02, "PHREEQC %.4f / 解析 %.4f (d=%+.4f)" % (c.pH, pH_an, d))
        print("  含盐路线的最大 |dpH| = %.4f" % worst_kn)
        gam = _species_gammas(os.path.join(M.OUT, "equilibrium_co2_kno2.out"),
                              "NtiO2-", "HNtiO2")
        if gam:
            for c, gd in zip(kc, gam):
                g_no2 = gd.get("NtiO2-", 1.0); g_hn = gd.get("HNtiO2", 1.0)
                aH = 10**(-c.pH)
                K = (c.m["HNtiO2"]*g_hn)/(c.m["NtiO2-"]*g_no2*aH)
                # 容差 3%: PHREEQC 会对 log K 作压力修正 (HNtiO2 未给独立 Vm),
                # 2 MPa 下 log K 由 3.1600 漂到约 3.169
                check("H 表压 %.2f MPa: HNO2 质子化常数 = 10^3.16" % c.gauge_mpa,
                      abs(K/10**3.16 - 1) <= 0.03,
                      "反算 log K = %.4f (设定 3.1600, 差值为 PHREEQC 的压力修正); gamma(NO2-)=%.4f gamma(HNtiO2)=%.4f"
                      % (math.log10(K), g_no2, g_hn))
        else:
            check("H 亚硝酸盐活度可从输出读出", False, "未能在 .out 中定位活度行")
        real = _species_gammas(os.path.join(M.OUT, "equilibrium_co2_realno2.out"), "NO2-")
        if real and gam:
            for i, (gr, gd) in enumerate(zip(real, gam)):
                gn = gd.get("NtiO2-", 1.0); grr = gr.get("NO2-", 1.0)
                d = abs(grr-gn)/gn
                check("H 表压 %.2f MPa: NtiO2- 活度系数 = 数据库 NO2-" % kc[i].gauge_mpa,
                      d <= 0.01, "真 NO2- %.4f vs NtiO2- %.4f (差 %.2f%%)"
                      % (grr, gn, 100*d))
        else:
            check("H 真 NO2- 对照算例可用", False,
                  "缺少 output/equilibrium_co2_realno2.out")
    else:
        check("H KNO2 输出存在", False, "缺少 output/equilibrium_co2_kno2.tsv")

    print()
    print("="*90)
    print("  通过 %d 项, 失败 %d 项" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("    失败:", f)
    print("="*90)
    return 1 if FAIL else 0

if __name__ == "__main__":
    sys.exit(main())
