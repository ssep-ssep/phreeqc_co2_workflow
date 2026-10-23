#!/usr/bin/env bash
# =============================================================================
#  在 Linux / macOS 上自行编译 PHREEQC v3.8.6
#  用法:  bash phreeqc/build_phreeqc.sh
#  产物:  phreeqc/phreeqc      (可执行文件)
#         phreeqc/phreeqc.dat  (热力学数据库, 已随包提供)
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

VER=3.8.6-17100
URL="https://water.usgs.gov/water-resources/software/PHREEQC/phreeqc-${VER}.tar.gz"

echo "== 下载 PHREEQC ${VER} =="
if [ ! -f "iphreeqc-${VER}.tar.gz" ]; then
  curl -sSL -o "iphreeqc-${VER}.tar.gz" "${URL}"
fi
tar xzf "iphreeqc-${VER}.tar.gz"
cd "iphreeqc-${VER}"

echo "== 配置 (安装到本目录) =="
./configure --prefix="$(cd .. && pwd)" > ../configure.log 2>&1

echo "== 编译 =="
make -j"$(nproc 2>/dev/null || echo 4)" > ../make.log 2>&1
make install > ../install.log 2>&1

cd ..
echo "== 自检 (期望 32/32 PASS) =="
( cd "iphreeqc-${VER}/test" && make check 2>&1 | tail -12 )

echo
echo "完成。可执行文件: $(pwd)/phreeqc"
echo "随后运行:  python ../run_all.py"