# -*- coding: utf-8 -*-
r"""
apply_domain_cost.py —— 领域角色上调、白板高费下调

## 背景

领域展开是目前最强的机制（持续状态 + 敌方压制 + 领域内技能追加全场），
但有几个领域角色只卖 1~2 费，明显德不配位。

用户提出的两条：
  1. 领域角色全部提到 4~5 费，让他们在后期出现
  2. 相应地把 4/5 费里「看起来白板」的角色调下来

## 本次调整

上调（→ 4 费）：
  [由死而生的灵感] 真人   2 → 4   领域展开「自闭圆顿裏」
  [咒灵的矜持]     漏瑚   2 → 4   領域展開「蓋棺鉄囲山」
  [战斗的愉悦]     花御   2 → 4   領域展開「朶頤光海」
  [无尽的式神]     陀艮   1 → 4   领域展开「荡蕴平线」

下调：
  [轻快的身体] 虎杖悠仁        4 → 1   技能/必杀都是纯伤害，无机制
  [为了保护非术师] 夏油杰      4 → 2   同上（用户点名）
  [术师杀手] 伏黑甚尔          4 → 2   同上
  [觉醒] 五条悟               4 → 2   同上
  [虚式「茈」] 五条悟          5 → 4   同上（用户点名）

费用分布 22/23/23/22/21 → 22/23/23/23/20（总数仍 111）

## 面板同步

每升一档 ×1.06、每降一档 ÷1.06（沿用 apply_cost_curve 的约定），
之后还会跑 rebalance_power.py 在档内再拉平一次。

用法：
    python tools\apply_domain_cost.py
"""
import json
import os
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
STEP = 0.06

UP = {
    "619763": (4, "[由死而生的灵感] 真人"),
    "607872": (4, "[咒灵的矜持] 漏瑚"),
    "607873": (4, "[战斗的愉悦] 花御"),
    "671525": (4, "[无尽的式神] 陀艮"),
}
DOWN = {
    "610359": (1, "[轻快的身体] 虎杖悠仁"),
    "607979": (2, "[为了保护非术师] 夏油杰"),
    "623845": (2, "[术师杀手] 伏黑甚尔"),
    "661932": (2, "[觉醒] 五条悟"),
    "612295": (4, "[虚式「茈」] 五条悟"),
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by = {u["id"]: u for u in units}
    print("[cost] 调整前分布:", dict(sorted(Counter(u["cost"] for u in units).items())))

    def move(uid, new_cost, label, tag):
        u = by.get(uid)
        if not u:
            print("   找不到", uid, label)
            return
        old = u["cost"]
        if old == new_cost:
            print("   %-26s %d 费不变（%s）" % (label, old, tag))
            return
        k = 1 + (new_cost - old) * STEP
        u["hp"] = int(round(u["hp"] * k))
        u["ad"] = int(round(u["ad"] * k))
        u["spell"] = int(round(u["spell"] * k))
        u["cost"] = new_cost
        u["costSource"] = tag
        print("   %-26s %d → %d 费（%s）" % (label, old, new_cost, tag))

    print("[cost] 领域角色上调：")
    for uid, (c, label) in UP.items():
        move(uid, c, label, "domain-up")
    print("[cost] 白板高费下调：")
    for uid, (c, label) in DOWN.items():
        move(uid, c, label, "blank-down")

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = Counter(u["cost"] for u in units)
    print("[cost] 调整后分布:", dict(sorted(n.items())), "总数", sum(n.values()))


if __name__ == "__main__":
    main()
