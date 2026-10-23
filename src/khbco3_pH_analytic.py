# -*- coding: utf-8 -*-
"""
0.2 mol/kg KHCO3 水溶液与不同压力 CO2 平衡时的 pH
====================================================
独立解析求解（不依赖 PHREEQC），含：
  * 碳酸体系全部平衡 + 电荷平衡 + 质量守恒
  * Davies 活度系数（I ~ 0.2 mol/kg）
  * Peng-Robinson 方程计算 CO2 逸度系数（>1 MPa 时显著偏离理想气体）
  * 温度对 pKa1 / pKa2 / Kw / Henry 常数的影响（van't Hoff）
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
    return dict(
        K1 = 10**-pK1_0 * math.exp( dH1/R*(1/T - 1/T0)),
        K2 = 10**-pK2_0 * math.exp( dH2/R*(1/T - 1/T0)),
        Kw = 10**-pKw_0 * math.exp(dHKw/R*(1/T - 1/T0)),
        KH = KH_0      * math.exp( dHK/R*(1/T - 1/T0)))

def lgamm(z, I, A):
    return -A*z*z*(math.sqrt(I)/(1+math.sqrt(I)) - 0.3*I)

def pr_phi(T, Pbar):
    """Peng-Robinson 纯组分 CO2 逸度系数"""
    Tc, Pc, w = 304.1282, 73.773, 0.22394
    Tr, Pr = T/Tc, Pbar/Pc
    kappa = 0.37464 + 1.54226*w - 0.26992*w*w
    alpha = (1 + kappa*(1 - math.sqrt(Tr)))**2
    Aa = alpha*0.45724*Pr/Tr/Tr
    Bb = 0.07780*Pr/Tr
    c2, c1, c0 = -(1-Bb), Aa-3*Bb*Bb-2*Bb, -(Aa*Bb-Bb*Bb-Bb**3)
    z = 1.0
    for _ in range(300):
        f  = z*z*z + c2*z*z + c1*z + c0
        df = 3*z*z + 2*c2*z + c1
        z -= f/df
    s2 = math.sqrt(2)
    lnf = (z-1) - math.log(z-Bb) - Aa/(2*s2*Bb)*math.log((z+(1+s2)*Bb)/(z+(1-s2)*Bb))
    return math.exp(lnf)

def newton(f, x0):
    x = x0
    for _ in range(300):
        d = max(abs(x), 1e-14)*1e-8
        f0, f1 = f(x), f(x+d)
        x -= f0*d/(f1-f0)
    return x

def pH_open(T, P_MPa, activity=True, fugacity=True, alk=0.2):
    """开口体系：碱度固定为 alk, 与 pCO2 达到平衡"""
    K = consts(T)
    Pbar = P_MPa*10.0
    phi  = pr_phi(T, Pbar) if fugacity else 1.0
    aCO2 = K['KH'] * phi * Pbar/1.01325          # 溶解 CO2* 的活度(中性, gamma~1)
    A    = A_DH(T-273.15)
    g1 = 10**lgamm(1, alk, A) if activity else 1.0
    g2 = 10**lgamm(2, alk, A) if activity else 1.0
    def cb(x):                                     # x = a_H+
        HCO3 = K['K1']*aCO2/x/g1
        CO3  = K['K2']*K['K1']*aCO2/(x*x)/g2
        OH   = K['Kw']/x/g1
        return x/g1 + alk - HCO3 - 2*CO3 - OH
    aH  = newton(cb, 1e-7)
    return dict(pH=-math.log10(aH), phi=phi, CO2=aCO2,
                HCO3=K['K1']*aCO2/aH/g1, CO3=K['K2']*K['K1']*aCO2/(aH*aH)/g2)

def pH_closed(T, CT=0.2, activity=True):
    """封闭体系：碳总量固定 CT, 无气体"""
    K = consts(T)
    A = A_DH(T-273.15)
    g1 = 10**lgamm(1, CT, A) if activity else 1.0
    def f(aH):
        H  = aH/g1
        OH = K['Kw']/aH/g1
        b  = (CT - H - OH)/(1 + 2*K['K2']/aH)
        co2 = CT - b - K['K2']*b/aH
        return K['K1'] - aH*g1*b/co2
    return -math.log10(newton(f, 4.5e-9))

PRESS = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0]

if __name__ == "__main__":
    print("0.2 mol/kg KHCO3 与 CO2 气相平衡的 pH")
    print("参考点校核: 25 C 密封瓶(无 CO2) pH = %.2f  (文献 ~8.3)" % pH_closed(298.15))
    print("            25 C 纯水与 1 atm CO2 平衡 pH ~ 3.9")
    for Tc in (15.0, 25.0, 40.0):
        T = Tc + 273.15
        print("\n--- T = %.0f C ---" % Tc)
        print("%9s %9s %9s %9s %9s %8s" % ("P/MPa","pH(理想)","pH(Davies)","pH(+PR)","phi","CO2*/M"))
        for P in PRESS:
            a = pH_open(T, P, False, False)
            b = pH_open(T, P, True,  False)
            c = pH_open(T, P, True,  True)
            print("%9.2f %9.2f %9.2f %9.2f %9.3f %8.4f" % (P, a['pH'], b['pH'], c['pH'], c['phi'], c['CO2']))
