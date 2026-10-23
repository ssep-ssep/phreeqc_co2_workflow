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
para("压力保留比例在 %.1f%%～%.1f%% 之间（见表 4），且与充气压力高低基本无关——这是定容体系的固有特征。"
     % (min(100*(x["pCO2"]+PH2O)/x["Pabs"] for x in R2),
        max(100*(x["pCO2"]+PH2O)/x["Pabs"] for x in R2)))

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
     "溶入液体的 CO₂ 反而更少。因此必须先与使用方确认：给出的压力是充气时的设定值，"
     "还是釜内稳定的实测值。"
     % (min(R2[i]["pH"]-R3[i]["pH"] for i in range(6)),
        max(R2[i]["pH"]-R3[i]["pH"] for i in range(6))))

# ================= 3 碳物种分布 =================
h1("3  电解液中碳物种分布")
def species_block(rr, t):
    """碳物种分布: 浓度与占比合并为一张表"""
    cap(t)
    rows=[]
    for key,label,cf,pf in [("CO2","CO₂*（溶解态 CO₂）","%.5f","%.2f"),
                            ("H1","HCO₃⁻","%.5f","%.2f"),
                            ("H3","CO₃²⁻","%.2e","%.4f"),
                            ("KHc","KHCO₃","%.5f","%.2f")]:
        rows.append([label+" 浓度 / mol·L⁻¹"]+[cf%x[key] for x in rr])
        rows.append([label+" 占总碳"]+[(pf+"%%")%(100*x[key]/x["DIC"]) for x in rr])
    rows.append(["CO₂ 溶解度活度修正项 [(CO₂)₂] 浓度 / mol·L⁻¹"]+["%.2e"%x["D2"] for x in rr])
    rows.append(["└ 折合碳记账占比（非独立物种）"]+["%.2f%%"%(100*2*x["D2"]/x["DIC"]) for x in rr])
    rows.append(["其中 H₂CO₃ 占溶解态 CO₂*"]+["0.170%"]*len(rr))
    rows.append(["总无机碳 / mol·L⁻¹"]+["%.5f"%x["DIC"] for x in rr])
    mktable(["组分"]+["%.2f"%x["g"] for x in rr], rows, widths=[6.2]+[1.5]*len(rr))

species_block(R2,"表00  组 2  电解液中碳物种分布")
species_block(R3,"表00  组 3  电解液中碳物种分布")
nt("注 1：表中 CO₂* 为溶解态 CO₂ 的总量。热力学数据库 phreeqc.dat 未区分 CO₂(aq) 与 H₂CO₃，"
   "二者按分配系数 K_h = 1.70×10⁻³（25 °C）合并计入 CO₂*，其中 H₂CO₃ 占 0.170%，"
   "该比例仅由温度决定，与压力和 pH 无关。")
nt("注 2：(CO₂)₂ 并非本工作主动引入的建模假设，而是 phreeqc.dat 内置的算法项，"
   "由反应式 2 CO₂ = (CO₂)₂（log K = −1.8）自动生成，其定义处注释即为"
   "“activity correction for CO₂ solubility at high P, T”。它是 CO₂ 溶解度非理想性的修正，"
   "等效于水溶液中 CO₂ 的第二维里系数，并非经独立测定的化学物种。"
   "因 PHREEQC 的碳衡算按每摩尔计入 2 个碳，上表中的“折合碳记账占比”仅为质量衡算的记账量，"
   "不具实验含义。")
