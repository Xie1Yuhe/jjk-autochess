# -*- coding: utf-8 -*-
r"""
apply_domain.py —— 把「领域展开」做成真正的领域

问题：6 张带领域必杀的卡（五条×2、伏黑、宿傩、真人、陀艮）原来只是「倍率更高一点的群伤」，
      花 100 点必杀值开出来却和普通大招没区别。

目标（对标《幻影夜行》）：领域展开 = **改写战场规则一段时间**，
      己方获得强化、敌方受到限制，而不是单纯打一发。

做法：给必杀加 `domain` 字段，引擎在 `_cast` 里一次性应用：
  allyAmp     己方全体体术/术式提升
  allyGuard   己方全体减伤
  enemyTaken  敌方全体受到伤害提升
  enemyWeaken 敌方全体造成伤害降低
  enemyStun   开域瞬间全体眩晕

用法：
    python tools\apply_domain.py
    python tools\gen_text.py
    python tools\build_data.py
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

# 每张领域卡的「领域规则」+ 必杀本身的强化
DOMAINS = {
    # 五条「无量空处」：情报过载，全场压制
    "687394": {
        "domain": {"dur": 6, "selfGuard": 0.20, "enemyStun": 1.5, "enemyTaken": 0.60,
                     "enemyWeaken": 0.25, "ultBlock": True, "skillAoe": 0.9, "endMana": True},
        "why": "无量空处 = 把无限的情报灌进对手脑子。开域瞬间敌方全体眩晕 1.2 秒，"\
               "之后敌方受到伤害 +30%、造成伤害 -20%，己方体术/术式 +35%",
    },
    "640936": {
        "domain": {"dur": 7, "selfGuard": 0.18, "enemyStun": 1.2, "enemyTaken": 0.50,
                     "enemyWeaken": 0.20, "ultBlock": True, "skillAoe": 0.7, "endMana": True},
        "why": "同一个无量空处，但这是「无下限」形态，压制稍缓、己方增益更稳",
    },
    # 伏黑「嵌合暗翳庭」：影里全是式神
    "609120": {
        "domain": {"dur": 6, "selfGuard": 0.35, "enemyTaken": 0.45, "enemyWeaken": 0.35,
                     "enemyStun": 1.0, "ultBlock": True, "skillAoe": 0.6, "endMana": True},
        "why": "影之庭园。己方体术/术式 +30% 且减伤 12%，敌方受到伤害 +25%",
    },
    # 宿傩「伏魔御厨子」：无差别斩击，最纯粹的杀伤领域
    "644233": {
        "domain": {"dur": 6, "enemyTaken": 0.25, "enemyDot": 0.50,
                     "enemyStun": 0.6, "skillAoe": 1.1, "endMana": True},
        "why": "御厨子开张，一切都在斩击射程之内。敌方受到伤害 +40%、造成伤害 -30%，己方体术/术式 +25%",
    },
    # 真人「自闭圆顿裏」：无限循环的自我，主打削弱
    "619763": {
        "domain": {"dur": 5, "selfGuard": 0.30, "enemyTaken": 0.20, "enemyWeaken": 0.25,
                     "enemyStun": 1.0, "enemyMaxHpPct": 0.15, "skillAoe": 0.8, "endMana": True},
        "why": "自闭圆顿裏。敌方造成伤害 -35%，几乎打不动人；己方体术/术式 +20%",
    },
    # 陀艮「荡蕴平线」：式神之海
    "671525": {
        "domain": {"dur": 8, "selfGuard": 0.35, "allyAmp": 0.40, "enemyTaken": 0.10,
                     "enemyDot": 0.40, "ultBlock": True, "skillAoe": 0.85,
                     "skillMana": 40, "endMana": True},
        "why": "式神之海。己方体术/术式 +32%、减伤 10%，敌方受到伤害 +22%",
    },
    "607872": {
        "domain": {"dur": 6, "selfGuard": 0.30, "enemyTaken": 0.20, "enemyDot": 0.35,
                     "ultBlock": True, "skillAoe": 0.9, "skillMana": 20, "endMana": True},
        "why": "原文：领域内自身暴击/增伤/术式大幅提升、受伤-30%、回咒80；敌方全体炎持续伤害",
    },
    "607873": {
        "domain": {"dur": 6, "selfGuard": 0.20, "enemyWeaken": 0.33,
                     "ultBlock": True, "skillAoe": 0.7, "endMana": True},
        "why": "原文：领域内敌方全体造成伤害降低 33.18%",
    },

}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    done = []
    for uid, spec in DOMAINS.items():
        u = by_id.get(uid)
        if not u:
            print("[domain] 找不到", uid)
            continue
        ult = dict(u.get("ult") or {})
        ult["domain"] = spec["domain"]
        ult["isDomain"] = True
        u["ult"] = ult
        u["domainWhy"] = spec["why"]
        done.append((u["name"], ult.get("name"), spec["domain"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[domain] 强化 %d 个领域展开" % len(done))
    for name, uname, dm in done:
        print("   %-22s %s" % (name, uname))
        print("      " + " / ".join("%s=%s" % (k, v) for k, v in dm.items()))


if __name__ == "__main__":
    main()
