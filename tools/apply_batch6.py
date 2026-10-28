# -*- coding: utf-8 -*-
r"""
apply_batch6.py —— 批次 6：最后 8 枚 2 费棋子，至此 **111 条角色全部实装**

用法（排在 apply_batch5.py 之后）：
    python tools\apply_batch6.py
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
REPORT = os.path.join(ROOT, "tools", "batch6_report.json")

BATCH6 = {
    "607853": {   # 东堂[野蛮的一级] 2费 C 行/体术 —— 击杀成长
        "skill": {"name": "重击", "type": "strike", "power": 1.9, "panel": "phys"},
        "ult": {"name": "金勾臂", "type": "strike", "power": 3.3, "panel": "phys"},
        "mods": {"bf": 0.05},
        "design": "「任意敌人被击败时自身体术 +10%」→ 用低配必杀 + 小幅度黑闪，定位是滚雪球型基础卡",
    },
    "607841": {   # 加茂宪纪[御三家的血脉] 2费 C 影/术式 —— 三连击
        "skill": {"name": "五月的雨声", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.67, "panel": "phys"},
        "ult": {"name": "追踪射击", "type": "barrage", "hits": 3, "power": 1.2,
                "panel": "hybrid", "hybrid": True},
        "mods": {},
        "design": "「近战 3 连击」+「随机点名射击」→ 三连击 + 随机散射必杀",
    },
    "607991": {   # 禅院真希[天赐无才] 2费 C 幻/体术 —— 降暴抗
        "skill": {"name": "飛苦無", "type": "strike", "power": 0.7, "panel": "phys", "applyTaken": 0.15},
        "ult": {"name": "怒涛的斩击", "type": "strike", "power": 3.5, "panel": "phys"},
        "mods": {},
        "design": "「降低会心抵抗」→ 挂易伤；天与咒缚前的真希，纯基础卡",
    },
    "607851": {   # 究极机械丸[炮咒强化形态] 2费 C 夜/回复 —— 全体炮击
        "skill": {"name": "掩护火力", "type": "slam", "radius": 99, "power": 0.5, "panel": "magic"},
        "ult": {"name": "「三重大祓砲」", "type": "barrage", "hits": 4, "power": 1.1,
                "panel": "magic", "radius": 99},
        "mods": {"immuneControl": True, "mres": 0.10},
        "design": "「毒/黑暗/眩晕/混乱全部无效」→ 免疫控制 + 魔抗，是 2 费里少见的抗性卡",
    },
    "607854": {   # 熊猫[以最短直线] 2费 B 影/体术 —— 5 连击 + 复活
        "skill": {"name": "熊猫连击", "type": "barrage", "hits": 5, "sameTarget": True,
                  "power": 0.85, "panel": "phys"},
        "ult": {"name": "熊猫猛撞", "type": "slam", "radius": 99, "power": 2.6, "panel": "phys"},
        "mods": {"reviveLeft": 1, "revivePct": 0.35},
        "design": "5 连击普攻 + 全体必杀 + 核转换复活；第三张熊猫，定位是「连击型副坦」",
    },
    "607840": {   # 狗卷[反击的接力棒] 2费 C 影/回复 —— 自残群攻
        "skill": {"name": "「爆裂吧」", "type": "slam", "radius": 99, "power": 0.84, "panel": "magic"},
        "ult": {"name": "「坠落吧」", "type": "strike", "power": 9.0, "panel": "magic", "sure": True},
        "mods": {"selfDamageOnUlt": 0.05},
        "design": "「对象含强敌时自损」→ 必杀自损 5%；群攻 + 高倍单体两条路线",
    },
    "606019": {   # 东堂[友情的记忆] 2费 C 幻/体术 —— 扰乱 + 亲友
        "skill": {"name": "不义游戏", "type": "strike", "power": 1.2, "panel": "phys", "stun": 0.8},
        "ult": {"name": "亲友哟", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 1.4, "panel": "phys"},
        "mods": {"aura_power": 0.10},
        "design": "「扰乱 + 给亲友加暴击」→ 小眩晕 + 全队攻击光环；第三张东堂",
    },
    "614518": {   # 西宫桃[别小看我] 2费 S 影/回复 —— 暴击拐 + 眩晕
        "skill": {"name": "侦察", "type": "empower", "amp": 0.3, "dur": 3.0, "applyTaken": 0.3},
        "ult": {"name": "可爱地修理一顿", "type": "slam", "radius": 99, "power": 2.3,
                "panel": "magic", "stun": 1.0},
        "mods": {"dodge": 0.20, "aura_power": 0.08},
        "design": "「给全队暴击率 + 给敌人降暴抗」→ 自身增伤 + 群体易伤；必杀带眩晕",
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
    applied = []
    for cid, spec in BATCH6.items():
        u = by_id.get(cid)
        if not u:
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old); sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"; sk["source"] = "batch6"
        u["skill"] = sk
        ult = dict(spec["ult"]); ult["combat"] = True; ult["source"] = "batch6"
        bv = num((u.get("wikiStats") or {}).get("必杀值"))
        if bv > 0:
            u["ultCost"] = max(70, min(130, round(70 + (bv - 973) / (2334 - 973) * 60)))
            u["ultCostSource"] = "wiki"
        else:
            u["ultCost"] = 70 + int(u["cost"]) * 6
            u["ultCostSource"] = "default"
        u["ult"] = ult
        u["mods"] = spec.get("mods") or {}
        u["batch"] = 6
        u["design"] = spec.get("design", "")
        u["playable"] = True
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    # 清掉批次 3 之前遗留的 _basePlayable 中间字段（只影响可玩标记的幂等性，已无用途）
    for u in units:
        u.pop("_basePlayable", None)
        u.pop("costFromRarity", None)

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    playable = [u for u in units if u["playable"]]
    rep = {
        "applied": len(applied), "playable": len(playable), "total": len(units),
        "costDist": dict(sorted(Counter(u["cost"] for u in playable).items())),
        "rarityDist": dict(Counter(u["rarity"] for u in playable)),
        "withUlt": sum(1 for u in units if (u.get("ult") or {}).get("combat")),
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[batch6] 应用 %d 枚 → 可玩池 %d / %d" % (len(applied), len(playable), len(units)))
    print("[batch6] 费用分布 %s" % rep["costDist"])
    print("[batch6] 品质分布 %s" % rep["rarityDist"])
    print("[batch6] 有必杀 %d 张" % rep["withUlt"])


if __name__ == "__main__":
    main()
