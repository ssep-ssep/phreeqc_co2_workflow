#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键复现并校验整个工作流
========================
  1) 用 PHREEQC 跑三个算例 (定压标定网格 / 高压段细网格 / 13 个正式算例)
  2) 对输出做全面交叉校验 (独立解析解、分析化学校验、容器碳守恒、高压段行为)

用法:
    python run_all.py                 # 完整流程
    python run_all.py --skip-phreeqc  # 跳过 PHREEQC, 直接校验已有输出
"""
import os, sys, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from config import PKG, SRC, IN, OUT, BIN

JOBS = [("cal2.pqi",    "cal2_out.txt"),     # 定压标定网格
        ("hp_fine.pqi", "hp_fine_out.txt"),  # 高压段细网格 (Windows 官方发行版)
        ("final2.pqi",  "final2_out.txt")]   # 13 个正式算例
# 注: hp_fine_linux_out.txt 是同一输入在 Linux 源码编译版下的结果, 作为对照保留,
#     不在本地重跑 (同一输入在两种构建下结果不同, 参见 README 已知注意事项)

def find_phreeqc():
    for name in ("phreeqc.exe", "phreeqc"):
        p = os.path.join(BIN, name)
        if os.path.exists(p):
            return p
    return shutil.which("phreeqc")

def run_phreeqc(exe):
    os.makedirs(OUT, exist_ok=True)
    db = os.path.join(BIN, "phreeqc.dat")
    if not os.path.exists(db):
        db = "phreeqc.dat"
    for inp, out in JOBS:
        src = os.path.join(IN, inp)
        dst = os.path.join(OUT, out)
        if not os.path.exists(src):
            print("     [错误] 输入文件不存在: %s" % src)
            return False
        try:
            subprocess.run([exe, os.path.join("input", inp),
                            os.path.join("output", out), db],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300,
                           stdin=subprocess.DEVNULL, cwd=PKG)
        except subprocess.TimeoutExpired:
            print("     [错误] PHREEQC 超时 (300 s)")
            return False
        n = 0
        if os.path.exists(dst):
            with open(dst, encoding="utf-8", errors="ignore") as f:
                n = sum(1 for l in f if l.strip().startswith("ERROR"))
        print("  %-16s -> %-22s errors=%d" % (inp, out, n))
        if n:
            print("     [警告] 该算例存在 ERROR 行, 请检查 output/%s" % out)
    return True

def main():
    skip = "--skip-phreeqc" in sys.argv
    print("="*76)
    print("  PHREEQC / CO2 平衡工作流")
    print("  包目录: %s" % PKG)
    print("="*76)

    if skip:
        print("")
        print("[1/2] 跳过 PHREEQC, 使用 output/ 中已有结果")
    else:
        exe = find_phreeqc()
        if not exe:
            print("[错误] 未找到 PHREEQC 可执行文件。")
            print("       Windows: 已在 phreeqc/phreeqc.exe 提供")
            print("       Linux  : 运行 bash phreeqc/build_phreeqc.sh 自行编译")
            return 1
        print("")
        print("[1/2] 运行 PHREEQC  (可执行文件: %s)" % exe)
        if not run_phreeqc(exe):
            return 1

    print("")
    print("[2/2] 结果交叉校验")
    r = subprocess.run([sys.executable, os.path.join(SRC, "verify_results.py")], cwd=SRC)
    print("")
    print("完成。原始输出位于 output/。")
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())