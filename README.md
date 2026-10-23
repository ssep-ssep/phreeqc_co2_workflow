# PHREEQC / CO₂ 平衡工作流

0.2 M KHCO₃ 溶液与 CO₂ 的气液平衡 pH 计算。本包**自包含、可独立复现**，
可不依赖任何 HPC 集群。

---

## 1  快速开始

```bash
# Windows
python run_all.py

# Linux / macOS
python3 run_all.py
```

一条命令完成：跑 PHREEQC → 生成报告 → 自动校验。

产物：`report/0.2M_KHCO3_CO2平衡pH计算报告.docx`

---

## 2  环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Python | ≥ 3.8 | 需 `python-docx` |
| PHREEQC | v3.8.6 | Windows 已随包提供 `phreeqc/phreeqc.exe`；Linux 见下 |
| 数据库 | phreeqc.dat | 已随包提供 `phreeqc/phreeqc.dat` |

安装 Python 依赖：

```bash
pip install python-docx
```

### Linux 上自行编译 PHREEQC

```bash
bash phreeqc/build_phreeqc.sh   # 下载 3.8.6 源码、编译、安装到 phreeqc/
python3 run_all.py
```

若系统已装 PHREEQC，`run_all.py` 会自动在 `PATH` 中查找。

---

## 3  目录结构

```
phreeqc_co2_workflow/
├── run_all.py              一键入口（跑 PHREEQC → 生成报告 → 校验）
├── check_integrity.py      检出完整性自检（比对 MANIFEST.sha256）
├── MANIFEST.sha256         源文件 SHA-256 清单
├── LICENSE
├── README.md
├── phreeqc/
│   ├── phreeqc.exe         Windows 二进制（Linux 可删）
│   ├── phreeqc.dat         热力学数据库
│   └── build_phreeqc.sh    Linux 自行编译脚本
├── input/
│   ├── cal2.pqi            定压标定网格（0.2–22 atm，26 个算例）
│   ├── hp_fine.pqi         高压段细网格（19–22 atm，8 个算例）
│   └── final2.pqi          13 个正式算例
├── output/                 PHREEQC 原始输出（运行后生成）
│   ├── cal2_out.txt            定压标定网格输出
│   ├── hp_fine_out.txt         高压段细网格输出（收敛分支之一）
│   ├── hp_fine_linux_out.txt    同一输入在 Linux 源码编译版下的结果（见 §7）
│   └── final2_out.txt          13 个正式算例输出
├── src/
│   ├── config.py           路径配置（全部相对包根目录）
│   ├── newdata.py          数据层：解析 PHREEQC 输出、交叉校验
│   ├── khbco3_pH_analytic.py  恒压独立解析解
│   ├── khbco3_sealed.py       定容独立解析解
│   ├── build_docx.py       docx 构件（标题/表格/字体）
│   ├── gen_report_*.py     报告正文（head/body/body2/body3）
│   ├── merge.py            合并上述为 make_report.py
│   ├── make_report.py      报告生成主程序
│   ├── verify_new.py       报告自动校验
│   └── attrib.py / chk_const.py / chk_hp2.py / cmp_cont.py
│                          归因分析与诊断脚本
└── report/                 生成的报告
```

---

## 4  计算体系

| 项 | 取值 |
|---|---|
| 溶液 | 0.2 mol/L KHCO₃，K⁺ = 0.2，碱度 = 0.2 mol/L（以 HCO₃⁻ 计）|
| 温度 | 25.0 °C |
| 反应器 | 定容，气液比 V气/V液 = 0.6 |
| 压力口径 | **表压**，绝对压力 = 表压 + 0.1013 MPa |
| 水蒸气 | p(H₂O) = 0.031 atm（由水活度 0.993 导出）|

### 三种工况

| 组 | 含义 | 压力如何给定 |
|---|---|---|
| 1 | 恒压：常压敞开，持续通入 CO₂ | 气相压力由外界维持，气液比不参与 |
| 2 | 定容，以**充气压力**为准 | 充至 P 后密封，气相压力下降，液相由容器总碳决定 |
| 3 | 定容，以**平衡压力**为准 | 体系稳定在 P，液相化学只取决于 CO₂ 分压 |

---

## 5  关键结果

| 表压 / MPa | 0.00 | 0.10 | 0.25 | 0.50 | 1.00 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|
| 组 1 恒压 pH | 7.002 | — | — | — | — | — | — |
| 组 2 定容(充气) pH | — | 7.095 | 6.839 | 6.599 | 6.334 | 6.173 | 6.057 |
| 组 3 定容(平衡) pH | — | 6.701 | 6.460 | 6.232 | 5.982 | 5.833 | 5.730 |

