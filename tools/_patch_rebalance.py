# -*- coding: utf-8 -*-
"""临时补丁：给 rebalance_power.py 加「温和拉平 + 面板上限」"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "tools", "rebalance_power.py")
s = io.open(p, encoding="utf-8").read()

s = s.replace(
    "LIMIT = 1.28          # 档内允许的极差（目标）",
    "TARGET_SPREAD = 1.18  # 档内目标极差：太小会失去个性，太大变成「唯一答案」",
)
s = s.replace(
    "CLAMP = (0.72, 1.45)  # 单次迭代的缩放上下限",
    "CLAMP = (0.80, 1.25)  # 单次迭代的缩放上下限\n"
    "STAT_MAX = (0.62, 1.70)   # 每张卡相对原始面板的变化上限，保住 wiki 辨识度",
)
s = s.replace("ITERS = 4", "ITERS = 6")

old = """    before = {}
    for it in range(ITERS):
        rows = index_all(units)"""
new = """    before = {}
    origin = {u["id"]: (u["hp"], u["ad"], u["spell"]) for u in units}
    for it in range(ITERS):
        rows = index_all(units)
        # 档内极差已经达标就停手，避免过度拉平
        spread_ok = True
        for c in (1, 2, 3, 4, 5):
            v = sorted(r["idx"] for r in rows if r["u"]["cost"] == c)
            if v and v[-1] / max(1, v[0]) > TARGET_SPREAD:
                spread_ok = False
                break
        if spread_ok and it > 0:
            print("   第 %d 轮收敛：档内极差已达标，停止" % it)
            break"""
assert old in s, "anchor1"
s = s.replace(old, new, 1)

old2 = """            u["hp"] = max(200, int(round(u["hp"] * k)))
            u["ad"] = max(8, int(round(u["ad"] * k)))
            u["spell"] = max(8, int(round(u["spell"] * k)))"""
new2 = """            oh, oa, osp = origin[u["id"]]
            u["hp"] = max(350, int(round(max(oh * STAT_MAX[0], min(oh * STAT_MAX[1], u["hp"] * k)))))
            u["ad"] = max(16, int(round(max(oa * STAT_MAX[0], min(oa * STAT_MAX[1], u["ad"] * k)))))
            u["spell"] = max(16, int(round(max(osp * STAT_MAX[0], min(osp * STAT_MAX[1],
                                                                    u["spell"] * k)))))"""
assert old2 in s, "anchor2"
s = s.replace(old2, new2, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("rebalance_power.py 已打补丁")
