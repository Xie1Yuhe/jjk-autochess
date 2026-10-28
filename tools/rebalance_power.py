# -*- coding: utf-8 -*-
r"""
rebalance_power.py —— 按「卡组固定配额」的前提重排战斗力

## 为什么必须调

卡组规则是 **8/8/8/8/4（精确配额）**，意味着：
  · 每个费用槽位对每套卡组都是**固定数量**
  · 玩家在同一个费用档里挑卡 → 如果档内强度差 2.3 倍，就是「有唯一正确答案」
  · 卡组选择的乐趣应该来自**机制配合**，而不是「挑数值最高的那 8 张」

所以目标从「费用越高越强」改成：

  1. **档内拉平**：同费用档综合值极差压到 ~1.25× 以内
  2. **档间有序**：1→5 费均值依次抬升（780 → 900 → 1010 → 1120 → 1260）
  3. **档位仍有用**：官方档位高一点的卡，在档内允许 +2~4% 的微小优势

## 怎么调

**只动面板（hp / ad / spell），不动技能倍率与附加效果** —— 后者严格忠实 wiki 原文。
每次迭代按 ratio^0.75 缩放（面板→综合值是次线性的），迭代 4 轮逼近目标。

用法：
    python tools\rebalance_power.py            # 预览
    python tools\rebalance_power.py --apply    # 写回 units.json
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")

# 每档的目标综合值（以「全池平均=1000」为标尺）
TARGET = {1: 830, 2: 915, 3: 995, 4: 1075, 5: 1160}
# 曲线比第一版平：第一版 1 费削太狠，前 3 回合直接崩
# 官方档位在档内的微小加成（SSS 最贵的那种本身就是 5 费，这里只做轻微区分）
TIER_BONUS = {"SSS": 0.05, "SS": 0.03, "S": 0.015, "A": 0.0, "B": -0.01, "C": -0.02}
TARGET_SPREAD = 1.18  # 档内目标极差：太小会失去个性，太大变成「唯一答案」
CLAMP = (0.80, 1.25)  # 单次迭代的缩放上下限
STAT_MAX = (0.62, 1.70)   # 每张卡相对原始面板的变化上限，保住 wiki 辨识度
ITERS = 6

sys.path.insert(0, os.path.join(ROOT, "tools"))
import power_audit as PA   # 复用同一套指标，保证前后口径一致


def index_all(units):
    rows = []
    for u in units:
        mods = u.get("mods") or {}
        e = PA.ehp(u, mods)
        d = PA.dps(u, mods)
        sv = PA.skill_value(u, u.get("skill") or {})
        uv = PA.ult_value(u, u.get("ult") or {}, mods)
        ut = PA.utility(mods)
        core = (e ** 0.42) * (d ** 0.38) * ((sv + uv + 1) ** 0.20)
        rows.append({"u": u, "score": core + ut})
    avg = sum(r["score"] for r in rows) / len(rows)
    for r in rows:
        r["idx"] = r["score"] / avg * 1000
    return rows


def main():
    apply = "--apply" in sys.argv
    units = json.load(open(UNITS, encoding="utf-8"))

    before = {}
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
            break
        # 先算每档均值，再把档内偏离往目标拉
        for r in rows:
            u = r["u"]
            c = u["cost"]
            tgt = TARGET[c] * (1 + TIER_BONUS.get(u.get("tier"), 0))
            ratio = tgt / max(1, r["idx"])
            ratio = max(CLAMP[0], min(CLAMP[1], ratio))
            k = ratio ** 0.75
            oh, oa, osp = origin[u["id"]]
            u["hp"] = max(350, int(round(max(oh * STAT_MAX[0], min(oh * STAT_MAX[1], u["hp"] * k)))))
            u["ad"] = max(16, int(round(max(oa * STAT_MAX[0], min(oa * STAT_MAX[1], u["ad"] * k)))))
            u["spell"] = max(16, int(round(max(osp * STAT_MAX[0], min(osp * STAT_MAX[1],
                                                                    u["spell"] * k)))))
            if it == 0:
                before[u["id"]] = r["idx"]

    rows = index_all(units)
    # 报告
    by_cost = {}
    for r in rows:
        by_cost.setdefault(r["u"]["cost"], []).append(r["idx"])
    print("[rebalance] 结果（目标 %s）" % TARGET)
    for c in sorted(by_cost):
        v = sorted(by_cost[c])
        print("   %d费: 均值 %.0f 范围 %.0f~%.0f 极差 %.2f×" % (
            c, sum(v) / len(v), v[0], v[-1], v[-1] / max(1, v[0])))

    # 档内离散度
    worst = []
    for r in rows:
        c = r["u"]["cost"]
        v = sorted(by_cost[c])
        med = v[len(v) // 2]
        worst.append((abs(r["idx"] - med) / max(1, med), r["u"]["name"], c, r["idx"], med))
    worst.sort(reverse=True)
    print("[rebalance] 偏离档内中位数最大的 8 张：")
    for dev, name, c, idx, med in worst[:8]:
        print("   %-24s %d费  %.0f vs 中位 %.0f  (%.0f%%)" % (name, c, idx, med, dev * 100))

    if apply:
        json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[rebalance] 已写回 units.json")
    else:
        print("[rebalance] 预览模式，未写入（加 --apply 应用）")


if __name__ == "__main__":
    main()
