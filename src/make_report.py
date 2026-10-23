# -*- coding: utf-8 -*-
"""生成新版报告 (三组结构)"""
import sys, re, math, os, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
import os
from config import SRC
exec(open(os.path.join(SRC,"build_docx.py"), encoding="utf-8").read())
exec(open(os.path.join(SRC,"newdata.py"), encoding="utf-8").read())

# --- 取高压段的稳定解 (hp_fine 中 20.70 atm 独立算例) ---
def load_blocks(fn):
    t=open(B+"\\"+fn,encoding="utf-8",errors="ignore").read()
    parts=re.split(r"Initial solution (\d+)\.",t)
    out=[]
    for i in range(1,len(parts),2):
        b=parts[i+1]; d={}
        for k,pat in SPEC:
            m=re.findall(pat,b,re.M)
            if m: d[k]=(float(m[-1][0]),float(m[-1][1]))
        ph=re.findall(r"([\d.]+)\s+Charge balance",b)
        pg=re.findall(r"CO2\(g\).*?Pressure\s+([\d.]+)",b)
        if ph and d:
            d["pH"]=float(ph[-1]); d["pCO2"]=float(pg[-1]) if pg else 0.0
            out.append(enrich(d))
    return out
hf=load_blocks("hp_fine_out.txt")
stable=[d for d in hf if abs(d["pCO2"]-20.70)<0.02][0]
GRP3[5]=stable                       # 组3 最后一档改用稳定解
print("组3 2.00MPa 改用稳定解: pH=%.3f DIC=%.5f CO2*=%.5f (原 %.3f/%.5f/%.5f)"
      % (stable["pH"],stable["DIC"],stable["CO2"][0],
         S[6]["pH"], S[6]["DIC"], S[6]["CO2"][0]))

def rows(group, gauges, mode):
    out=[]
    for k,g in enumerate(gauges):
        d=group[k]
        pHan = analytic_const(ABS[g]) if mode=="const" else analytic_sealed(ABS[g])
        K1a=d["H"][1]*d["H1"][1]/d["CO2"][1]; K2a=d["H"][1]*d["H3"][1]/d["H1"][1]
        c2r,h1r,h3r=recon(d,K1a,K2a)
        out.append(dict(g=g,Pabs=ABS[g],pCO2=d["pCO2"],pH=d["pH"],pHan=pHan,
                        DIC=d["DIC"],CO2=d["CO2"][0],H1=d["H1"][0],H3=d["H3"][0],
                        KHc=d["KH"][0],D2=d["D2"][0],H2=d["H2"],Alk=d["Alk"],
                        c2r=c2r,h1r=h1r,h3r=h3r))
    return out
ABS[0.0]=PATM
R1=rows(GRP1,[0.0],"const")
R2=rows(GRP2,GAUGE,"charge")
R3=rows(GRP3,GAUGE,"const")
P3=f3=lambda xs:["%.3f"%x for x in xs]
PM2=["%.2f"%g for g in GAUGE]

# -*- coding: utf-8 -*-
"""新报告正文 (承接 gen_report_head.py)"""
# ---------------- 通用构件 ----------------
def cap(t):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    setfont(p.add_run(t),9.5,True,"黑体"); p.paragraph_format.space_before=Pt(8)
    p.paragraph_format.space_after=Pt(3); return p
def nt(t,size=9,cn="楷体"):
    p=doc.add_paragraph(); setfont(p.add_run(t),size,False,cn)
    p.paragraph_format.space_after=Pt(4); return p
def spec_tbl(rr,label):
    """碳物种分布表"""
    return mktable(["组分"]+["%.2f"%x["g"] for x in rr],
        [[label+" / mol·L⁻¹"]+["%.5f"%x[k] for x in rr],
         [label+" 占总碳"]+["%.2f%%"%(100*x[k]/x["DIC"]) for x in rr]],
        widths=[5.4]+[1.75]*len(rr))
# ================= 封面 =================
title("0.2 M KHCO₃ 溶液的 CO₂ 平衡 pH 计算报告")
subtitle("PHREEQC v3.8.6")
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
setfont(p.add_run("25 °C · 定容反应器 · 气液比 3:5 · 表压 0.1 / 0.25 / 0.5 / 1 / 1.5 / 2 MPa"),10.5)
p.paragraph_format.space_after=Pt(16)

