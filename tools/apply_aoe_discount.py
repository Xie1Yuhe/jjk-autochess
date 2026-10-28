# -*- coding: utf-8 -*-
r"""
apply_aoe_discount.py —— 群体技能折价

## 问题

倍率映射只看 wiki 的百分比，**没区分单体与群体**。
实测结果：

| 类别 | 单体均值 | 群体均值 | 比值 |
|---|---|---|---|
| 技能 | 1.34 | 1.28 | 0.96 |
| 必杀 | 2.37 | 2.95 | **1.24** |

群体必杀不但没折价，反而比单体强 —— 明显不对。
用户点名的典型案例：[群鸦翩舞之夜] 冥冥（2 费）技能 2.19 全体，
比不少 5 费群体必杀条还高。

## 做法

按「群体 ≈ 单体 × 0.65」定标（自走棋里群体通常打到 3~5 个目标，
0.65 是常见折价），反推每类的缩放系数：

  skill: 群体目标 = 1.34 × 0.65 = 0.871  →  系数 = 0.871 / 1.28 = 0.68
  ult:   群体目标 = 2.37 × 0.65 = 1.540  →  系数 = 1.540 / 2.95 = 0.52

只缩放「群体」类（`type === 'slam'` 或 `radius >= 99`），单体不动。

用法：
    python tools\apply_aoe_discount.py            # 预览
    python tools\apply_aoe_discount.py --apply
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
TARGET_RATIO = 0.65
MIN_POWER = 0.3


def is_aoe(sk):
    if not sk:
        return False
    if sk.get("type") == "slam":
        return True
    if (sk.get("radius") or 0) >= 99:
        return True
    return bool(sk.get("aoe"))


def collect(units, key):
    single, aoe = [], []
    for u in units:
        sk = u.get(key) or {}
        p = sk.get("power")
        if not p:
            continue
        (aoe if is_aoe(sk) else single).append(p)
    return single, aoe


def main():
    apply = "--apply" in sys.argv
    units = json.load(open(UNITS, encoding="utf-8"))
    factors = {}
    for label, key in (("技能", "skill"), ("必杀", "ult")):
        single, aoe = collect(units, key)
        if not single or not aoe:
            continue
        ms, ma = statistics.mean(single), statistics.mean(aoe)
        target = ms * TARGET_RATIO
        f = target / ma
        factors[key] = f
        print("[aoe] %s：单体均值 %.2f / 群体均值 %.2f → 目标群体 %.2f，系数 ×%.2f" % (
            label, ms, ma, target, f))

    changed = 0
    worst = []
    for u in units:
        for key in ("skill", "ult"):
            sk = u.get(key) or {}
            if not is_aoe(sk) or not sk.get("power"):
                continue
            old = sk["power"]
            new = max(MIN_POWER, round(old * factors[key], 2))
            sk["power"] = new
            changed += 1
            worst.append((old - new, u["name"], key, old, new))
    worst.sort(reverse=True)

    print("[aoe] 共调整 %d 处" % changed)
    print("[aoe] 削得最多的 8 张：")
    for d, name, key, old, new in worst[:8]:
        print("   %-26s %s  %.2f → %.2f" % (name, "技能" if key == "skill" else "必杀", old, new))

    # 复核
    for label, key in (("技能", "skill"), ("必杀", "ult")):
        single, aoe = collect(units, key)
        if single and aoe:
            print("[aoe] 复核 %s：单体均值 %.2f / 群体均值 %.2f（比值 %.2f，目标 %.2f）" % (
                label, statistics.mean(single), statistics.mean(aoe),
                statistics.mean(aoe) / statistics.mean(single), TARGET_RATIO))

    if apply:
        json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[aoe] 已写回 units.json")
    else:
        print("[aoe] 预览模式（加 --apply 应用）")


if __name__ == "__main__":
    main()
