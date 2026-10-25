
# PHREEQC / CO₂ 平衡工作流

0.2 M KHCO₃ 溶液与 CO₂ 的气液平衡 pH 计算。本包**自包含、可独立复现**，
不依赖任何 HPC 集群，也不生成任何交付文档 —— 只提供输入、原始输出、
模型与校验。需要成文报告的话，自己拿 agent 写即可。

---

## 1  快速开始

```bash
# Windows
python run_all.py

# Linux / macOS  (需先自行编译 PHREEQC)
bash phreeqc/build_phreeqc.sh
python3 run_all.py
```

一条命令完成四件事：生成输入 → 跑 PHREEQC → 迭代求解定容对照工况 → 全面交叉校验。

| 产物 | 说明 |
|---|---|
| `output/*.tsv` | PHREEQC 高精度输出（`SELECTED_OUTPUT -high_precision`）|
| `output/*.out` | PHREEQC 原始输出 |
| 校验输出 | 84 项检查的 PASS/FAIL 明细 |

---

## 2  环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Python | ≥ 3.8 | 无第三方依赖，标准库即可 |
| PHREEQC | v3.8.6 | Windows 已随包提供 `phreeqc/phreeqc.exe`；Linux 见下 |
| 数据库 | phreeqc.dat | 已随包提供 `phreeqc/phreeqc.dat` |

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
├── run_all.py              一键入口
├── check_integrity.py      检出完整性自检（比对 MANIFEST.sha256）
├── MANIFEST.sha256         源文件 SHA-256 清单
├── LICENSE
├── README.md
├── phreeqc/
│   ├── phreeqc.exe         Windows 二进制（Linux 可删）
│   ├── phreeqc.dat         热力学数据库
│   └── build_phreeqc.sh    Linux 自行编译脚本
├── input/
│   ├── equilibrium_co2.pqi        主线：7 个表压档，规定平衡 CO₂ 分压
│   ├── equilibrium_co2_kno2.pqi   同上 + 20 mM KNO₂ 变体 (Nti 独立组分)
│   ├── equilibrium_co2_realno2.pqi 对照：直接用数据库真 NO₂⁻（见 §7）
│   └── sealed_charge.pqi          对照：定容充气压力（由 run_all.py 生成）
├── output/                 PHREEQC 输出（运行后生成）
└── src/
    ├── config.py           路径配置（全部相对包根目录）
    ├── co2_model.py        模型层：读取高精度输出、交叉核对原语
    ├── make_inputs.py      生成主线与 KNO₂ 变体的输入
    ├── make_sealed_input.py  生成定容对照工况的输入（外层迭代）
    ├── verify_results.py   校验主程序（7 组共 84 项检查）
    ├── khbco3_pH_analytic.py  恒压独立解析解（Davies + Peng-Robinson）
    ├── khbco3_sealed.py       定容独立解析解（含容器碳守恒）
    └── attrib.py / chk_const.py / chk_hp2.py   偏差归因诊断
