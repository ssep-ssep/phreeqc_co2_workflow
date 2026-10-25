# -*- coding: utf-8 -*-
"""
khbco3_pH_analytic.py —— 独立解析解 (不依赖 PHREEQC)

用于与 PHREEQC 结果交叉核对, 故与 PHREEQC 保持同一记账口径:
  * 基准: mol/kg water (活度系数的自然基准); PHREEQC 的 mol/L 输入需先换算
  * 总碱度 (carbonate alkalinity)、总 K+、离子强度 I 三者分开处理:
    I 由各物种电荷实时迭代求出, 不用碱度代替
  * 气体参数是 **CO2 分压** (atm), 不是总压

修正记录 (2026-10-24 代码审查):
  - van't Hoff 符号: ln[K(T)/K(T0)] = -dH/R*(1/T - 1/T0)。原式用 +dH/R*(1/T-1/T0),
    对吸热反应会使 K 随温度升高而减小, 方向反了。T = T0 = 25 C 时两者相同, 此前结果不受影响。
  - 离子强度不再用碱度代替, 改为由物种电荷迭代。
  - 函数参数由总压改为 CO2 分压。
"""
import math

R    = 8.314462618      # J/(mol*K)
T0   = 298.15          # K, 25 C
pK1_0, pK2_0, pKw_0   = 6.352, 10.329, 14.00
KH_0                  = 0.0340   # mol/(kg*atm), 25 C, CO2*
dH1, dH2, dHKw, dHK   = 19.5e3, 20.2e3, 55800.0, -19.4e3   # J/mol

# Debye-Huckel A 逐点表 (C -> A*1e10)
_A = [(0,0.5438),(15,0.5110),(25,0.5092),(30,0.5078),(40,0.4883),(50,0.4750),(100,0.4522)]
def A_DH(Tc):
    for i in range(len(_A)-1):
        if Tc <= _A[i+1][0]:
            f = (Tc-_A[i][0])/(_A[i+1][0]-_A[i][0])
            return _A[i][1] + f*(_A[i+1][1]-_A[i][1])
    return 0.45

def consts(T):
    """25 C 为基准, 按 van't Hoff 外推到 T"""
    def vh(dH):
        return math.exp(-dH/R*(1/T - 1/T0))
    return dict(K1 = 10**-pK1_0 * vh(dH1),
                K2 = 10**-pK2_0 * vh(dH2),
                Kw = 10**-pKw_0 * vh(dHKw),
                KH = KH_0       * vh(dHK))

def lgamm(z, I, A):
    return -A*z*z*(math.sqrt(I)/(1+math.sqrt(I)) - 0.3*I)

def pr_phi(T, P_atm):
    """Peng-Robinson 纯组分 CO2 逸度系数, 输入压力单位 atm"""
    P_bar = P_atm * 1.01325
    Tc, Pc, w = 304.1282, 73.773, 0.22394
    Tr, Pr = T/Tc, P_bar/Pc
    kappa = 0.37464 + 1.54226*w - 0.26992*w*w
    alpha = (1 + kappa*(1 - math.sqrt(Tr)))**2
    Aa = alpha*0.45724*Pr/Tr/Tr
    Bb = 0.07780*Pr/Tr
    c2 = -(1-Bb); c1 = Aa-3*Bb*Bb-2*Bb; c0 = -(Aa*Bb-Bb*Bb-Bb**3)
    z = 1.0
    for _ in range(300):
        f = z*z*z + c2*z*z + c1*z + c0
        df = 3*z*z + 2*c2*z + c1
        z -= f/df
    s2 = math.sqrt(2)
    lnf = (z-1) - math.log(z-Bb) - Aa/(2*s2*Bb)*math.log((z+(1+s2)*Bb)/(z+(1-s2)*Bb))
    return math.exp(lnf)