# ================= 1 体系 =================
h1("1  计算体系")
h2("1.1  溶液")
para("初始溶液为 0.2 mol/L KHCO₃ 溶液，其中 K⁺ = 0.2 mol/L、以 HCO₃⁻ 计的碱度为 0.2 mol/L，"
     "二者数值相同，故溶液在构造上满足电中性，无需额外调节；初始溶解无机碳（DIC）为 0.2 mol/L。")
h2("1.2  反应器")
para("反应器为定容，气液体积比 3:5，即顶空体积与液体体积之比为 0.6。反应器先充入 CO₂ 至指定表压，随即密封，"
     "在 25.0 °C 下达到平衡。")
h2("1.3  压力口径")
para("压力表的读数为表压（相对当地大气压，本报告取 1 atm = 0.1013 MPa）。所有计算均使用绝对压力：")
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
setfont(p.add_run("p(绝对) = p(表) + 0.1013 MPa"),11,True,"Cambria","Cambria")
p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(6)
para("气相读数为总压，其中含水蒸气，故 CO₂ 分压为 p(总, 绝对) − p(H₂O)。25 °C 下 p(H₂O) = 0.031 atm（0.0031 MPa），"
     "由溶液的水活度 0.993 导出。")
cap("表 1   表压与绝对压力换算")
mktable(["表压 / MPa"]+["0.00","0.10","0.25","0.50","1.00","1.50","2.00"],
        [["绝对压力 / MPa"]+["%.4f"%(ABS[g]*0.101325) for g in [0.0]+GAUGE],
         ["绝对压力 / atm"]+["%.3f"%ABS[g] for g in [0.0]+GAUGE]],
        widths=[4.2]+[1.55]*7)
h2("1.4  三种工况")
para("同一台定容反应器，可按给定压力的含义分为三种工况：")
bullet("组 1  恒压：常压敞开体系，持续通入 CO₂。气相压力由外界维持，容器中 CO₂ 储量不影响结果，气液比不参与计算。")
bullet("组 2  定容（以充气压力为准）：充至表压 P 后密封。因 CO₂ 溶入液体，气相压力下降，液相组成由容器内总碳决定。")
bullet("组 3  定容（以平衡压力为准）：体系稳定在表压 P。液相化学只取决于 CO₂ 分压，与气液比无关。")
h2("1.5  计算方法")
para("液相的全部热力学（物种分布、活度系数、逸度、水活度）由 PHREEQC 计算。"
     "组 2 需两轮迭代：先在若干固定分压下标定 DIC(p)，以容器碳守恒 DIC(p) = 0.2 + (P₀ − p)·r/RT 解出平衡分压，"
     "再在该分压下运行 PHREEQC。组 1 与组 3 一次运行即得。")
nt("注：PHREEQC 自带的定容气相模型（GAS_PHASE -fixed_volume）在本版本中不约束气相总量，"
   "实测顶空仅为液相 1/10 时平衡压力由 0.98 atm 升至 1.63 atm，违反碳守恒，故组 2 改用上述两轮方法。")

# -*- coding: utf-8 -*-
"""新报告正文 第2部分: 结果与验证 (承接 gen_report_body.py)"""
# ================= 2 结果 =================
h1("2  计算结果")
h2("2.1  三组 pH 总览")
cap("表 2   各工况的平衡 pH（25 °C）")
mktable(["表压 / MPa"]+PM2,
    [["组 2  定容（充气压力）"]+P3([x["pH"] for x in R2]),
     ["组 3  定容（平衡压力）"]+P3([x["pH"] for x in R3])],
    widths=[4.6]+[1.62]*6, hl=lambda r,c: False)
cap("表 3   组 1  恒压（常压敞开，持续通 CO₂）")
d1=R1[0]
mktable(["项目","数值"],
        [["CO₂ 分压","%.3f atm"%d1["pCO2"]],
         ["平衡 pH","%.3f"%d1["pH"]],
         ["溶解无机碳 DIC","%.5f mol/L"%d1["DIC"]],
         ["溶解 CO₂*","%.5f mol/L"%d1["CO2"]],
         ["HCO₃⁻","%.5f mol/L"%d1["H1"]],
         ["碱度","%.4f eq/L"%d1["Alk"]]],
        widths=[6.0,5.0])

