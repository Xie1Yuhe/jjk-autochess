# -*- coding: utf-8 -*-
r"""
wiki_power_span.py —— 量出 wiki 伤害倍率的真实跨度，定一个统一的换算系数

目的：现在的做法是
    小技能 power = clamp(pct/120, 1.0, 3.3)
    必杀   upow  = clamp(pct/150, 1.4, 4.0)
两处 clamp 把 wiki 的大跨度压扁了，导致「A 的大招比 B 强多少倍」这层关系丢失。

本脚本统计所有卡的真实 pct 分布，算出「线性映射」所需的统一系数 K，
使得 power 的中位数落在 1.6 左右，并给出映射后的极值。
"""
import json
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")

PAT_A = [
    r"造成[^。%]{0,24}?([0-9]+(?:\.[0-9]+)?)%[^。%]{0,6}(?:的)?(?:体术|术式|复合|伤害)",
    r"(?:近战|远程|近身)攻击的[^。%]{0,12}?([0-9]+(?:\.[0-9]+)?)%",
    r"([0-9]+(?:\.[0-9]+)?)%\s*[的]?(?:体术|术式|复合)伤害",
]
PAT_B = [r"造成[^。%]{0,20}?([0-9]+(?:\.[0-9]+)?)%[^。]{0,10}伤害"]
PAT_C = [r"([0-9]+(?:\.[0-9]+)?)%[^。]{0,8}伤害"]


def extract(desc):
    if not desc:
        return None
    for group in (PAT_A, PAT_B, PAT_C):
        for p in group:
            m = re.search(p, desc)
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    pass
    return None


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    sk, ul = [], []
    for u in units:
        a = extract((u.get("skill") or {}).get("wikiDesc") or "")
        b = extract((u.get("ultimate") or {}).get("wikiDesc") or "")
        if a and a >= 60:      # 低于 60% 基本是“概率/回合”之类的噪声
            sk.append((a, u["name"]))
        if b and b >= 100:
            ul.append((b, u["name"]))

    def report(label, arr):
        vals = sorted(x[0] for x in arr)
        if not vals:
            return
        med = statistics.median(vals)
        print("%s：n=%d  最小 %.0f%%  中位 %.0f%%  最大 %.0f%%  跨度 %.1f×" % (
            label, len(vals), vals[0], med, vals[-1], vals[-1] / max(1, vals[0])))
        print("   最高 5 张：" + "、".join(
            "%s %.0f%%" % (n, v) for v, n in sorted(arr, reverse=True)[:5]))
        # 线性映射：中位数 → 1.6
        K = med / 1.6
        print("   统一线性系数 K = %.0f（中位映射到 power 1.6）" % K)
        print("   → 映射后范围 %.2f ~ %.2f（跨度仍为 %.1f×，关系完整保留）" % (
            vals[0] / K, vals[-1] / K, vals[-1] / max(1, vals[0])))
        print("   对比现状：小技能最高 3.3×、必杀最高 4.0× —— 被压扁")
        return K

    print("=== wiki 伤害倍率真实分布 ===")
    ks = report("小技能", sk)
    print()
    ku = report("必杀", ul)
    print()
    print("=== 结论 ===")
    print("要「忠实映射」，应去掉 clamp，用单一 K 线性换算：")
    if ks:
        print("   小技能 power = pct / %.0f" % ks)
    if ku:
        print("   必杀   upow  = pct / %.0f" % ku)
    print("代价：必杀最高会到 5~7 倍，需要同步上调 HP 曲线，否则一局 2 秒结束。")


if __name__ == "__main__":
    main()