---

## 6  验证

三条相互独立的技术路线：

| 方法 | 偏差 |
|---|---|
| PHREEQC ↔ 独立解析解（Davies + Peng-Robinson） | \|ΔpH\| ≤ 0.024 |
| PHREEQC ↔ 分析化学校验（分布分数反算） | ≤ 0.01% |
| 容器碳守恒残差 | < 2×10⁻⁵ mol/L |

`run_all.py` 每次运行都会自动做表号连续性与数值一致性校验；
`check_integrity.py` 可校验检出是否完整（与 MANIFEST.sha256 逐文件比对）。

---

## 7  已知注意事项

**（1）pCO₂ 20～21 atm 区间，PHREEQC v3.8.6 的收敛结果依赖构建。** 同一输入文件
（同一 SHA-256）、同一版本，但 Windows 官方发行版与 Linux 源码编译版在 20.30 与
21.00 atm 两点给出相差一倍的 DIC，其余各点完全一致：

| pCO₂ / atm | 20.00 | 20.30 | 20.50 | 20.70 | 21.00 | 21.50 | 22.00 |
|---|---|---|---|---|---|---|---|
| Windows 官方发行版 | 0.7899 | **1.1790** | 1.1900 | 0.8077 | **1.2160** | 1.2430 | 1.2710 |
| Linux 源码编译版 | 0.7899 | 0.7975 | 1.1900 | 0.8077 | 0.8152 | 1.2430 | 1.2710 |
| 符合亨利 + PR 逸度修正 | 是 | 是 | 否 | 是 | 是 | 否 | 否 |

仅 DIC ≈ 0.80 的分支与亨利定律 + Peng-Robinson 逸度修正一致（理论 K_H·φ ≈ 0.0302，
另一分支隐含 ≈ 0.048，偏离约 60%）。报告组 3 的 2.00 MPa 一档采用与理论相符的分支
（pCO₂ = 20.70 atm，两种构建在此压力上一致）。1.50 MPa 及以下未见此问题。

两份原始输出都在 output/ 里：hp_fine_out.txt（Windows，随 run_all.py 重跑）与
hp_fine_linux_out.txt（Linux 集群上由同一输入得到，作为对照保留）。

**（2）PHREEQC 的 `GAS_PHASE -fixed_volume` 不可用。** 该版本中定容气相不守恒气相总量
（顶空仅为液相 1/10 时，平衡压力由 0.98 atm 升至 1.63 atm，违反碳守恒），
故组 2 改用两轮方法：平衡分压由容器碳守恒在 PHREEQC 之外确定，液相热力学仍全部由 PHREEQC 计算。

**（3）`CO2` 输出即表观 CO₂\***。数据库 phreeqc.dat 无 H₂CO₃ 物种，
CO₂(aq) 与 H₂CO₃ 已合并；由 log K = −1.8 与 −log(K_a1·K_a2) = 16.681 锁定。
H₂CO₃ 占溶解态 CO₂\* 的 0.170%（25 °C 纯水取值，仅由温度决定）。

**（4）`(CO₂)₂` 是数据库内置的算法项**，定义处注释即为
`activity correction for CO₂ solubility at high P, T`，等效于水溶液中 CO₂ 的第二维里系数，
不是经独立测定的化学物种；其"折合碳"仅为质量衡算记账量。

**（5）碱度实测为 0.195 eq/L**，而非设定值 0.200，差异源于 mol·L⁻¹ 与 mol·kg⁻¹ 的换算。

---

## 8  许可证

本仓库代码以 MIT 许可证发布（见 LICENSE）。

随包重新分发的 PHREEQC v3.8.6（phreeqc/phreeqc.exe 与 phreeqc/phreeqc.dat）
属美国地质调查局（USGS）公共领域作品；phreeqc/build_phreeqc.sh 从官方源码
发行版下载并编译。详见 <https://www.usgs.gov/software/phreeqc-version-3>。

---

## 9  引用

1. Parkhurst D L, Appelo C A J. *Description of input and examples for PHREEQC version 3*.
   U.S. Geological Survey Techniques and Methods, Report 6-A43, 2013.
2. Peng D Y. A simple algorithm for calculating phase equilibria with local and global
   minimization methods. *Fluid Phase Equilibria*, 1989, 54(3): 381–398.
3. Charlton S R, Parkhurst D L. Modules based on the geochemical model PHREEQC for use in
   scripting and programming languages. *Computers & Geosciences*, 2011, 37(10): 1653–1663.