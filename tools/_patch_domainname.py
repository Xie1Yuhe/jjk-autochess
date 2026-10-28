# -*- coding: utf-8 -*-
"""给领域事件带上名字，方便 UI 朗读"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(p, encoding="utf-8").read()

n = 0
# 1) 特级羁绊自动开域
old1 = "this._emit({ t: 'domain', team: t });"
if old1 in s:
    s = s.replace(old1, "this._emit({ t: 'domain', team: t, name: '領域展開' });", 1)
    n += 1

# 2) 单位放大招开域（找 domain 相关的 emit）
for m in re.finditer(r"this\._emit\(\{\s*t:\s*'domain'[^}]*\}\)", s):
    seg = m.group(0)
    if "name" not in seg:
        s = s.replace(seg, seg.replace("}", ", name: (u && u.def && u.def.ult && u.def.ult.name) || '領域展開' }"), 1)
        n += 1

io.open(p, "w", encoding="utf-8").write(s)
print("domain 事件已加 name：%d 处" % n)

# 检查还有没有不带 name 的
s2 = io.open(p, encoding="utf-8").read()
left = [m.group(0) for m in re.finditer(r"t:\s*'domain'[^}]*\}", s2)]
for x in left:
    print("   剩余:", x[:110])
