# -*- coding: utf-8 -*-
import io, os
import os
B=os.path.dirname(os.path.abspath(__file__))
parts=["gen_report_head.py","gen_report_body.py","gen_report_body2.py","gen_report_body3.py"]
buf=[]
for p in parts:
    with io.open(os.path.join(B,p), encoding="utf-8") as f:
        buf.append(f.read())
src="\n".join(buf)
with io.open(os.path.join(B,"make_report.py"),"w",encoding="utf-8") as f:
    f.write(src)
print("merged, chars:", len(src))