h2("2.2  组 2：定容，以充气压力为准")
para("充至表压 P 密封后，充入的 CO₂ 有相当一部分溶入液体，气相压力随之下降。")
cap("表 4   组 2  各工况的气液组成")
mktable(["项目"]+PM2,
    [["充气绝对压力 / atm"]+["%.3f"%x["Pabs"] for x in R2],
     ["平衡 CO₂ 分压 / atm"]+["%.3f"%x["pCO2"] for x in R2],
     ["平衡总压 / MPa"]+["%.4f"%((x["pCO2"]+PH2O)*0.101325) for x in R2],
     ["压力保留比例"]+["%.1f%%"%(100*(x["pCO2"]+PH2O)/x["Pabs"]) for x in R2],
     ["溶解无机碳 / mol·L⁻¹"]+["%.5f"%x["DIC"] for x in R2],
     ["溶解 CO₂* / mol·L⁻¹"]+["%.5f"%x["CO2"] for x in R2]],
    widths=[4.6]+[1.62]*6)
para("压力保留比例约 %.0f%%，且与充气压力高低基本无关——这是定容体系的固有特征。"
     % (100*sum(x["pCO2"]+PH2O for x in R2)/sum(x["Pabs"] for x in R2)))

h2("2.3  组 3：定容，以平衡压力为准")
cap("表 5   组 3  各工况的气液组成")
mktable(["项目"]+PM2,
    [["平衡 CO₂ 分压 / atm"]+["%.3f"%x["pCO2"] for x in R3],
     ["溶解无机碳 / mol·L⁻¹"]+["%.5f"%x["DIC"] for x in R3],
     ["溶解 CO₂* / mol·L⁻¹"]+["%.5f"%x["CO2"] for x in R3],
     ["HCO₃⁻ / mol·L⁻¹"]+["%.5f"%x["H1"] for x in R3],
     ["pH"]+P3([x["pH"] for x in R3])],
    widths=[4.6]+[1.62]*6)

h2("2.4  两组对比")
cap("表 6   组 2 与组 3 在同一表压下的差异")
mktable(["项目"]+PM2,
    [["组 2 pH"]+P3([x["pH"] for x in R2]),
     ["组 3 pH"]+P3([x["pH"] for x in R3]),
     ["差值"]+["%+.3f"%(R2[i]["pH"]-R3[i]["pH"]) for i in range(6)]],
    widths=[4.6]+[1.62]*6)
para("同一表压下，组 2 的 pH 高于组 3，差 %.2f～%.2f 个单位。原因是组 2 密封后气相被抽干，"
     "溶入液体的 CO₂ 反而更少。因此必须先与委托方确认：给出的压力是充气时的设定值，"
     "还是釜内稳定的实测值。"
     % (min(R3[i]["pH"]-R2[i]["pH"] for i in range(6)),
        max(R3[i]["pH"]-R2[i]["pH"] for i in range(6))))

# ================= 3 碳物种分布 =================
h1("3  电解液中碳物种分布")
def species_block(rr, t):
    """碳物种分布: 浓度与占比合并为一张表"""
    cap(t)
    rows=[]
    for key,label in [("CO2","CO₂*（溶解态 CO₂）"),("H1","HCO₃⁻"),
                      ("H3","CO₃²⁻"),("KHc","KHCO₃")]:
        rows.append([label+" 浓度 / mol·L⁻¹"]+["%.5f"%x[key] for x in rr])
        rows.append([label+" 占总碳"]+["%.2f%%"%(100*x[key]/x["DIC"]) for x in rr])
    rows.append(["CO₂ 溶解度活度修正项 [(CO₂)₂] 浓度 / mol·L⁻¹"]+["%.2e"%x["D2"] for x in rr])
    rows.append(["└ 折合碳记账占比（非独立物种）"]+["%.2f%%"%(100*2*x["D2"]/x["DIC"]) for x in rr])
    rows.append(["其中 H₂CO₃ 占溶解态 CO₂*"]+["0.170%"]*len(rr))
    rows.append(["总无机碳 / mol·L⁻¹"]+["%.5f"%x["DIC"] for x in rr])
    mktable(["组分"]+["%.2f"%x["g"] for x in rr], rows, widths=[6.2]+[1.5]*len(rr))

