# -*- coding: utf-8 -*-
"""
co2_model.py —— PHREEQC 结果的读取与交叉核对原语

数据来源: PHREEQC 的 SELECTED_OUTPUT (-high_precision true) 生成的 TSV,
不解析格式化文本, 避免有效数字损失。

单位口径:
  * PHREEQC 原生输出为 molality (mol/kg water); 报告同时给出 mol/L,
    换算因子 factor = mass_H2O / solution_volume_L
  * 碱度: 直接采用 PHREEQC 输出的 Alk, 并用完整物种求和交叉核对
    (含中性络合物 KHCO3 的一个当量; 若加入 HNO2 则再减去其质子化部分)

修正记录 (2026-10-24 代码审查):
  - 删除"最高压力点用邻近算例替换"的做法: 现在用 EQUILIBRIUM_PHASES 直接规定
    平衡 CO2 分压, 气相留足余量, 边界总是可达, 无需挑选分支
  - 碱度求和补入 KHCO3
  - 物种浓度标注为 molality 并另给 mol/L
"""
import os, csv, math, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG  = os.path.dirname(HERE)
OUT  = os.path.join(PKG, "output")

GAUGE = [0.00, 0.10, 0.25, 0.50, 1.00, 1.50, 2.00]   # 表压 MPa
ATM_MPA   = 0.101325
P_ATM     = 1.0        # 当地大气压 (atm)
H2O_ATM   = 0.03106    # 25 C 水蒸气分压 (atm)
R_GAS     = 0.082057 * 298.15   # L atm / mol
RATIO     = 0.6        # V_G / V_L (定容工况)

SPECIES = ["CO2", "HCO3-", "CO3-2", "KHCO3", "(CO2)2", "H+", "OH-", "NtiO2-", "HNtiO2"]

class Case(object):
    """一个平衡工况"""

    def __init__(self, row, gauge_mpa):
        f = lambda k: float(row.get(k) or 0.0)
        self.gauge_mpa  = gauge_mpa
        self.p_abs_mpa  = gauge_mpa + P_ATM * ATM_MPA
        self.p_co2_atm  = f("inferred_pCO2_atm")
        self.p_co2_target_atm = (P_ATM + gauge_mpa / ATM_MPA) - H2O_ATM
        self.pH         = f("pH")
        self.Alk        = f("Alk")            # eq/kg water
        self.I          = f("mu")
        self.pct_err    = f("pct_err")
        self.mass_H2O   = f("mass_H2O")
        self.soln_vol_L = f("solution_volume_L")
        self.phi        = f("phi_CO2")
        self.totals     = {k: f(k) for k in ("C", "K", "Nti")}
        self.m          = {k: f("m_" + k) for k in SPECIES}
        self.a          = {k: f("a_" + k) for k in ("H+", "CO2", "HCO3-", "CO3-2")}
        self.gas_dCO2   = f("d_CO2(g)")
        self.factor     = (self.mass_H2O / self.soln_vol_L) if self.soln_vol_L else 1.0

    def M(self, sp):
        """mol/L"""
        return self.m[sp] * self.factor

    def m(self, sp):
        """mol/kg water"""
        return self.m[sp]

    def alk_species(self):
        """完整物种求和的碱度 (eq/kg water)"""
        return (self.m["HCO3-"] + 2*self.m["CO3-2"] + self.m["KHCO3"]
                + self.m["OH-"] - self.m["H+"] - self.m["HNtiO2"])

    def carbon_species(self):
        """完整物种求和的总碳 (mol/kg water)"""
        return (self.m["CO2"] + self.m["HCO3-"] + self.m["CO3-2"]
                + self.m["KHCO3"] + 2*self.m["(CO2)2"])

    def alk_M(self):
        return self.Alk * self.factor

    def DIC_M(self):
        return self.totals["C"] * self.factor

    def summary(self):
        return dict(gauge=self.gauge_mpa, p_abs=self.p_abs_mpa,
                    p_co2=self.p_co2_atm, pH=self.pH, Alk=self.Alk, I=self.I,
                    DIC=self.DIC_M(), CO2=self.M("CO2"), HCO3=self.M("HCO3-"),
                    CO3=self.M("CO3-2"), KHCO3=self.M("KHCO3"),
                    D2=self.M("(CO2)2"), OH=self.M("OH-"), H=self.M("H+"))


