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
