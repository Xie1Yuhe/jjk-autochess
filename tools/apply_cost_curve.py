# -*- coding: utf-8 -*-
r"""
apply_cost_curve.py —— 按「强度档位 + 人气」重排费用，并同步调整面板

背景（用户要求）：
  1. 费用应当反映强度 —— 官方强度榜（PVE）能大致反映我们自走棋的强度，
     但两者毕竟不同（回合制 vs 实时、辅助位价值差异），所以以榜单为主、人气与定位为辅。
  2. 原来 1 费有 30 种，卡池被稀释得厉害：凑一张 1 费 3 星要 ~115 金（TFT 约 50 金）。
     重排后每档 21–23 种，接近 TFT 的 14/13/14/14/10 那种均衡。

做法：
  · score = 档位权重 + 人气加成
  · 按 score 降序，按配额切档：5 费 21 / 4 费 22 / 3 费 23 / 2 费 23 / 1 费 22
  · 面板随费用同步缩放：每升一档 ×1.06（保证 5 费真的比 1 费厚）

用法（排在 apply_batch7.py 之后）：
    python tools\apply_cost_curve.py
    python tools\build_data.py
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
REPORT = os.path.join(ROOT, "tools", "cost_report.json")

# 档位权重（官方强度榜）
TIER_W = {"SSS": 100, "SS": 86, "S": 72, "A": 56, "B": 38, "C": 22}

# 人气 / 定位加成：主角团与超人气角色往上抬，纯辅助与小配角往下压
POPULAR = {
    "五条悟": 14, "两面宿傩": 14, "虎杖悠仁": 12, "夏油杰": 12, "乙骨忧太": 11,
    "伏黑惠": 10, "钉崎野蔷薇": 8, "七海建人": 9, "真人": 10, "漏瑚": 8,
    "花御": 7, "胀相": 7, "伏黑甚尔": 9, "禅院直毘人": 8, "禅院真希": 6,
    "东堂葵": 5, "狗卷棘": 5, "熊猫": 3, "三轮霞": 4, "冥冥": 5,
    "家入硝子": 4, "夜蛾正道": 4, "加茂宪伦": 4, "里梅": 3, "米格尔": 3,
    "陀艮": 3, "猪野琢真": 2, "日下部笃也": 2, "乐岩寺嘉伸": 2,
}
# 纯辅助/工具人定位再压一档（他们强度榜可能高，但自走棋里不该贵）
SUPPORT_DOWN = {"家入硝子", "伊地知洁高", "结木海斗", "西宫桃", "三輪霞", "三轮霞", "龙胆咲"}

# 每档配额（合计 111）
QUOTA = {5: 21, 4: 22, 3: 23, 2: 23, 1: 22}

# 面板随费用缩放：每升一档 ×1.06
STAT_STEP = 0.06


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    before = {u["id"]: u["cost"] for u in units}

    for u in units:
        base = u["baseCharacter"]
        s = TIER_W.get(u.get("tier"), 50)
        s += POPULAR.get(base, 0)
        if base in SUPPORT_DOWN:
            s -= 12
        # 同角色多张卡时，让「高费形态」略微占优（避免同角色全挤在一个费用档）
        s += (u.get("cost") or 3) * 0.8
        u["_score"] = s

    units.sort(key=lambda x: (-x["_score"], x["name"]))
    idx = 0
    new_cost = {}
    for c in (5, 4, 3, 2, 1):
        n = QUOTA[c]
        for u in units[idx:idx + n]:
            new_cost[u["id"]] = c
        idx += n

    moved = 0
    for u in units:
        old = u["cost"]
        new = new_cost[u["id"]]
        if new != old:
            moved += 1
            mult = 1 + (new - old) * STAT_STEP
            u["hp"] = int(round(u["hp"] * mult))
            u["ad"] = int(round(u["ad"] * mult))
            u["spell"] = int(round(u["spell"] * mult))
        u["cost"] = new
        u["costSource"] = "tier+popularity"
        u.pop("_score", None)

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    dist = dict(sorted(Counter(u["cost"] for u in units).items()))
    rep = {
        "dist": dist,
        "moved": moved,
        "quota": QUOTA,
        "detail": [{"name": u["name"], "tier": u.get("tier"), "from": before[u["id"]],
                    "to": u["cost"]} for u in units if before[u["id"]] != u["cost"]],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[cost] 新费用分布 %s（合计 %d）" % (dist, sum(dist.values())))
    print("[cost] 变动 %d 张" % moved)
    ups = [d for d in rep["detail"] if d["to"] > d["from"]]
    downs = [d for d in rep["detail"] if d["to"] < d["from"]]
    print("[cost] 涨价 %d 张，降价 %d 张" % (len(ups), len(downs)))
    for name_label, group in (("涨价", ups), ("降价", downs)):
        print("  %s示例: %s" % (name_label, "、".join(
            "%s(%d→%d)" % (d["name"], d["from"], d["to"]) for d in group[:6])))


if __name__ == "__main__":
    main()
