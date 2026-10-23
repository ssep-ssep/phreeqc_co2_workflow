# -*- coding: utf-8 -*-
"""
一键复现整个工作流
==================
  1) 用 PHREEQC 跑三组输入 (标定网格 / 高压细网格 / 13 个正式算例)
  2) 生成计算报告 (docx)
  3) 自动校验 (表号连续性、数值一致性、内部自洽)

用法:
    python run_all.py                 # 完整流程
    python run_all.py --skip-phreeqc  # 跳过 PHREEQC, 直接用已有输出重建报告
"""
import os, sys, subprocess, shutil, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from config import PKG, SRC, IN, OUT, BIN, REPORT, REPORT_DIR

def find_phreeqc():
    """定位 PHREEQC 可执行文件"""
    for name in ("phreeqc.exe", "phreeqc"):
        p = os.path.join(BIN, name)
        if os.path.exists(p):
            return p
    p = shutil.which("phreeqc")
    if p:
        return p
    return None

def run_phreeqc(exe):
    os.makedirs(OUT, exist_ok=True)          # 输出目录必须存在, 否则 PHREEQC 会转入交互提问
    os.makedirs(REPORT_DIR, exist_ok=True)
    jobs = [("cal2.pqi", "cal2_out.txt"),
            ("hp_fine.pqi", "hp_fine_out.txt"),
            ("final2.pqi", "final2_out.txt")]
    for inp, out in jobs:
        src = os.path.join(IN, inp)
        dst = os.path.join(OUT, out)
        db  = os.path.join(BIN, "phreeqc.dat")
        if not os.path.exists(db):
            db = "phreeqc.dat"
        t0 = time.time()
        if not os.path.exists(src):
            print("     [错误] 输入文件不存在: %s" % src)
            return False
        try:
            r = subprocess.run([exe, src, dst, db], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=300, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            print("     [错误] PHREEQC 超时 (300 s), 通常是输出目录缺失或参数有误")
            return False
        err = os.path.join(OUT, out)
        nerr = 0
        if os.path.exists(err):
            with open(err, encoding="utf-8", errors="ignore") as f:
                nerr = sum(1 for l in f if l.strip().startswith("ERROR"))
        print("  %-16s -> %-20s  %5.2f s   errors=%d" % (inp, out, time.time()-t0, nerr))
        if nerr:
            print("     [警告] 该算例存在 ERROR 行，请检查 output/%s" % out)
    return True

def main():
    skip = "--skip-phreeqc" in sys.argv
    print("="*72)
    print("  PHREEQC / CO2 平衡工作流")
    print("  包目录: %s" % PKG)
    print("="*72)

    if not skip:
        exe = find_phreeqc()
        if not exe:
            print("[错误] 未找到 PHREEQC 可执行文件。")
            print("       Windows: 已在 phreeqc/phreeqc.exe 提供")
            print("       Linux  : 运行 bash phreeqc/build_phreeqc.sh 自行编译")
            return 1
        print("\n[1/3] 运行 PHREEQC  (可执行文件: %s)" % exe)
        if not run_phreeqc(exe):
            return 1
    else:
        print("\n[1/3] 跳过 PHREEQC, 使用 output/ 中已有结果")

    print("\n[2/3] 生成计算报告")
    _kw = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=SRC)
    r  = subprocess.run([sys.executable, os.path.join(SRC, "merge.py")], **_kw)
    r2 = subprocess.run([sys.executable, os.path.join(SRC, "make_report.py")], **_kw)
    tail = [l for l in (r2.stdout or "").splitlines() if "saved" in l or "caption" in l]
    for l in tail:
        print("  " + l)
    if r2.returncode != 0:
        print(r2.stdout[-2000:]); print(r2.stderr[-2000:])
        return 1
    print("  报告: %s" % REPORT)

    print("\n[3/3] 自动校验")
    r3 = subprocess.run([sys.executable, os.path.join(SRC, "verify_new.py")], **_kw)
    for l in (r3.stdout or "").splitlines():
        if l.strip():
            print("  " + l)
    print("\n完成。报告位于: %s" % REPORT)
    return 0

if __name__ == "__main__":
    sys.exit(main())
