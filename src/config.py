# -*- coding: utf-8 -*-
"""工作流路径配置 (相对于包根目录)"""
import os
PKG  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(PKG, "src")
IN   = os.path.join(PKG, "input")
OUT  = os.path.join(PKG, "output")
BIN  = os.path.join(PKG, "phreeqc")
REPORT_DIR = os.path.join(PKG, "report")
REPORT = os.path.join(REPORT_DIR, "0.2M_KHCO3_CO2平衡pH计算报告.docx")
