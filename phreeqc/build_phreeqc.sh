#!/usr/bin/env bash
# =============================================================================
#  在 Linux / macOS 上自行编译 PHREEQC v3.8.6
#  用法:  bash phreeqc/build_phreeqc.sh
#  产物:  phreeqc/phreeqc        (可执行文件, 与 run_all.py 的查找路径一致)
#         phreeqc/phreeqc.dat    (热力学数据库, 已随包提供, 无需重新生成)
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

VER=3.8.6-17100
URL="https://water.usgs.gov/water-resources/software/PHREEQC/phreeqc-${VER}.tar.gz"

if [ ! -x ./phreeqc ] && [ ! -f ./phreeqc ]; then
  echo "== 下载 PHREEQC ${VER} =="
  if [ ! -f "phreeqc-${VER}.tar.gz" ]; then
    curl -sSL -o "phreeqc-${VER}.tar.gz" "${URL}";
  fi
  tar xzf "phreeqc-${VER}.tar.gz"
fi

# 发行包的解包目录名各版本不同 (phreeqc-... 或 iphreeqc-...), 不写死:
SRC=""
for d in phreeqc-${VER} iphreeqc-${VER} phreeqc-* iphreeqc-*; do
  if [ -f "$d/configure" ]; then SRC="$d"; break; fi
done
if [ -z "$SRC" ]; then
  echo "[错误] 找不到含 configure 的源码目录"; exit 1
fi
echo "== 源码目录: $SRC =="

cd "$SRC"
echo "== 配置 (安装到本目录) =="
./configure --prefix="$(cd .. && pwd)" > ../configure.log 2>&1
echo "== 编译 =="
make -j"$(nproc 2>/dev/null || echo 4)" > ../make.log 2>&1
make install > ../install.log 2>&1
cd ..

if [ ! -x ./phreeqc ]; then
  echo "[错误] make install 后仍未找到 ./phreeqc, 见 install.log"; exit 1
fi
echo "== 自检 (期望 32/32 PASS) =="
( cd "$SRC/test" && make check 2>&1 | tail -12 ) || true
echo
echo "完成: $(pwd)/phreeqc"
echo "随后运行:  python ../run_all.py"