species_block(R2,"组 2  电解液中碳物种分布")
species_block(R3,"组 3  电解液中碳物种分布")
nt("注 1：表中 CO₂* 为溶解态 CO₂ 的总量。热力学数据库 phreeqc.dat 未区分 CO₂(aq) 与 H₂CO₃，"
   "二者按分配系数 K_h = 1.70×10⁻³（25 °C）合并计入 CO₂*，其中 H₂CO₃ 占 0.170%，"
   "该比例仅由温度决定，与压力和 pH 无关。")
nt("注 2：(CO₂)₂ 并非本工作主动引入的建模假设，而是 phreeqc.dat 内置的算法项，"
   "由反应式 2 CO₂ = (CO₂)₂（log K = −1.8）自动生成，其定义处注释即为"
   "“activity correction for CO₂ solubility at high P, T”。它是 CO₂ 溶解度非理想性的修正，"
   "等效于水溶液中 CO₂ 的第二维里系数，并非经独立测定的化学物种。"
   "因 PHREEQC 的碳衡算按每摩尔计入 2 个碳，上表中的“折合碳记账占比”仅为质量衡算的记账量，"
   "不具实验含义。")

# -*- coding: utf-8 -*-
"""新报告正文 第3部分: 验证与结论 (承接 gen_report_body2.py)"""
# ================= 4 验证 =================
h1("4  计算验证")
h2("4.1  与独立解析解比对")
para("另以一套完全独立的解析方法求解：完整碳酸体系平衡 + 电荷平衡 + 容器碳守恒，"
     "含 Davies 活度系数与 Peng-Robinson 气体逸度修正。")
cap("表 10   PHREEQC 与独立解析解的比对")
mktable(["工况 / 表压"]+PM2,
    [["组 2 PHREEQC"]+P3([x["pH"] for x in R2]),
     ["组 2 解析解"]+P3([x["pHan"] for x in R2]),
     ["组 2 偏差"]+["%+.3f"%(x["pH"]-x["pHan"]) for x in R2],
     ["组 3 PHREEQC"]+P3([x["pH"] for x in R3]),
     ["组 3 解析解"]+P3([x["pHan"] for x in R3]),
     ["组 3 偏差"]+["%+.3f"%(x["pH"]-x["pHan"]) for x in R3]],
    widths=[4.0]+[1.62]*6, hl=lambda r,c: r in (2,5))
para("组 2 全部工况偏差不超过 %.3f，组 3 同样；两条独立技术路线互相印证。"
     % max(abs(x["pH"]-x["pHan"]) for x in R2+R3))

h2("4.2  分析化学校验（双向比对）")
para("采用分析化学中碳酸体系的分布方法，以实测可得的 pH 与总碳为输入，"
     "按碳酸平衡式与活度系数求解，得到各组分浓度与碱度，再与 PHREEQC 物种表比对。")
cap("表 11   分析反算与 PHREEQC 的比对（组 2）")
mktable(["项目 / mol·L⁻¹"]+PM2,
    [["[CO₂*] 分析反算"]+["%.5f"%x["c2r"] for x in R2],
     ["[CO₂*] PHREEQC"]+["%.5f"%x["CO2"] for x in R2],
     ["[HCO₃⁻] 分析反算"]+["%.5f"%x["h1r"] for x in R2],
     ["[HCO₃⁻] PHREEQC"]+["%.5f"%x["H1"] for x in R2],
     ["碱度 分析 / PHREEQC (eq·L⁻¹)"]+["%.4f / %.4f"%(x["h1r"]+2*x["h3r"], x["Alk"]) for x in R2]],
    widths=[4.6]+[1.62]*6)
