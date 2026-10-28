# -*- coding: utf-8 -*-
r"""
apply_batch4.py —— 批次 4：14 枚（剩余 3 费 ×8 + 4 费 ×6）

用法（排在 apply_batch3.py 之后）：
    python tools\apply_batch4.py
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
REPORT = os.path.join(ROOT, "tools", "batch4_report.json")

BATCH4 = {
    # ---------------------------------------------------- 3 费 ×8
    "606010": {   # 狗卷[觉悟的咒言] 3费 B 行/回复 —— 易伤 + 自残
        "skill": {"name": "「粉碎吧」", "type": "strike", "power": 3.2,
                  "panel": "magic", "applyTaken": 0.23},
        "ult": {"name": "吹飞吧", "type": "strike", "power": 12.0, "panel": "magic"},
        "mods": {"selfDamageOnUlt": 0.12},
        "design": "「受伤提升 23%」+ 咒言自残；被动「保护队友 3 次」压成必杀代价，避免再做一套格挡系统",
    },
    "605992": {   # 伏黑[继承的术式] 3费 A 影/回复 —— 召唤玉犬
        "skill": {"name": "满象", "type": "slam", "radius": 99, "power": 1.3, "panel": "magic"},
        "ult": {"name": "玉犬「浑」", "type": "summon"},
        "mods": {"armor": 0.10},
        "design": "「召唤玉犬浑」直接用 summon；「式神的守护」压成 10% 减伤",
    },
    "649666": {   # 家入[拯救生命] 3费 SSS 行/体术 —— 治疗 + 易伤
        "skill": {"name": "情报共享", "type": "slam", "radius": 99, "power": 0.5,
                  "panel": "phys", "applyTaken": 0.15},
        "ult": {"name": "可以随意解剖吧", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.0, "panel": "phys"},
        "mods": {"healAlly": {"cost": 15, "pct": 0.10, "maxHpPct": 0.4, "interval": 4}},
        "design": "「队友残血时回复全队 30%」压成 healAlly；必杀 4 连击",
    },
    "606003": {   # 禅院真希[叛逆的吊车尾] 3费 C 幻/体术 —— 零消耗循环
        "skill": {"name": "旋回", "type": "slam", "radius": 99, "power": 1.4, "panel": "phys"},
        "ult": {"name": "游雲乱舞", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 1.3, "panel": "phys", "crit": 1.2},
        "mods": {"ultStart": 20, "mana_on_cast": 10},
        "design": "原作「所有技能都不消耗咒力」→ 高回咒（mana_on_cast）+ 开场必杀值，靠频率取胜",
    },
    "605996": {   # 钉崎[铁骨娘] 3费 S 行/回复 —— 越残越强
        "skill": {"name": "刍灵咒法「共鸣」", "type": "strike", "power": 4.0,
                  "panel": "magic", "applyTaken": 0.20},
        "ult": {"name": "刍灵咒法「簪」", "type": "strike", "power": 6.0, "panel": "magic"},
        "mods": {"debuffBonus": 0.10},
        "design": "「自身 HP 越少增伤越高」压成按目标减益增伤（自走棋里血量不可控，做成队伍协同）",
    },
    "683430": {   # 东堂[你这样就满足了吗？] 3费 SSS 夜/体术 —— 9 连击
        "skill": {"name": "不义游戏组合技", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.65, "panel": "phys"},
        "ult": {"name": "最高潮☆JUMPING！", "type": "barrage", "hits": 9, "sameTarget": True,
                "power": 0.9, "panel": "phys", "crit": 1.2, "sure": True},
        "mods": {"extra_attack": True, "bf": 0.15},
        "design": "必杀 9 连击（第 9 击必暴 → crit）；「队友黑闪后追打」做成常驻追击",
    },
    "678629": {   # 日下部[化解锐刃] 3费 S 行/体术 —— 简易领域
        "skill": {"name": "新·阴流「简易领域」", "type": "empower", "amp": 0.3, "dur": 4.0,
                  "taunt": 2.0, "guard": 0.40},
        "ult": {"name": "新·阴流「拔刀」", "type": "slam", "radius": 99, "power": 2.8,
                "panel": "phys", "crit": 1.2},
        "mods": {"counterMult": 1.6, "mres": 0.20},
        "design": "「简易领域 + 反击 2 次 + 全体术式减伤 40%」→ 嘲讽 + 40% 减伤 + 1.6 倍反击",
    },
    "717469": {   # 猪野[不挠的瑞兽] 3费 SSS 夜/术式 —— 复合
        "skill": {"name": "三番「麒麟」", "type": "strike", "power": 1.6,
                  "panel": "hybrid", "hybrid": True},
        "ult": {"name": "实事求是，严于律己", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 1.4, "panel": "hybrid", "hybrid": True, "applyTaken": 0.20},
        "mods": {"aura_power": 0.08},
        "design": "「夜特性受到伤害提升」→ 易伤 + 全队光环",
    },
    # ---------------------------------------------------- 4 费 ×6
    "606028": {   # 七海[十划呪法] 4费 S 夜/术式 —— 黑闪引擎
        "skill": {"name": "十划呪法", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.55, "panel": "hybrid", "hybrid": True},
        "ult": {"name": "十划呪法「瓦落瓦落」", "type": "slam", "radius": 99, "power": 2.0,
                "panel": "hybrid", "hybrid": True},
        "mods": {"bf": 0.15, "manaOnCrit": 12},
        "design": "暴击/黑闪回咒的循环；必杀是 8 连击全体复合（压成单段 2.0）",
    },
    "713476": {   # 乐岩寺[老奸巨猾摇滚] 4费 SS 幻/回复 —— 幻属双易伤
        "skill": {"name": "咒力的律动", "type": "slam", "radius": 99, "power": 1.0,
                  "panel": "magic", "applyTaken": 0.30},
        "ult": {"name": "杀了老夫试试看", "type": "slam", "radius": 99, "power": 1.6,
                "panel": "magic", "applyTaken": 0.30},
        "mods": {"ultStart": 20},
        "design": "「术式与体术受到伤害各 +30%」压成统一易伤 30%；调谐计数做成开场必杀值",
    },
    "619762": {   # 虎杖[注入咒力吧] 4费 A 影/体术 —— 眩晕必杀
        "skill": {"name": "咒力连打", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.9, "panel": "phys"},
        "ult": {"name": "贯穿的咒力之拳", "type": "strike", "power": 7.0,
                "panel": "phys", "stun": 1.2},
        "mods": {"bf": 0.12},
        "design": "必杀带眩晕（对应原作 76% 眩晕）；三连打保留手感",
    },
    "622643": {   # 夏油杰[为了保护非术师] 4费 S 夜/术式 —— 复合 + 吸收
        "skill": {"name": "咒灵操术（乙）", "type": "strike", "power": 1.9,
                  "panel": "hybrid", "hybrid": True, "applyTaken": 0.18},
        "ult": {"name": "「虹龙」", "type": "strike", "power": 6.0,
                "panel": "hybrid", "hybrid": True},
        "mods": {"manaOnKill": 25},
        "design": "体术+术式复合；「吸收」= 击杀回 25 咒力（与大义同源，但这是复合型）",
    },
    "689190": {   # 虎杖[被托付的生命] 4费 SSS 夜/体术 —— 六连击
        "skill": {"name": "锤踢", "type": "strike", "power": 3.2, "panel": "phys"},
        "ult": {"name": "不挠的反击", "type": "barrage", "hits": 6, "sameTarget": True,
                "power": 0.9, "panel": "phys", "applyTaken": 0.15},
        "mods": {"aura_power": 0.10},
        "design": "必杀 6 连击 + 夜属易伤；「对友方全体赋予夜特性增伤」压成全队攻击光环",
    },
    "610359": {   # 虎杖[轻快的身体] 4费 S 幻/体术 —— 必黑闪
        "skill": {"name": "飞踢", "type": "strike", "power": 2.4, "panel": "phys", "armNext": 0.3},
        "ult": {"name": "咒力乱打", "type": "strike", "power": 9.0,
                "panel": "phys", "crit": 1.5, "applyTaken": 0.45},
        "mods": {"bf": 0.20},
        "design": "「必杀必定黑闪」→ crit 1.5；「体术易伤 45%」直接保留",
    },
}


def num(s):
    try:
        return int(float(str(s).replace(",", "")))
    except Exception:
        return 0


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    applied, missing = [], []

    for cid, spec in BATCH4.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old)
        sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"
        sk["source"] = "batch4"
        u["skill"] = sk

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch4"
        bv = num((u.get("wikiStats") or {}).get("必杀值"))
        if spec.get("ultCost"):
            u["ultCost"] = int(spec["ultCost"]); u["ultCostSource"] = "design"
        elif bv > 0:
            u["ultCost"] = max(70, min(130, round(70 + (bv - 973) / (2334 - 973) * 60)))
            u["ultCostSource"] = "wiki"
        else:
            u["ultCost"] = 70 + int(u["cost"]) * 6
            u["ultCostSource"] = "default"
        u["ult"] = ult
        u["mods"] = spec.get("mods") or {}
        u["batch"] = 4
        u["design"] = spec.get("design", "")
        if not u.get("playable"):
            u["playable"] = True
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    playable = [u for u in units if u["playable"]]
    rep = {
        "applied": len(applied), "playable": len(playable),
        "costDist": dict(sorted(Counter(u["cost"] for u in playable).items())),
        "list": [{"name": a[0], "cost": a[1], "tier": a[2], "ultCost": a[3]} for a in applied],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[batch4] 应用 %d 枚，可玩池 %d" % (len(applied), len(playable)))
    print("[batch4] 费用分布 %s" % rep["costDist"])
    for name, cost, tier, uc in applied:
        print("   %-24s %s费 %-3s 必杀槽 %d" % (name, cost, tier, uc))


if __name__ == "__main__":
    main()