```

---

## 4  计算体系与口径

| 项 | 取值 |
|---|---|
| 溶液 | 0.2 mol/L KHCO₃（K⁺ = 0.2，碱度 = 0.2 mol/L 以 HCO₃⁻ 计）|
| 温度 | 25.0 °C |
| 压力口径 | **表压**；绝对压力 = 表压 + 0.1013 MPa |
| CO₂ 分压 | 平衡时 p(总,绝对) − p(H₂O)，p(H₂O) = 0.031 atm |
| 边界 | 用 `EQUILIBRIUM_PHASES` 直接规定平衡 CO₂ 分压，气相留 100 mol 余量 |
| 浓度单位 | PHREEQC 原生 mol/kg water；报告同时给 mol/L，换算因子 = mass_H₂O / SOLN_VOL |

**为什么用 `EQUILIBRIUM_PHASES` 而不是 `GAS_PHASE -fixed_pressure`：**
后者在定容算例中气相可能被完全耗尽（PHREEQC 报 Fixed-pressure gas phase dissolved
completely），得到的解不可用；而**挑选一个看起来更合理的邻近算例来替换它，等于用结果反推
输入**，不是可复现的做法。`EQUILIBRIUM_PHASES` 配足量气相后，边界总是可达，
不需要任何分支判断。

已验证：

- 目标 CO₂ 分压达成，相对偏差 ≤ 1.2×10⁻¹⁴
- 气相余量 1 / 10 / 100 mol 给出**完全相同**的 pH（Δ = 0）
- Windows 官方发行版与 Linux 源码编译版给出**完全相同**的 pH（Δ = 0）

---

## 5  主要结果

主线（规定平衡 CO₂ 分压）：

| 表压 / MPa | 0.00 | 0.10 | 0.25 | 0.50 | 1.00 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|
| 绝对压力 / MPa | 0.1013 | 0.2013 | 0.3513 | 0.6013 | 1.1013 | 1.6013 | 2.1013 |
| CO₂ 分压 / atm | 0.969 | 1.956 | 3.436 | 5.904 | 10.838 | 15.773 | 20.707 |
| **pH** | **7.0022** | **6.7004** | **6.4600** | **6.2320** | **5.9821** | **5.8332** | **5.7292** |
| DIC / mol·L⁻¹ | 0.2332 | 0.2647 | 0.3112 | 0.3865 | 0.5292 | 0.6618 | 0.7847 |
| CO₂* / mol·L⁻¹ | 0.0315 | 0.0631 | 0.1095 | 0.1844 | 0.3253 | 0.4550 | 0.5739 |
| HCO₃⁻ / mol·L⁻¹ | 0.1925 | 0.1925 | 0.1923 | 0.1919 | 0.1910 | 0.1902 | 0.1894 |
| 碱度 / eq·L⁻¹ | 0.2019 | 0.2016 | 0.2013 | 0.2008 | 0.1999 | 0.1990 | 0.1982 |

对照（定容，以**充气压力**为准；气液比 3:5）：

| 充气表压 / MPa | 0.10 | 0.25 | 0.50 | 1.00 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|
| 平衡 CO₂ 分压 / atm | 0.812 | 1.451 | 2.528 | 4.716 | 6.952 | 9.237 |
| **pH** | **7.0784** | **6.8287** | **6.5912** | **6.3270** | **6.1651** | **6.0485** |

**同一表压下两种口径相差 0.05～0.32 个 pH 单位，给压力之前必须先确认口径。**

KNO₂ 敏感性（20 mM）：ΔpH = −0.0042（各压力档相同），对应 ΔE = −0.25 mV ——
相对压力校准中的几十 mV 量级可以忽略。仓库主输入为无盐 KHCO₃ 示例；
实际体系的盐组分应按配制方案另行加入 input/。

---

## 6  校验

`src/verify_results.py` 做 7 组共 84 项检查：

| 组 | 检查 | 判据 |
|---|---|---|
| A | 目标 CO₂ 分压达成；气相未耗尽 | 相对偏差 ≤ 1×10⁻⁸；无 “dissolved completely” |
| B | 电荷平衡；K / Nti 质量守恒；碳质量守恒（含气相交换）| ≤ 1×10⁻⁶；≤ 1×10⁻⁹；≤ 1×10⁻⁸ |
| C | 总碱度、总碳与完整物种求和一致 | ≤ 1×10⁻⁹ |
| D | mol/L 与 mol/kg water 换算 | 因子 = mass_H₂O / SOLN_VOL |
| E | **与独立解析解交叉核对**（Davies + Peng-Robinson，与 PHREEQC 无共用）| \|ΔpH\| ≤ 0.02（实测 ≤ 0.0159）|
| F | 内部一致性：离子强度两种算法互校 | ≤ 1×10⁻⁶ |
| G | 定容对照的容器碳守恒；KNO₂ 敏感性 | ≤ 1×10⁻⁵ mol/kg（实测 ≤ 3×10⁻⁷）；\|ΔpH\| ≤ 0.01 |
| **H** | **NO₂⁻ 路线独立验证**（见 §7） | Nti 质量守恒、碱度含 HNtiO₂、电荷与碳守恒、与独立解析解交叉核对 \|ΔpH\| ≤ 0.02（实测 0.0185）、质子化常数反算 log K = 3.16±0.01、NtiO₂⁻ 活度系数 = 数据库 NO₂⁻（差 ≤ 0.05%）|

**E 组是真正的独立交叉核对**（独立程序不使用 PHREEQC 的任何输出）；
其余各组是对同一份 PHREEQC 输出的内部一致性检查，不应被当作独立验证。

定容对照工况的平衡分压由外层迭代求得：每轮用 PHREEQC 实际算出的 (p, DIC) 作为新锚点，
容器碳守恒残差从 1.2×10⁻² 收敛到 ≤ 3×10⁻⁷ mol/kg water。

---

## 7  已知注意事项

**（1）数据库的 CO2 物种即表观 CO₂\*。** phreeqc.dat 无 H₂CO₃ 物种，
CO₂(aq) 与 H₂CO₃ 已合并；由 log K = −1.8 与 −log(K_a1·K_a2) = 16.681 锁定。
H₂CO₃ 占溶解态 CO₂\* 的 0.170%（25 °C 纯水取值，仅由温度决定）。
因该部分碳已含在 PHREEQC 的 Total CO2 内，**不能再另行计入总无机碳**。

**（2）(CO₂)₂ 是数据库内置的算法项**，定义处注释即为
activity correction for CO₂ solubility at high P, T，等效于水溶液中 CO₂ 的第二维里系数，
不是经独立测定的化学物种；其“折合碳”仅为质量衡算记账量。

**（3）总碱度是 0.204 eq/kg water（= 0.202～0.199 eq/L，随压力略降）。**
求和必须计入中性络合物 KHCO₃⁰ 的一个当量：
Alk = [HCO₃⁻] + 2[CO₃²⁻] + [KHCO₃⁰] + [OH⁻] − [H⁺]（加入 HNO₂ 时再减去其质子化部分）。
输入设的是 0.2 mol/L，换算到 mol/kg water 后为 0.2041，与设定值一致。

**（4）离子强度用游离 K⁺**（总 K 减去中性络合物 KHCO₃ 中的 K），不是总 K。

**（5）读 PHREEQC 输出时不要用结果段末尾的汇总行取气相分压。** 该行形如
CO2(g) ... Pressure 20.7 atm，只有 2 位有效数字。精确值在输出开头的输入回显段；
本包统一读 `SELECTED_OUTPUT -high_precision` 生成的 TSV。

**（6）亚硝酸盐必须用独立组分 Nti，不能直接用数据库的 NO₂⁻。**
直接写 §N(+3) 0.02§ 时，PHREEQC 的初始解会做氧化还原平衡，把氮拆散：

| 价态 | 总量 | 实际物种 |
|---|---|---|
| N(−3) | 0 | — |
| N(0) | 8.17×10⁻³ | N₂ = 4.09×10⁻³ |
| **N(3)** | **7.84×10⁻¹³** | **NO₂⁻ ≈ 0（几乎全被消耗）** |
| N(5) | 1.23×10⁻² | NO₃⁻ = 1.23×10⁻² |

亚硝酸盐被歧化掉了。本包用独立组分 §Nti§ 规避：§NtiO2⁻§ 继承数据库 NO₂⁻ 的活度与体积参数
（§-gamma 3 0§、§-Vm 5.5864 5.859 3.3472 -3.0212 1.1847§），另加 §HNtiO2§ 的质子化平衡
（log K = 3.16）。该 pKa 取自 da Silva Gabriel, Kennedy E M, Dlugogorski B Z (2006)
*Ab Initio Procedure for Aqueous-Phase pKa Calculation: The Acidity of Nitrous Acid*,
J. Phys. Chem. A **110**, 11371–11376, doi:10.1021/jp0639243。

已验证 Nti 路线的正确性（§verify_results.py§ 的 H 组，共 42 项）：

- Nti 质量守恒（偏差 ≤ 1×10⁻¹⁴ mol）
- 碱度 = 完整物种求和（**含 −[HNtiO₂]**），与 PHREEQC 报告值吻合到 ≤1×10⁻⁹ eq/kg
- 电荷平衡 ≤ 1×10⁻¹¹；碳质量守恒 ≤ 1×10⁻¹³ mol
- 与**独立解析解**（含亚硝酸盐项）交叉核对：最大 \|ΔpH\| = 0.0185
- 由 PHREEQC 自己的活度反算 HNO₂ 质子化常数：log K = 3.1600（1 atm）～3.1690（2 MPa）；
  高压端的漂移来自 PHREEQC 对 log K 的压力修正（HNtiO₂ 未给独立 Vm），非计算错误
- **NtiO₂⁻ 的活度系数与数据库真 NO₂⁻ 逐点相差仅 0.00%–0.05%**（§input/equilibrium_co2_realno2.pqi§ 对照算例），
  说明替代物与数据库物种的活度模型完全一致

---

## 8  许可证

本仓库代码以 MIT 许可证发布（见 LICENSE）。

随包重新分发的 PHREEQC v3.8.6（phreeqc/phreeqc.exe 与 phreeqc/phreeqc.dat）
属美国地质调查局（USGS）公共领域作品；phreeqc/build_phreeqc.sh 从官方源码
发行版下载并编译。详见 <https://www.usgs.gov/software/phreeqc-version-3>。

---

## 9  引用

1. Parkhurst D L, Appelo C A J. Description of input and examples for PHREEQC version 3:
   A computer program for speciation, batch-reaction, one-dimensional transport,
   and inverse geochemical calculations. U.S. Geological Survey Techniques and Methods,
   Report 6-A43, 2013. https://doi.org/10.3133/tm6A43
2. Peng D Y. A simple algorithm for calculating phase equilibria with local and global
   minimization methods. Fluid Phase Equilibria, 1989, 54(3): 381–398.
3. Charlton S R, Parkhurst D L. Modules based on the geochemical model PHREEQC for use in
   scripting and programming languages. Computers & Geosciences, 2011, 37(10): 1653–1663.