def _newton(f, x0, tol=1e-16):
    x = x0
    for _ in range(400):
        d = max(abs(x), 1e-14)*1e-8
        f0, f1 = f(x), f(x+d)
        if f1 == f0: break
        x -= f0*d/(f1-f0)
        if abs(f0*d/(f1-f0)) < tol: break
    return x

def pH_open(T, p_co2_atm, alk_kgw=0.2, k_kgw=None, nitrite=0.0,
            activity=True, fugacity=True, pka_hno2=3.16):
    """恒压 (规定 CO2 分压) 体系的平衡 pH。

    参数
      p_co2_atm  平衡 CO2 分压 (atm) —— 不是总压
      alk_kgw    碳酸盐总碱度 (mol/kg water)
      k_kgw      总 K+ (mol/kg water);  缺省等于 alk_kgw (纯 KHCO3)
      nitrite    总亚硝酸盐 (mol/kg water), 0 表示不加盐
    """
    K = consts(T)
    A = A_DH(T-273.15)
    if k_kgw is None:
        k_kgw = alk_kgw
    phi = pr_phi(T, p_co2_atm) if fugacity else 1.0
    aCO2 = K['KH'] * phi * p_co2_atm          # 溶解 CO2* 的活度 (中性, gamma ~ 1)
    ka_no2 = 10**-pka_hno2

    def species(aH, g1, g2):
        H    = aH/g1
        OH   = K['Kw']/aH/g1
        HCO3 = K['K1']*aCO2/aH/g1
        CO3  = K['K2']*K['K1']*aCO2/(aH*aH)/g2
        no2  = nitrite/(1 + aH*g1/ka_no2) if nitrite else 0.0
        hn   = nitrite - no2
        I = 0.5*(k_kgw + H + OH + HCO3 + 4*CO3 + no2)
        return H, OH, HCO3, CO3, no2, hn, I

    I = max(alk_kgw, 1e-6)
    for _ in range(200):
        g1 = 10**lgamm(1, I, A) if activity else 1.0
        g2 = 10**lgamm(2, I, A) if activity else 1.0
        def cb(aH):
            H, OH, HCO3, CO3, no2, hn, I_ = species(aH, g1, g2)
            return (k_kgw + H) - (HCO3 + 2*CO3 + OH + no2)
        aH = _newton(cb, 1e-7)
        H, OH, HCO3, CO3, no2, hn, I_new = species(aH, g1, g2)
        if abs(I_new - I) < 1e-13:
            I = I_new; break
        I = 0.5*(I_new + I)
    return dict(pH=-math.log10(aH), phi=phi, CO2=aCO2, I=I,
                HCO3=HCO3, CO3=CO3, OH=OH, HNO2=hn, aH=aH)

def pH_closed(T, CT=0.2, activity=True):
    """封闭体系 (无 CO2 交换): 碳总量固定, 作参照"""
    K = consts(T)
    A = A_DH(T-273.15)
    g1 = 10**lgamm(1, CT, A) if activity else 1.0
    def f(aH):
        H  = aH/g1
        OH = K['Kw']/aH/g1
        b  = (CT - H - OH)/(1 + 2*K['K2']/aH)
        co2 = CT - b - K['K2']*b/aH
        return K['K1'] - aH*g1*b/co2
    return -math.log10(_newton(f, 4.5e-9))

if __name__ == "__main__":
    print("独立解析解自检 (0.2 mol/kg KHCO3, 25 C)")
    print("  封闭体系 (无 CO2) pH = %.2f   (文献 ~8.3)" % pH_closed(298.15))
    print()
    print("%10s %10s %10s %10s" % ("pCO2/atm", "pH", "I/mol/kg", "phi"))
    for p in (0.969, 1.956, 3.436, 5.904, 10.838, 15.773, 20.707):
        r = pH_open(298.15, p)
        print("%10.3f %10.4f %10.5f %10.4f" % (p, r["pH"], r["I"], r["phi"]))