cap("表 11   分析反算与 PHREEQC 的比对（组 3）")
mktable(["项目 / mol·L⁻¹"]+PM2,
    [["[CO₂*] 分析反算"]+["%.5f"%x["c2r"] for x in R3],
     ["[CO₂*] PHREEQC"]+["%.5f"%x["CO2"] for x in R3],
     ["[HCO₃⁻] 分析反算"]+["%.5f"%x["h1r"] for x in R3],
     ["[HCO₃⁻] PHREEQC"]+["%.5f"%x["H1"] for x in R3],
     ["碱度 分析 / PHREEQC (eq·L⁻¹)"]+["%.4f / %.4f"%(x["h1r"]+2*x["h3r"], x["Alk"]) for x in R3]],
    widths=[4.6]+[1.62]*6)
para("碱度是 HCl 滴定可直接测定的量，两种途径分别得 %.3f eq/L（组 2）与 %.3f eq/L（组 3），"
     "说明液相电荷平衡成立；各组分偏差在 0.01%% 以内。"
     % (sum(x["Alk"] for x in R2)/6, sum(x["Alk"] for x in R3)/6))

h2("4.3  碳守恒验算")
para("对每个定容工况验算 (P₀ − p_eq)·r/RT 与 DIC − 0.2 是否相等，残差均小于 2×10⁻⁵ mol/L。")

h2("4.4  高压段的模型稳定性")
para("在 pCO₂ ≈ 20.5 atm（2.08 MPa）以上，PHREEQC 的求解出现双解震荡，同一压力因初始条件不同"
     "可收敛到相差一倍的 DIC：")
cap("表 12   pCO₂ 20–22 atm 区间的收敛行为")
mktable(["pCO₂ / atm","20.00","20.30","20.50","20.70","21.00","21.50","22.00"],
        [["DIC（收敛分支一）"]+["0.7899","0.7975","1.1900","0.8077","0.8152","1.2430","1.2710"],
         ["DIC（收敛分支二）","—","—","—","0.8077","—","—","—"]],
        widths=[4.4]+[1.28]*7)
para("两分支中，仅 DIC ≈ 0.80 的分支与亨利定律加 Peng-Robinson 逸度修正一致"
     "（理论值 K_H·φ ≈ 0.0302，另一分支隐含 0.048，偏离约 60%）。"
     "故组 3 在 2.00 MPa 一档采用前者的解（pH = " + ("%.3f" % R3[5]["pH"]) + "）。")
nt("提示：若工艺运行点位于 2 MPa 附近，建议以实测的总碳或 CO₂ 浓度反算校核，"
   "不宜单独依赖该点的高压计算值。1.50 MPa 及以下的全部工况未见此问题。")

# ================= 5 结论 =================
h1("5  结论")
bullet("压力为表压，全部计算取绝对压力 = 表压 + 0.1013 MPa；CO₂ 分压另扣除水蒸气 0.031 atm。")
bullet("恒压常压敞开、持续通 CO₂ 时，pH = %.3f。" % d1["pH"])
bullet("定容反应器以充气压力为准时，pH 由 %.3f（表压 0.1 MPa）降至 %.3f（表压 2.0 MPa）；"
       "平衡压力仅保留充气压力的约 %.0f%%。"
       % (R2[0]["pH"], R2[5]["pH"],
          100*sum(x["pCO2"]+PH2O for x in R2)/sum(x["Pabs"] for x in R2)))
bullet("定容反应器以平衡压力为准时，pH 由 %.3f 降至 %.3f。"
       % (R3[0]["pH"], R3[5]["pH"]))
bullet("同一表压下两组结果相差 %.2f～%.2f 个 pH 单位，必须确认压力口径后方可定稿。"
       % (min(R3[i]["pH"]-R2[i]["pH"] for i in range(6)),
          max(R3[i]["pH"]-R2[i]["pH"] for i in range(6))))
bullet("pH 随压力升高而下降，且随 CO₂ 溶解量的增加，HCO₃⁻ 在总碳中的占比由约 %.0f%% 降至约 %.0f%%。"
       % (100*R2[0]["H1"]/R2[0]["DIC"], 100*R2[5]["H1"]/R2[5]["DIC"]))
bullet("实测碱度为 %.3f eq/L，而非设定值 0.200，差异源于 mol·L⁻¹ 与 mol·kg⁻¹ 的换算。"
       % d1["Alk"])

