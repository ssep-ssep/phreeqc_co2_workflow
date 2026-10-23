# -*- coding: utf-8 -*-
"""校验新报告: 表号连续 + 无未转义%% + 关键数值"""
import sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from config import REPORT as P
d=Document(P)
def it(p,doc):
    for c in p.iterchildren():
        if c.tag.endswith("}p"): yield Paragraph(c,doc)
        elif c.tag.endswith("}tbl"): yield Table(c,doc)
caps=[]; ntab=0; bad=[]
ti=0
for b in it(d.element.body,d):
    if isinstance(b,Table): ntab+=1
    else:
        t=b.text.strip()
        m=re.match(r"^表\s*(\d+)\s{2,}", t)
        if m:
            ti+=1
            caps.append((int(m.group(1)), t[:44]))
            if int(m.group(1))!=ti: bad.append("表号不连续: %s (第%d个caption)"%(t[:16],ti))
        if "%%" in t: bad.append("未转义%%: "+t[:40])
print("表格对象 %d, 表caption %d" % (ntab, ti))
print("问题:", bad if bad else "无")
print()
for n,t in caps: print("  表%-3d %s" % (n,t))
