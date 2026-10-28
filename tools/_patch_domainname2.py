# -*- coding: utf-8 -*-
"""第二处 domain 事件（单位开域）补 name"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(p, encoding="utf-8").read()

old = "this._emit({ t: 'domain', pos: { x: u.pos.x, y: u.pos.y }"
i = s.find(old)
assert i >= 0, "找不到第二处"
# 找到这段 _emit 的结尾
j = s.find("});", i)
seg = s[i:j + 3]
print("原段:", seg[:160])
new = seg.replace("pos: { x: u.pos.x, y: u.pos.y }",
                  "pos: { x: u.pos.x, y: u.pos.y }, team: u.team, "
                  "name: (u.def && u.def.ult && u.def.ult.name) || '領域展開'", 1)
s = s[:i] + new + s[j + 3:]
io.open(p, "w", encoding="utf-8").write(s)
print("已补:", new[:180])