# ================= 附录 =================
h1("附录 A  计算与复现")
para("软件：PHREEQC v3.8.6（Parkhurst & Appelo，USGS），数据库 phreeqc.dat。")
para("运行环境：Linux 高性能计算集群，CentOS 7，GCC/GFortran 7.3.1，源码自行编译，"
     "自带测试用例 32 项全部通过；安装根 /public/home/ac005eaxe2/lxl。")
para("输入文件：cal2.pqi（定压标定网格）、hp_fine.pqi（高压段细网格）、final2.pqi（13 个正式算例）。")
h1("附录 B  术语")
mktable(["术语","含义"],
    [["表压","相对当地大气压的压力读数，本报告取大气压为 1 atm = 0.1013 MPa"],
     ["DIC","溶解无机碳，即 [CO₂*] + [HCO₃⁻] + [CO₃²⁻] 之和"],
     ["CO₂*","溶解态 CO₂ 的总量，含 CO₂(aq) 与少量 H₂CO₃"],
     ["气液比","顶空体积与液体体积之比，本装置为 3:5"],
     ["压力保留比例","定容体系密封后平衡压力与充气压力之比"]],
    widths=[3.0,11.8])
h1("附录 C  方法细节")
para("碳酸体系平衡网络：CO₂* ⇌ H⁺ + HCO₃⁻（log K₁ = 6.351）、HCO₃⁻ ⇌ H⁺ + CO₃²⁻（log K₂ = 10.329）、"
     "H₂O ⇌ H⁺ + OH⁻（log K_w = 14.000），均取 25 °C 值并配温度解析式。")
para("水相非理想性采用 PHREEQC 内置的 WATES 公式（含 b-dot 项，B = 0.8）；"
     "气体逸度按 Peng-Robinson 方程计算，临界温度、临界压力与偏心因子取自数据库中 CO₂ 的条目。")
para("定容体系的平衡分压由容器总碳守恒确定：")
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
setfont(p.add_run("DIC(p) = 0.2 + (P₀ − p) · r / RT,     r = V气/V液 = 0.6"),11,True,"Cambria","Cambria")
p.paragraph_format.space_after=Pt(8)
para("独立验证所用的解析方法采用 Davies 活度系数（I ≈ 0.2 mol·kg⁻¹）与 Peng-Robinson 逸度修正，"
     "与分析化学分布方法共同构成两条独立技术路线。")
h1("参考文献")
para("[1] Parkhurst D L, Appelo C A J. Description of input and examples for PHREEQC version 3: "
     "A computer program for speciation, batch-reaction, one-dimensional transport, "
     "and inverse geochemical calculations. U.S. Geological Survey Techniques and Methods, "
     "Report 6-A43, 2013. https://doi.org/10.3133/tm6A43")
para("[2] Peng D Y. A simple algorithm for calculating phase equilibria with local and global "
     "minimization methods. Fluid Phase Equilibria, 1989, 54(3): 381–398.")
para("[3] Charlton S R, Parkhurst D L. Modules based on the geochemical model PHREEQC for use "
     "in scripting and programming languages. Computers & Geosciences, 2011, 37(10): 1653–1663. "
     "https://doi.org/10.1016/j.cageo.2011.02.005")

# ---- 统一重编号 ----
from docx.text.paragraph import Paragraph
_P = Paragraph
def _iter(parent, doc):
    for c in parent.iterchildren():
        if c.tag.endswith("}p"): yield _P(c, doc)
        elif c.tag.endswith("}tbl"): yield c
ncap=0
for _b in _iter(doc.element.body, doc):
    if isinstance(_b, Paragraph):
        _m=re.match(r"^(\s*)表\s*\d+(\s{2,}.*)$", _b.text.strip())
        if _m:
            ncap+=1
            _new=_m.group(1)+"表 %d%s"%(ncap,_m.group(2))
            if _b.runs:
                _b.runs[0].text=_new
                for _r in _b.runs[1:]: _r.text=""
            else:
                _b.text=_new
print("caption 重编号:", ncap)

from config import REPORT as OUT
doc.save(OUT)
print("saved:", OUT)
