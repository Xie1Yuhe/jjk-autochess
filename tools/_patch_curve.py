# -*- coding: utf-8 -*-
"""把 rebalance 的目标曲线压平一点：早期别削太狠"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "tools", "rebalance_power.py")
s = io.open(p, encoding="utf-8").read()

old = "TARGET = {1: 780, 2: 900, 3: 1010, 4: 1120, 5: 1260}"
new = ("TARGET = {1: 830, 2: 915, 3: 995, 4: 1075, 5: 1160}\n"
       "# 曲线比第一版平：第一版 1 费削太狠，前 3 回合直接崩")
assert old in s, "target anchor"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("目标曲线已压平：830 / 915 / 995 / 1075 / 1160")
