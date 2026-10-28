# -*- coding: utf-8 -*-
r"""
apply_batch5.py —— 批次 5：收尾 16 枚（5 费 ×4 + 1 费 ×12）

全部 111 条角色到此**全部实装**。

5 费 ×4：五条悟[0.2秒的领域展开]、五条悟[冰菓消溶]、五条悟[虚式「茈」]、伏黑甚尔[降灵]
1 费 ×12：伊地知[送别者]、伏黑惠[不平等的救赎]、吉野顺平[生命的价值]、熊猫[熊猫但不是熊猫]、
          真依[凌厉的子弹]、钉崎[为了保持自我]、龙胆咲[不服来战]、龙胆咲[灾祸转咒]、
          三轮霞[决意的迎击]、西宫桃[空中侦查]、真依[有效射程]、龙胆咲[心怀觉悟]

用法（排在 apply_batch4.py 之后）：
    python tools\apply_batch5.py
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
REPORT = os.path.join(ROOT, "tools", "batch5_report.json")

BATCH5 = {
    # ---------------------------------------------------- 5 费 ×4
    "687394": {   # 五条[0.2秒的领域展开] 5费 SSS 影/体术 —— 领域眩晕 + 自毁
        "skill": {"name": "无限的扩张", "type": "slam", "radius": 99, "power": 2.4, "panel": "magic"},
        "ult": {"name": "领域展开「无量空处」", "type": "slam", "radius": 99, "power": 5.0,
                "panel": "magic", "stun": 2.0, "applyTaken": 0.5, "sure": True},
        "mods": {"ultStart": 45, "retireOnUlt": True, "retireAura": 0.20},
        "design": "领域=全体眩晕 2s + 50% 易伤；代价是必杀后自毁（原作 11 回合后 / 放必杀后退场）",
    },
    "706347": {   # 五条[冰菓消溶] 5费 SS 行/体术 —— 纯辅助型
        "skill": {"name": "热血指导", "type": "empower", "amp": 0.5, "dur": 4.0},
        "ult": {"name": "稍微休息会吧", "type": "empower", "amp": 0.8, "dur": 5.0},
        "mods": {"invulnStart": 4.0, "aura_power": 0.15, "aura_haste": 0.10},
        "design": "唯一的纯辅助五条：全队攻击 +15%、攻速 +10%，开场 4 秒攻击无效化（被解除可再赋予→压成开场无敌）",
    },
    "612295": {   # 五条[虚式「茈」] 5费 SS 夜/术式 —— 核弹
        "skill": {"name": "应该优先解决你", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.9, "panel": "magic"},
        "ult": {"name": "虚式「茈」", "type": "slam", "radius": 99, "power": 9.0, "panel": "magic"},
        "mods": {"ultStart": 40, "retireOnUlt": True},
        "design": "全游戏单发倍率最高的必杀（9.0 倍全体术式），用后立刻自毁 —— 一换一核弹",
    },
    "674677": {   # 伏黑甚尔[降灵] 5费 A 行/体术 —— 高速连击刺客
        "skill": {"name": "乱击", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 1.35, "panel": "phys"},
        "ult": {"name": "噬向强者的獠牙", "type": "barrage", "hits": 5, "sameTarget": True,
                "power": 1.6, "panel": "phys", "dot": 0.02, "dotDur": 4},
        "mods": {"dodge": 0.20, "regen": True, "armor": 0.15},
        "design": "「天与暴君」= 20% 闪避 + 15% 减伤 + 每秒再生；必杀 5 连击附带刺伤 DOT",
    },
    # ---------------------------------------------------- 1 费 ×12
    "607994": {   # 伊地知[送别者] 1费 B 夜/体术 —— 全队减伤
        "skill": {"name": "危機管理", "type": "empower", "amp": 0.12, "dur": 3.0, "guard": 0.25},
        "ult": {"name": "我不会再错了", "type": "empower", "amp": 0.25, "dur": 3.0},
        "mods": {"aura_power": 0.06},
        "design": "「全队减伤 15.6%」→ 施法时自身护盾式减伤 + 常驻全队攻击光环",
    },
    "607989": {   # 伏黑惠[不平等的救赎] 1费 C 夜/回复 —— 基础单体
        "skill": {"name": "「蝦蟇」", "type": "drain", "power": 1.2, "panel": "magic"},
        "ult": {"name": "十種影法術", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 1.5, "panel": "magic"},
        "mods": {},
        "design": "最基础的 1 费术式卡：抽咒力的单体技 + 2 连击必杀，作为新手起手",
    },
    "607847": {   # 吉野顺平[生命的价值] 1费 C 影/回复 —— 护盾 + 毒
        "skill": {"name": "澱月", "type": "shield"},
        "ult": {"name": "别捣乱！", "type": "dot", "power": 1.4, "panel": "magic", "dot": 0.03, "dotDur": 4},
        "mods": {},
        "design": "「攻击无效化 3 回合」压成护盾；必杀挂毒 DOT",
    },
    "607993": {   # 熊猫[熊猫但不是熊猫] 1费 C 行/体术 —— 嘲讽坦克
        "skill": {"name": "同伴由我来保护！", "type": "empower", "amp": 0, "dur": 0.1,
                  "taunt": 1.5, "guard": 0.40},
        "ult": {"name": "熊猫热潮", "type": "barrage", "hits": 6, "sameTarget": True,
                "power": 0.55, "panel": "phys"},
        "mods": {"armor": 0.10},
        "design": "又一个 1 费坦克位（与「别小看人偶」同角色）：嘲讽 + 40% 减伤 + 6 连击必杀",
    },
    "607844": {   # 禅院真依[凌厉的子弹] 1费 C 行/体术 —— 眩晕 + 追击
        "skill": {"name": "掩护火力", "type": "stun", "power": 1.1, "panel": "phys", "stun": 1.0},
        "ult": {"name": "构筑术式", "type": "strike", "power": 3.5, "panel": "phys"},
        "mods": {"extra_attack": True},
        "design": "「3 连射带眩晕」→ stagger 眩晕；被动追击做成常驻",
    },
    "607990": {   # 钉崎[为了保持自我] 1费 C 影/回复 —— 易伤
        "skill": {"name": "芻霊呪法「簪」", "type": "strike", "power": 1.2,
                  "panel": "magic", "applyTaken": 0.20},
        "ult": {"name": "芻霊呪法「共鳴り」", "type": "strike", "power": 3.0,
                "panel": "magic", "applyTaken": 0.20},
        "mods": {},
        "design": "「钉子计数越多伤害越高」压成易伤叠层，1 费里少见的易伤位",
    },
    "607848": {   # 龙胆咲[不服来战] 1费 B 行/术式 —— 体术提升
        "skill": {"name": "灾难逆转咒", "type": "strike", "power": 1.5,
                  "panel": "hybrid", "hybrid": True},
        "ult": {"name": "灾难扭转魔法", "type": "strike", "power": 2.0,
                "panel": "hybrid", "hybrid": True},
        "mods": {"armor": 0.10},
        "design": "「体术提升 27.8% + 复合伤害」→ 复合面板 + 常驻减伤（顽健）",
    },
    "607995": {   # 龙胆咲[灾祸转咒] 1费 B 夜/术式 —— 自残换攻
        "skill": {"name": "「災渦転呪」", "type": "empower", "amp": 0.4, "dur": 4.0},
        "ult": {"name": "「災渦転呪・連撃」", "type": "barrage", "hits": 6, "sameTarget": True,
                "power": 0.5, "panel": "hybrid", "hybrid": True},
        "mods": {"selfDamageOnUlt": 0.03},
        "design": "「对自身造成 3% HP 伤害」→ 必杀自损小额；技能是自增伤",
    },
    "607845": {   # 三轮霞[决意的迎击] 1费 B 幻/术式 —— 反击
        "skill": {"name": "新·阴流·简易领域", "type": "empower", "amp": 0.10, "dur": 2.0, "taunt": 1.5},
        "ult": {"name": "「拔刀」", "type": "strike", "power": 2.4,
                "panel": "hybrid", "hybrid": True},
        "mods": {"counterMult": 1.0},
        "design": "第三张三轮霞：以「反击」为核心，配合另两张可组三卡体系",
    },
    "607835": {   # 西宫桃[空中侦查] 1费 A 夜/回复 —— 眩晕/闪避
        "skill": {"name": "咒力旋风", "type": "stun", "power": 0.8, "panel": "magic", "stun": 1.5},
        "ult": {"name": "咒力风暴", "type": "slam", "radius": 99, "power": 2.2,
                "panel": "magic", "stun": 1.0},
        "mods": {"dodge": 0.20},
        "design": "「全体眩晕 + 自身回避」→ 群体眩晕必杀 + 20% 闪避",
    },
    "714626": {   # 禅院真依[有效射程] 1费 SS 影/术式 —— 追击 + 复合
        "skill": {"name": "闪光弹", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.75, "panel": "hybrid", "hybrid": True},
        "ult": {"name": "狙击", "type": "strike", "power": 4.2,
                "panel": "hybrid", "hybrid": True},
        "mods": {"extra_attack": True},
        "design": "「降低暴击抗性 + 自身追击」→ 3 连击复合 + 常驻追击；1 费里唯一 SS 档",
    },
    "628287": {   # 龙胆咲[心怀觉悟] 1费 A 夜/术式 —— 复活 + 复合
        "skill": {"name": "「灾祸转咒」", "type": "slam", "radius": 99, "power": 0.9,
                  "panel": "hybrid", "hybrid": True},
        "ult": {"name": "觉悟之拳", "type": "strike", "power": 5.0,
                "panel": "hybrid", "hybrid": True},
        "mods": {"reviveLeft": 1, "revivePct": 0.30},
        "design": "「顽健：战斗开始时复活状态 1 次」直接保留；血量越低越强压成常驻复合伤害",
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

    for cid, spec in BATCH5.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old)
        sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"
        sk["source"] = "batch5"
        u["skill"] = sk

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch5"
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
        u["batch"] = 5
        u["design"] = spec.get("design", "")
        if not u.get("playable"):
            u["playable"] = True
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    playable = [u for u in units if u["playable"]]
    rep = {
        "applied": len(applied), "playable": len(playable), "total": len(units),
        "costDist": dict(sorted(Counter(u["cost"] for u in playable).items())),
        "list": [{"name": a[0], "cost": a[1], "tier": a[2], "ultCost": a[3]} for a in applied],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[batch5] 应用 %d 枚，可玩池 %d / %d" % (len(applied), len(playable), len(units)))
    print("[batch5] 费用分布 %s" % rep["costDist"])
    for name, cost, tier, uc in applied:
        print("   %-24s %s费 %-3s 必杀槽 %d" % (name, cost, tier, uc))


if __name__ == "__main__":
    main()
