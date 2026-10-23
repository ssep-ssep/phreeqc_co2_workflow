# -*- coding: utf-8 -*-
"""
完整性校验: 比对当前目录与 MANIFEST.sha256

用法:  python check_integrity.py
退出码 0 = 全部一致; 1 = 存在差异或缺文件
"""
import os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "MANIFEST.sha256")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    if not os.path.exists(MANIFEST):
        print("找不到 MANIFEST.sha256，请在包根目录运行本脚本")
        return 1
    entries = []
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digest, rel = line.split("  ", 1)
            entries.append((digest, rel))
    missing, changed, ok = [], [], 0
    for digest, rel in entries:
        p = os.path.join(HERE, rel.replace("/", os.sep))
        if not os.path.exists(p):
            missing.append(rel)
        elif sha256(p) != digest:
            changed.append(rel)
        else:
            ok += 1
    print("清单文件: %d" % len(entries))
    print("一致:     %d" % ok)
    if missing:
        print("缺失:     %d" % len(missing))
        for r in missing:
            print("   [缺失] %s" % r)
    if changed:
        print("内容不同: %d" % len(changed))
        for r in changed:
            print("   [改动] %s" % r)
    if missing or changed:
        print("\n结论: 不一致 —— 请检查是否漏传文件或本地被修改")
        return 1
    print("\n结论: 全部一致，包完整可用")
    print("提示: 再运行 python run_all.py 可端到端复现并重新生成报告")
    return 0

if __name__ == "__main__":
    sys.exit(main())