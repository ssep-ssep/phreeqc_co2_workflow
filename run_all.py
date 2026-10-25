#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键复现并校验整个工作流
========================
  1) 生成 PHREEQC 输入 (主线: 规定平衡 CO2 分压; 对照: 定容充气压力; KNO2 变体)
  2) 运行 PHREEQC (主线 / KNO2 变体)
  3) 迭代求解定容对照工况的平衡分压 (用实际算出的 DIC 作锚点, 直至容器碳守恒收敛)
  4) 对结果做全面交叉校验

用法:
    python run_all.py                 # 完整流程
    python run_all.py --skip-phreeqc  # 跳过 PHREEQC, 直接校验已有输出
"""
import os, sys, subprocess, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from config import PKG, SRC, IN, OUT, BIN

SEALED_ITERS = 4      # 定容对照工况的外层迭代次数

def find_phreeqc():
    """按平台选择可执行文件: Linux 优先用编译好的 phreeqc, 不用 Windows 的 exe"""
    if sys.platform.startswith("win"):
        for name in ("phreeqc.exe", "phreeqc"):
            p = os.path.join(BIN, name)
            if os.path.exists(p):
                return p
    else:
        p = os.path.join(BIN, "phreeqc")
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
        found = shutil.which("phreeqc")
        if found:
            return found
        p = os.path.join(BIN, "phreeqc.exe")
        if os.path.exists(p):
            return p
    return shutil.which("phreeqc")

def run_phreeqc(exe, pqi, out, tsv=None):
    """运行 PHREEQC; 检查返回码、ERROR 行, 并确认输出文件是新生成的"""
    outp = os.path.join(OUT, out)
    tsvp = os.path.join(OUT, tsv) if tsv else None
    before = os.path.getmtime(outp) if os.path.exists(outp) else 0
    if tsvp and os.path.exists(tsvp):
        os.remove(tsvp)
    cmd = [exe, os.path.join("input", pqi), os.path.join("output", out),
           os.path.join("phreeqc", "phreeqc.dat")]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, cwd=PKG,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError("PHREEQC 退出码 %d (%s): %s" % (r.returncode, pqi, r.stderr[-500:]))
    if not os.path.exists(outp):
        raise RuntimeError("PHREEQC 未生成输出: %s" % outp)
    if os.path.getmtime(outp) <= before:
        raise RuntimeError("PHREEQC 输出未被更新, 可能误用旧结果: %s" % outp)
    txt = open(outp, encoding="utf-8", errors="ignore").read()
    nerr = sum(1 for l in txt.splitlines() if l.strip().startswith("ERROR"))
    if nerr:
        raise RuntimeError("%s 有 %d 行 ERROR" % (pqi, nerr))
    if tsvp and not os.path.exists(tsvp):
        raise RuntimeError("PHREEQC 未生成高精度输出: %s" % tsvp)
    print("  %-26s -> %-26s %5.2f s" % (pqi, out, time.time()-t0))
    return txt

def main():
    skip = "--skip-phreeqc" in sys.argv
    print("="*76)
    print("  PHREEQC / CO2 平衡工作流")
    print("  包目录: %s" % PKG)
    print("="*76)

    # ---- 1) 生成输入 ----
    print("\n[1/4] 生成 PHREEQC 输入")
    r = subprocess.run([sys.executable, os.path.join(SRC, "make_inputs.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=SRC)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-2000:]); return 1
    print("  input/: " + ", ".join(sorted(f for f in os.listdir(IN) if f.endswith(".pqi"))))

    # ---- 2) 主线与 KNO2 变体 ----
    if not skip:
        exe = find_phreeqc()
        if not exe:
            print("[错误] 未找到 PHREEQC 可执行文件。")
            print("       Windows: 已在 phreeqc/phreeqc.exe 提供")
            print("       Linux  : 运行 bash phreeqc/build_phreeqc.sh 自行编译")
            return 1
        print("\n[2/4] 运行 PHREEQC  (可执行文件: %s)" % exe)
        run_phreeqc(exe, "equilibrium_co2.pqi", "equilibrium_co2.out", "equilibrium_co2.tsv")
        run_phreeqc(exe, "equilibrium_co2_kno2.pqi", "equilibrium_co2_kno2.out",
                 "equilibrium_co2_kno2.tsv")
        run_phreeqc(exe, "equilibrium_co2_realno2.pqi", "equilibrium_co2_realno2.out",
                 "equilibrium_co2_realno2.tsv")
    else:
        print("\n[2/4] 跳过 PHREEQC, 使用 output/ 中已有结果")

    # ---- 3) 定容对照工况: 迭代求解 ----
    print("\n[3/4] 定容对照工况: 迭代求解平衡分压")
    import co2_model as M
    import make_sealed_input as MS
    cases = M.load_case("equilibrium_co2.tsv")
    init_C = float(M.load_initial("equilibrium_co2.tsv")[0]["C"])
    curve = MS.Curve(cases)
    if not skip:
        for it in range(1, SEALED_ITERS+1):
            path, peqs = MS.write(curve, init_C)
            run_phreeqc(exe, "sealed_charge.pqi", "sealed_charge.out", "sealed_charge.tsv")
            sc = M.load_case("sealed_charge.tsv", gauges=MS.GAUGE_CHARGE)
            worst = 0.0
            for g, c, (gg, P0, pe) in zip(MS.GAUGE_CHARGE, sc, peqs):
                V = c.soln_vol_L/c.mass_H2O
                rhs = init_C + (P0-c.p_co2_atm)*M.RATIO*V/M.R_GAS
                worst = max(worst, abs(c.totals["C"]-rhs))
                curve.add(c.p_co2_atm, c.totals["C"], V)
            print("     迭代 %d: 容器碳守恒最大残差 %.2e mol/kg" % (it, worst))
            if worst < 1e-8:
                break

    # ---- 4) 校验 ----
    print("\n[4/4] 结果交叉校验")
    r = subprocess.run([sys.executable, os.path.join(SRC, "verify_results.py")], cwd=SRC)
    print("\n完成。原始输出位于 output/。")
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())