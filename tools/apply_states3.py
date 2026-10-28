# -*- coding: utf-8 -*-
r"""
apply_states3.py —— A 类：机制特殊、值得单独做的角色

三种新原语（已在 battle.js 里实现）：
  · skill.altSkill      双技能交替（宿傩「解 / 捌」）
  · skill.stackOnCast   叠层引爆（里梅「冻结」攒满 3 层炸开）
  · ult.scaleByCounter  必杀倍率随计数放大（钉崎「钉子指示物」）

用法：
    python tools\apply_states3.py && python tools\gen_text.py && python tools\build_data.py
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

# ---- 双技能交替
ALT = {
    # 宿傩：解（斩击）↔ 捌（解咒），原文两套技能轮流用
    "644233": {
        "altSkill": {"name": "「解」", "type": "barrage", "hits": 4, "sameTarget": True,
                     "power": 1.15, "panel": "magic", "applyTaken": 0.2},
        "why": "原文：宿傩用「解」与「捌」两套斩击轮换，不是单套技能",
    },
    # 胀相：血刃 ↔ 穿血
    "672458": {
        "altSkill": {"name": "「穿血」", "type": "strike", "power": 3.6,
                     "panel": "hybrid", "hybrid": True, "applyTaken": 0.25},
        "why": "原文：「血刃」与「穿血」交替使用",
    },
}

# ---- 叠层引爆
STACK = {
    # 里梅[退下废物]「冻结强化」：原文「自身冻结强化Lv上升(最大20)、必杀对 3 个以上冻结额外 400%」
    "691924": {
        "stackOnCast": {"key": "freezeLv", "max": 3, "burst": 1.7, "taken": 0.30},
        "why": "原文：冻结强化 Lv 叠层、3 层以上引爆并解除 3 个冻结",
    },
    # 钉崎[相性极差]「钉子计数」：攒钉子，满层引爆
    "615301": {
        "stackOnCast": {"key": "nail2", "max": 4, "burst": 1.5, "taken": 0.3},
        "why": "原文：钉子指示物越多效果越大，最多 11 个",
    },
}

# ---- 必杀随计数放大
SCALE = {
    # 里梅[退下废物]：必杀随冻结强化层数放大
    "691924": {"scaleByCounter": {"key": "freezeLv", "per": 0.10, "max": 10},
               "why": "原文：冻结强化 Lv 越高必杀越痛（最大 20 层）"},
    "607990": {"scaleByCounter": {"key": "nail", "per": 0.18, "max": 8},
               "why": "原文：钉子计数越多「簪」的伤害越高"},
    "605996": {"scaleByCounter": {"key": "nail2", "per": 0.15, "max": 8},
               "why": "原文：钉子指示物越多倍率越高"},
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by = {u["id"]: u for u in units}
    n = 0
    for uid, spec in ALT.items():
        u = by.get(uid)
        if not u:
            print("[A] 找不到", uid); continue
        sk = dict(u.get("skill") or {})
        sk["altSkill"] = spec["altSkill"]
        sk["stateWhy"] = spec["why"]
        u["skill"] = sk
        n += 1
        print("   %-22s 双技能交替：%s ↔ %s" % (u["name"], sk.get("name"), spec["altSkill"]["name"]))
    for uid, spec in STACK.items():
        u = by.get(uid)
        if not u:
            print("[A] 找不到", uid); continue
        sk = dict(u.get("skill") or {})
        sk["stackOnCast"] = spec["stackOnCast"]
        sk["stateWhy"] = spec["why"]
        u["skill"] = sk
        n += 1
        print("   %-22s 叠层引爆：%d 层" % (u["name"], spec["stackOnCast"]["max"]))
    for uid, spec in SCALE.items():
        u = by.get(uid)
        if not u:
            print("[A] 找不到", uid); continue
        ult = dict(u.get("ult") or {})
        ult["scaleByCounter"] = spec["scaleByCounter"]
        u["ult"] = ult
        n += 1
        print("   %-22s 必杀随计数放大" % u["name"])
    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[A] 共接入 %d 张" % n)


if __name__ == "__main__":
    main()
