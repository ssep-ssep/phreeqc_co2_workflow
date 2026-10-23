# -*- coding: utf-8 -*-
"""co2_model.py —— 0.2 M KHCO3 / CO2 气液平衡模型 (PHREEQC 结果解析 + 交叉校验)

提供:
  * load_outputs()      解析 PHREEQC 输出, 返回每算例的物种与 pH
  * enrich()            补算 DIC / 碱度 / H2CO3 拆分
  * recon()             分析化学校验: 由 pH 与总碳反算各组分
  * analytic_const()    独立解析解 (恒压 / 指定平衡分压)
  * analytic_sealed()   独立解析解 (定容, 含容器碳守恒)
  * GROUPS              三种工况的算例分组
"""
import os, re, math, importlib.util, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG  = os.path.dirname(HERE)
OUT  = os.path.join(PKG, "output")

# ---- 常数 ----
KH      = 1.70e-3        # H2CO3 / CO2(aq) 水合分配系数 (25 C)
RATIO   = 0.6            # V气 / V液
RT      = 0.082057*298.15
MPA2ATM = 1/0.101325     # 1 MPa = 9.86923 atm
PATM    = 1.0            # 当地大气压 (atm)
PH2O    = 0.03106        # 水蒸气分压 (atm, 25 C)
GAUGE   = [0.10, 0.25, 0.50, 1.00, 1.50, 2.00]   # 表压档位 (MPa)
ABS     = {g: g*MPA2ATM + PATM for g in GAUGE}   # 绝对压力 (atm)
ABS[0.0] = PATM

