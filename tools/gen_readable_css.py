# -*- coding: utf-8 -*-
r"""
gen_readable_css.py —— 自动生成「放大字号」覆盖层

思路：扫描现有 CSS 里所有 font-size 规则，把 ≤11px 的 +2px、12~13px 的 +1px，
生成 css/readable.css（最后加载，带 !important）。

只动字号，不动 padding / 高度 / line-height，尽量不改变排版骨架。
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_DIR = os.path.join(ROOT, "css")

# 这些是纯装饰（棋子角标、小圆点数字），放大会挤压图形，跳过
SKIP_PAT = re.compile(r"::?(before|after)|\.tk-q|\.ic-count|\.gc-star|\.sc-tier|\.ir-cost|\.bench-slot::after")

rules = []          # (selector, size)
seen = set()

for f in sorted(os.listdir(CSS_DIR)):
    if not f.endswith(".css") or f == "readable.css":
        continue
    s = io.open(os.path.join(CSS_DIR, f), encoding="utf-8").read()
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", s):
        sel = " ".join(m.group(1).split())
        body = m.group(2)
        fm = re.search(r"font-size\s*:\s*([\d.]+)px", body)
        if not fm:
            continue
        size = float(fm.group(1))
        if size > 13:
            continue
        if SKIP_PAT.search(sel):
            continue
        # 只取简单选择器（避免复杂组合被我们覆盖后错位）
        key = (sel, size)
        if key in seen:
            continue
        seen.add(key)
        rules.append((sel, size))

out = ["/* 自动生成：把小字号整体放大 1~2px（只改 font-size，不动排版骨架） */\n"]
n2 = n1 = 0
for sel, size in rules:
    if size <= 11:
        new = size + 2
        n2 += 1
    else:
        new = size + 1
        n1 += 1
    out.append("%s { font-size: %gpx !important; }" % (sel, new))

# 额外：几处最常读的文本再给一点
out.append("""
/* 关键可读性补充 */
.shop-card .sc-name { font-size: 14px !important; letter-spacing: .02em !important; }
.hud-chip .hc-value { font-size: 15px !important; }
.hud-chip .hc-label { font-size: 10.5px !important; }
.btn, .btn-start { font-size: 13.5px !important; }
.traits-panel .tr-name, .traits-panel .tr-label { font-size: 12.5px !important; }
.log-line { font-size: 12.5px !important; line-height: 1.5 !important; }
""".replace("\n", "\n"))

io.open(os.path.join(CSS_DIR, "readable.css"), "w", encoding="utf-8").write("\n".join(out))
print("[readable] 生成 %d 条规则（+2px %d 条，+1px %d 条）" % (len(rules), n2, n1))

# 在 index.html 里最后引入
p = os.path.join(ROOT, "index.html")
h = io.open(p, encoding="utf-8").read()
if "css/readable.css" not in h:
    i = h.rindex('<link rel="stylesheet"')
    j = h.index(">", i) + 1
    h = h[:j] + '\n  <link rel="stylesheet" href="css/readable.css">' + h[j:]
    io.open(p, "w", encoding="utf-8").write(h)
    print("[readable] index.html 已引入（最后加载）")
