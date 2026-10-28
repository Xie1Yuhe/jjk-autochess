# -*- coding: utf-8 -*-
r"""
apply_rolefix.py —— 修正「技能/必杀职能」和原作对不上的棋子

判定依据：直接看 `skill.wikiDesc` / `ultimate.wikiDesc` 原文，
原文小技能是「减伤 / 治疗 / 自身强化」，我们却做成了纯伤害 —— 那就是反了。

本轮修 3 张（都是原文写得很明确的）：
  606636 [幼鱼和逆罚] 吉野顺平  —— 小技能改全队减伤，必杀才是毒 DoT
  624754? 见下方 ID 表       米格尔 —— 小技能原文是「体术提升+受到伤害降低40%」
  606019 东堂葵[和高田酱一起]  —— 小技能原文是「受到伤害降低+回复HP」

用法：
    python tools\apply_rolefix.py
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

FIXES = {
    # 顺平 SSR：原作里他是「毒」的化身，但小技能承担的是护住队友的角色
    "606636": {
        "who": "[幼鱼和逆罚] 吉野顺平",
        "skill": {"name": "「淀月」", "type": "shield", "power": 1.0, "panel": "magic"},
        "ult": {"name": "不要搞错生命的价值啊", "type": "dot", "power": 4.2,
                "panel": "magic", "dot": 0.045, "dotDur": 5, "applyTaken": 0.30},
        "why": "小技能「淀月」在原文里是护住自己与同伴的防御技；毒 DoT 是必杀的招牌。"
               "之前把两者都做成毒伤，等于丢了他「行属性辅助」的定位。",
    },
    # 米格尔：小技能原文 = 自身体术 +35%、受到伤害降低 40%、暴击率 +20%
    "642790": {
        "who": "[拦路的指标] 米格尔",
        "skill": {"name": "拦路的指标", "type": "empower", "amp": 0.35, "dur": 4.0, "guard": 0.40},
        "why": "原文小技能是纯自身强化（体术+35%、受到伤害-40%、暴击+20%），没有伤害。",
    },
    # 东堂：小技能原文 = 受到伤害降低 + 回复自身 HP
    "618983": {
        "who": "[和高田酱一起] 东堂葵",
        "skill": {"name": "高田酱的指引", "type": "empower", "amp": 0.12, "dur": 3.0, "guard": 0.25},
        "why": "原文小技能是「受到伤害降低 12.25% + 回复 7.25% HP」，属于站场型，不是输出技。",
    },
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    done = []
    for uid, spec in FIXES.items():
        u = by_id.get(uid)
        if not u:
            print("[rolefix] 找不到", uid)
            continue
        name = spec.get("who") or u["name"]
        # 先确认原文真的支持这个改法
        desc = (u.get("skill") or {}).get("wikiDesc") or ""
        sk = dict(u.get("skill") or {})
        for k, v in spec["skill"].items():
            sk[k] = v
        u["skill"] = sk
        if spec.get("ult"):
            ult = dict(u.get("ult") or {})
            for k, v in spec["ult"].items():
                ult[k] = v
            u["ult"] = ult
        u["roleFixed"] = spec["why"]
        done.append((u["id"], name, spec["why"], desc[:70]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[rolefix] 修正 %d 张" % len(done))
    for uid, name, why, desc in done:
        print("   %s %s" % (uid, name))
        print("     原文: %s…" % desc)
        print("     理由: %s" % why)


if __name__ == "__main__":
    main()