# ---- PHREEQC 物种表正则 ----
SPEC = [("CO2", r"^\s+CO2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("D2",  r"^\s+\(CO2\)2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("H1",  r"^\s+HCO3-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("H3",  r"^\s+CO3-2\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("KH",  r"^\s+KHCO3\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("OH",  r"^\s+OH-\s+([\d.eE+-]+)\s+([\d.eE+-]+)"),
        ("H",   r"^\s+H\+\s+([\d.eE+-]+)\s+([\d.eE+-]+)")]

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_sealed = _load_module("_khbco3_sealed", os.path.join(HERE, "khbco3_sealed.py"))
_open   = _load_module("_khbco3_open",   os.path.join(HERE, "khbco3_pH_analytic.py"))

# PHREEQC 在输出开头回显输入的 GAS_PHASE 定义, 其中给出精确的气相分压。
# (结果段末尾的 "CO2(g) ... Pressure X atm" 汇总行只有 2 位有效数字, 不可用于计算)
GAS_ECHO = re.compile(
    r"GAS_PHASE\s+\d+\s*\n"
    r"\s*fixed_pressure\s*\n"
    r"\s*pressure\s+([\d.eE+-]+)\s*\n"
    r"\s*CO2\(g\)\s+([\d.eE+-]+)\s*\n"
    r"\s*H2O\(g\)\s+([\d.eE+-]+)", re.M)

def parse_file(path):
    """解析一个 PHREEQC 输出文件, 返回算例列表"""
    txt = open(path, encoding="utf-8", errors="ignore").read()
    echoes = GAS_ECHO.findall(txt)
    parts = re.split(r"Initial solution (\d+)\.", txt)
    out = []
    for i in range(1, len(parts), 2):
        b = parts[i+1]
        d = {}
        for k, pat in SPEC:
            m = re.findall(pat, b, re.M)
            if m:
                d[k] = (float(m[-1][0]), float(m[-1][1]))
        ph = re.findall(r"([\d.]+)\s+Charge balance", b)
        tt = re.findall(r"Total CO2 \(mol/kg\)\s+=\s+([\d.eE+-]+)", b)
        if ph and d:
            d["pH"]   = float(ph[-1])
            d["TOT"]  = float(tt[-1]) if tt else None
            j = len(out)
            if j < len(echoes):
                p_tot, p_co2, p_h2o = (float(x) for x in echoes[j])
                d["pTotal"] = p_tot
                d["pCO2"]   = p_co2
                d["pH2O"]   = p_h2o
            else:
                d["pTotal"] = d["pCO2"] = d["pH2O"] = 0.0
            out.append(enrich(d))
    return out

def enrich(d):
    # H2CO3 已由 PHREEQC 并入表观物种 CO2*, 此处仅作拆分比例参考
    d["H2"] = d["CO2"][0]*KH
    # 总无机碳 = 物种和 (含 (CO2)2 的两个碳)。不用 PHREEQC 打印的 "Total CO2",
    # 因其只有 4 位有效数字; 两者在 1e-5 量级上一致。
    d["DIC"] = d["CO2"][0]+d["H1"][0]+d["H3"][0]+d["KH"][0]+2*d["D2"][0]
    d["Alk"] = d["H1"][0]+2*d["H3"][0]+d["OH"][0]-d["H"][0]
    return d

def recon(d, Ka1a, Ka2):
    """分析化学校验: 给定 pH 与总碳, 按碳酸平衡式与活度系数反算各组分浓度"""
    aH = d["H"][1]
    g1 = 10**math.log10(d["H1"][1]/d["H1"][0])
    g0 = 10**math.log10(d["CO2"][1]/d["CO2"][0])
    g2 = 10**math.log10(d["H3"][1]/d["H3"][0])
    CT = d["CO2"][0]+d["H1"][0]+d["H3"][0]
    lo, hi = 1e-8, 0.5
    for _ in range(300):
        mid = (lo+hi)/2
        f = (aH*mid/Ka1a)/g0 + mid/g1 + (Ka2*mid/aH)/g2 - CT
        if f < 0: lo = mid
        else:     hi = mid
    ah = (lo+hi)/2
    return (aH*ah/Ka1a)/g0, ah/g1, (Ka2*ah/aH)/g2

def analytic_const(P_atm):
    """独立解析解: 指定气相 CO2 分压 (恒压 / 指定平衡压力)"""
    return _open.pH_open(298.15, P_atm*0.101325, True, True)["pH"]

def analytic_sealed(P0_atm):
    """独立解析解: 定容反应器, 由充气压力解出平衡分压 (含容器碳守恒)"""
    r = _sealed.solve(P0_atm, RATIO)
    return r[0] if isinstance(r, tuple) else r

def load_final():
    """13 个正式算例 -> (组1 恒压, 组2 定容-充气, 组3 定容-平衡)"""
    S = parse_file(os.path.join(OUT, "final2_out.txt"))
    if len(S) < 13:
        raise RuntimeError("final2_out.txt 算例数不足: %d" % len(S))
    grp1 = [S[0]]
    grp2 = [S[7+k] for k in range(6)]
    grp3 = list(S[1:7])
    # 组3 的 2.00 MPa 一档采用与亨利+PR 逸度修正相符的分支 (见 README 已知注意事项)
    hf = parse_file(os.path.join(OUT, "hp_fine_out.txt"))
    stable = [x for x in hf if abs(x["pCO2"]-20.70) < 0.02]
    if not stable:
        raise RuntimeError("hp_fine_out.txt 中找不到 20.70 atm 算例")
    grp3[5] = stable[0]
    return grp1, grp2, grp3

if __name__ == "__main__":
    g1, g2, g3 = load_final()
    for nm, cs, gau in [("组1 恒压", g1, [0.0]), ("组2 定容-充气", g2, GAUGE),
                        ("组3 定容-平衡", g3, GAUGE)]:
        print("=== %s ===" % nm)
        for g, d in zip(gau, cs):
            pHan = analytic_const(ABS[g]) if nm != "组2 定容-充气" else analytic_sealed(ABS[g])
            print("  表压 %4.2f MPa | 绝对 %7.3f atm | pCO2 %6.3f | pH %6.3f | 解析 %6.3f | d=%+.3f"
                  % (g, ABS[g], d["pCO2"], d["pH"], pHan, d["pH"]-pHan))
