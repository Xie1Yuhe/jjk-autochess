# -*- coding: utf-8 -*-
r"""
apply_states.py —— 把「状态切换 / 持续自我增益」做成真实机制

原作里很多角色的招牌是：**放技能 → 进入一个持续若干回合的状态 → 状态期间技能变招**。
之前我们一律压成「一次性自我增伤」，这是还原度损失最大的一处。

引擎已支持 `skill.enterState`：
  { name, dur, amp, guard, bf, skill:{...} }
  · 施放后进入状态 dur 秒，期间 ad/spell ×(1+amp)、减伤 guard、黑闪 +bf
  · 状态期间再放技能 → 换成 `skill`（变化后的版本）
  · 到期自动回退数值

本脚本按 wiki 原文给这些卡配状态。第一批挑原文写得最明确的 12 张。

用法：
    python tools\apply_states.py
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

# id -> (状态定义, 原文依据)
STATES = {
    # 灰原「蒸升」：暴击率 +80%，一部分技能效果变化
    "719571": ({
        "name": "蒸升", "dur": 5.0, "amp": 0.25, "bf": 0.35,
        "skill": {"name": "蒸汽咒法「蒸升」", "type": "strike", "power": 2.6,
                  "panel": "magic", "crit": 1.5},
    }, "原文：赋予自身「蒸升」（5回合）、暴击率+80%、一部分技能效果变化"),
    # 漆英司「全开速」：连锁计数 10 时开状态，技能变 6 连击
    "701554": ({
        "name": "全开速", "dur": 4.0, "amp": 0.15, "bf": 0.2,
        "skill": {"name": "连锁纹・全开", "type": "barrage", "hits": 6,
                  "sameTarget": True, "power": 0.85, "panel": "phys", "crit": 1.4},
    }, "原文：赋与「全开速」、技能变化为 6 连击、暴击率+30%"),
    # 东堂[友情的记忆]：原文只有「挚友」暴击 buff，没有大猩猩模式
    "606019": ({
        "name": "挚友", "dur": 20.0, "amp": 0.15, "bf": 0.25,
        "skill": {"name": "挚友・连击", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 1.0, "panel": "phys", "crit": 1.4},
    }, "原文：必杀提升自身与【挚友】友军的暴击率 39.98%"),
    # 熊猫[别小看人偶]「大猩猩模式」：体术 +99.95%，技能变化
    "606014": ({
        "name": "大猩猩模式", "dur": 20.0, "amp": 0.40,
        "skill": {"name": "猩猩连击", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 1.05, "panel": "phys"},
    }, "原文：赋予自身大猩猩模式、体术提升 99.95%，技能随之变化"),
    # 三轮霞「纳刀」：纳刀计数 ≥7 时必杀变化、计数越低越弱
    "625876": ({
        "name": "纳刀", "dur": 5.0, "amp": 0.2,
        "skill": {"name": "纳刀・居合", "type": "strike", "power": 3.0,
                  "panel": "hybrid", "hybrid": True, "applyTaken": 0.25},
    }, "原文：纳刀计数为 1 以上时技能完全变化、造成伤害提升"),
    # 日下部「简易领域」：反击状态 + 体术提升
    "678629": ({
        "name": "简易领域", "dur": 4.0, "guard": 0.15,
        "skill": {"name": "拔刀・简易领域", "type": "slam", "radius": 99,
                  "power": 2.2, "panel": "phys", "crit": 1.2},
    }, "原文：赋予「简易领域」状态 4 回合、反击 2 次、体术提升 30%"),
    # 猪野「灵龟」：概率闪避 + 自身造成伤害降低（副作用）
    "658698": ({
        "name": "灵龟", "dur": 4.0, "guard": 0.2,
        "skill": {"name": "灵龟反击", "type": "strike", "power": 2.8,
                  "panel": "magic", "crit": 1.3},
    }, "原文：赋予自身灵龟状态 4 回合、概率闪避、造成伤害降低（副作用）"),
    # 伏黑「浑」：召唤玉犬，技能变招
    "676882": ({
        "name": "脱兔", "dur": 4.0, "guard": 0.15,
        "skill": {"name": "脱兔・连携", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.95, "panel": "magic"},
    }, "原文：召唤脱兔分担伤害、技能随之变化"),
    # 漏瑚「咒灵的矜持」：领域内的自身强化
    "628287": ({
        "name": "顽健", "dur": 4.0, "amp": 0.25,
        "skill": {"name": "灾祸转咒・燃", "type": "slam", "radius": 99,
                  "power": 1.6, "panel": "hybrid", "hybrid": True},
    }, "原文：自身生命值越低效果越大、持续强化"),
    # 真希「全力一刀」：0 消耗，状态里技能变化
    "652057": ({
        "name": "全力一刀", "dur": 3.0, "amp": 0.2,
        "skill": {"name": "全力一刀・砍倒", "type": "strike", "power": 7.5,
                  "panel": "phys", "crit": 1.4},
    }, "原文：赋予自身「全力一刀」状态 2 回合、技能追加效果"),
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    done = []
    for uid, (spec, why) in STATES.items():
        u = by_id.get(uid)
        if not u:
            print("[states] 找不到", uid)
            continue
        sk = dict(u.get("skill") or {})
        sk["enterState"] = spec
        sk["stateWhy"] = why
        u["skill"] = sk
        done.append((u["name"], spec["name"], spec["dur"], why))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[states] 接入状态机制 %d 张" % len(done))
    for name, sname, dur, why in done:
        print("   %-24s → 「%s」%.0f 秒" % (name, sname, dur))
        print("      %s" % why)


if __name__ == "__main__":
    main()
