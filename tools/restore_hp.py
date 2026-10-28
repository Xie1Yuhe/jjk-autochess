# -*- coding: utf-8 -*-
r"""
restore_hp.py —— 把 HP 中位数恢复到「按档位重排前」的水平

## 为什么

rebalance_power.py 为了拉平综合值，把不少卡的 HP 削到了原值的 50~60%。
综合指数里 EHP 只占 0.42 次方，所以指数看着「平了」，
但实战里血量掉一半 = 出手次数少一半 = 实际强度远低于指数。

结果：平衡从 90/60/28 掉到 55/14/4。

## 做法

保持已经拉平好的 ad / spell（输出），
只把每个费用档的 HP 中位数拉回重排前的观测值：

    1费 690 / 2费 790 / 3费 834 / 4费 841 / 5费 937

同档内按「当前 HP 相对本档中位数的比例」整体缩放，
所以档内的血量差异（辨识度）保留，只是整体回到健康水平。

用法：
    python tools\restore_hp.py            # 预览
    python tools\restore_hp.py --apply
"""
import json
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")

TARGET_MEDIAN = {1: 690, 2: 790, 3: 834, 4: 841, 5: 937}
FLOOR, CEIL = 340, 1320


def main():
    apply = "--apply" in sys.argv
    units = json.load(open(UNITS, encoding="utf-8"))

    by_cost = {}
    for u in units:
        by_cost.setdefault(u["cost"], []).append(u)

    print("[hp] 各档 HP 中位数：修复前 → 修复后")
    for c in sorted(by_cost):
        g = by_cost[c]
        cur = statistics.median([u["hp"] for u in g])
        tgt = TARGET_MEDIAN.get(c, cur)
        k = tgt / max(1, cur)
        print("   %d费  中位 %d → %d   (×%.2f，%d 张)" % (c, cur, tgt, k, len(g)))
        for u in g:
            u["hp"] = max(FLOOR, min(CEIL, int(round(u["hp"] * k))))

    if apply:
        json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[hp] 已写回 units.json")
    else:
        print("[hp] 预览模式（加 --apply 应用）")


if __name__ == "__main__":
    main()