def read_tsv(path):
    """读 SELECTED_OUTPUT 的 TSV, 返回 (表头, 行字典列表)"""
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows:
        return [], []
    head = [h.strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(x.strip() for x in r):
            continue
        out.append(dict(zip(head, [x.strip() for x in r])))
    return head, out


def load_case(tsv_name, gauges=None):
    """读一个算例文件的 react 状态, 返回 Case 列表"""
    path = tsv_name if os.path.isabs(tsv_name) else os.path.join(OUT, tsv_name)
    head, rows = read_tsv(path)
    react = [r for r in rows if r.get("state") == "react"]
    gauges = gauges or GAUGE
    if len(react) != len(gauges):
        raise RuntimeError("%s: 期望 %d 个平衡状态, 实得 %d"
                           % (tsv_name, len(gauges), len(react)))
    return [Case(r, g) for r, g in zip(react, gauges)]


def load_initial(tsv_name):
    """读 i_soln 状态 (初始解), 用于质量守恒核对"""
    path = tsv_name if os.path.isabs(tsv_name) else os.path.join(OUT, tsv_name)
    head, rows = read_tsv(path)
    return [r for r in rows if r.get("state") == "i_soln"]


# --------------------------------------------------------------------------
# 独立解析解 (交叉核对用, 与 PHREEQC 无任何共用)
# --------------------------------------------------------------------------
import importlib.util
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
_analytic = _load("_khbco3_pH_analytic", os.path.join(HERE, "khbco3_pH_analytic.py"))
_sealed   = _load("_khbco3_sealed",      os.path.join(HERE, "khbco3_sealed.py"))

def analytic_const(p_co2_atm, alk_kgw=0.2, k_kgw=None, nitrite=0.0, T=298.15):
    """恒压: 规定 CO2 分压, 返回独立解析解的 pH"""
    r = _analytic.pH_open(T, p_co2_atm, alk_kgw=alk_kgw, k_kgw=k_kgw, nitrite=nitrite)
    return r["pH"]

def analytic_sealed(P0_co2_atm, r=RATIO, alk_kgw=0.2, k_kgw=None, nitrite=0.0):
    """定容: 初始充 CO2 至 P0, 返回 (pH, P_eq)"""
    return _sealed.solve(P0_co2_atm, r, alk_kgw=alk_kgw, k_kgw=k_kgw, nitrite=nitrite)

def dik_at(cases, p_co2_atm):
    """由一组 Case 插值得到 DIC(p) (mol/kg water)"""
    xs = [c.p_co2_atm for c in cases]
    ys = [c.totals["C"] for c in cases]
    if p_co2_atm <= xs[0]:  return ys[0]
    if p_co2_atm >= xs[-1]: return ys[-1]
    for i in range(len(xs)-1):
        if xs[i] <= p_co2_atm <= xs[i+1]:
            f = (p_co2_atm-xs[i])/(xs[i+1]-xs[i])
            return ys[i] + f*(ys[i+1]-ys[i])

def solve_sealed_p_eq(cases, P0_co2_atm, ratio=RATIO, c_init=0.2):
    """由容器碳守恒解出平衡 CO2 分压 (atm)"""
    lo, hi = 1e-9, P0_co2_atm
    for _ in range(200):
        mid = 0.5*(lo+hi)
        f = dik_at(cases, mid) - c_init - (P0_co2_atm - mid)*ratio/R_GAS
        f0 = dik_at(cases, lo) - c_init - (P0_co2_atm - lo)*ratio/R_GAS
        if f0*f <= 0: hi = mid
        else:        lo = mid
    return 0.5*(lo+hi)


if __name__ == "__main__":
    for c in load_case("equilibrium_co2.tsv"):
        s = c.summary()
        print("  表压 %4.2f | 绝对 %6.4f MPa | pCO2 %9.6f atm | pH %8.5f | Alk %.5f | I %.5f | DIC %.5f M"
              % (s["gauge"], s["p_abs"], s["p_co2"], s["pH"], s["Alk"], s["I"], s["DIC"]))

# --------------------------------------------------------------------------
# 内部一致性核对
# --------------------------------------------------------------------------
def ionic_strength_from_species(case):
    """由各物种的电荷数与浓度算离子强度 (mol/kg water), 用于与 PHREEQC 报告的 mu 互校"""
    # 离子强度只计带电物种: 游离 K+ = 总 K - 中性络合物 KHCO3 中的 K
    k_free = case.totals["K"] - case.m["KHCO3"]
    return 0.5*(k_free + case.m["H+"] + case.m["OH-"] + case.m["HCO3-"]
                + 4*case.m["CO3-2"] + case.m["NtiO2-"])
