# -*- coding: utf-8 -*-
r"""
apply_batch3.py —— 批次 3：14 枚低费棋子（补厚 1–2 费池）

1 费 ×8：七海[不上班族术师]、狗卷[诅咒的言灵]、结木[呪錬礎術]、灰原[燃烧的意志]、
        真依[最后的子弹]、伊地知[慰劳的接送]、三轮霞[残心]、结木[作为术师的觉悟]
2 费 ×6：夜蛾[咒骸临战]、家入[反转术式]、冥冥[群鸦翩舞之夜]、
        乐岩寺[咒力的旋律]、夜蛾[教育者]、与幸吉[目睹一切]

用法（排在 apply_batch2.py 之后）：
    python tools\apply_batch3.py
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
REPORT = os.path.join(ROOT, "tools", "batch3_report.json")

BATCH3 = {
    # ---------------------------------------------------- 1 费 ×8
    "607846": {   # 七海[不上班族术师] 1费 A 幻/术式 —— 黑闪引擎
        "skill": {"name": "7:3", "type": "strike", "power": 1.8, "panel": "hybrid", "hybrid": True},
        "ult": {"name": "十劃呪法", "type": "strike", "power": 5.0, "panel": "hybrid", "hybrid": True},
        "mods": {"bf": 0.25, "aura_power": 0.10, "manaOnCrit": 10},
        "design": "黑闪率 25% + 暴击回咒；必杀把「全队增伤」压成 aura_power",
    },
    "607992": {   # 狗卷[诅咒的言灵] 1费 S 幻/回复 —— 护盾 + 自残
        "skill": {"name": "「防住」", "type": "shield"},
        "ult": {"name": "「爆破吧」", "type": "strike", "power": 9.6, "panel": "magic", "applyTaken": 0.20},
        "mods": {"selfDamageOnUlt": 0.15},
        "design": "「防住」= 全队护盾；咒言反噬 = 必杀自损 15%",
    },
    "607996": {   # 结木[呪錬礎術] 1费 S 行/回复 —— 回咒辅助
        "skill": {"name": "呪力支援", "type": "buff"},
        "ult": {"name": "咒錬礎术", "type": "empower", "amp": 1.2, "dur": 4.0},
        "mods": {"aura_power": 0.08},
        "design": "「给队友回咒」压成全队攻击增益（自走棋没有队友咒力转移通道）",
    },
    "719571": {   # 灰原[燃烧的意志] 1费 SS 幻/术式 —— 高暴击
        "skill": {"name": "蒸汽咒法", "type": "strike", "power": 1.6, "panel": "magic", "crit": 1.3},
        "ult": {"name": "蒸汽咒法「临界冲」", "type": "strike", "power": 4.5, "panel": "magic", "crit": 1.6},
        "mods": {"bf": 0.30, "manaOnCrit": 10},
        "design": "「蒸升」= 高暴击状态；暴击回咒形成循环",
    },
    "635863": {   # 真依[最后的子弹] 1费 S 幻/体术 —— 追击 + 易伤
        "skill": {"name": "再装填", "type": "slam", "radius": 99, "power": 0.6,
                  "panel": "phys", "applyTaken": 0.30},
        "ult": {"name": "让我来教教你该怎么说话", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 1.6, "panel": "phys", "applyTaken": 0.80},
        "mods": {"extra_attack": True},
        "design": "「追击」= 施法后追加普攻；易伤最高叠到 80%",
    },
    "712114": {   # 伊地知[慰劳的接送] 1费 S 夜/体术 —— 夜队专拐
        "skill": {"name": "情报收集", "type": "empower", "amp": 0.5, "dur": 3.5},
        "ult": {"name": "连携调查", "type": "empower", "amp": 0.5, "dur": 3.5},
        "mods": {"aura_power": 0.12},
        "design": "「给夜特性队友加成」压成全队攻击光环 +12%（自走棋没有特性限定 buff）",
    },
    "625876": {   # 三轮霞[残心] 1费 SSS 影/术式 —— 纳刀计数
        "skill": {"name": "纳刀", "type": "empower", "amp": 0.5, "dur": 3.5},
        "ult": {"name": "一闪", "type": "strike", "power": 4.0, "panel": "magic"},
        "mods": {"counter_counter": "nada", "max_nada": 15, "grow_nada": 0.02, "aura_power": 0.10},
        "design": "纳刀计数每层 +2% 攻击（上限 15 层）；与「疾走」同角色的新版 —— 可触发异格联动",
    },
    "607849": {   # 结木[作为术师的觉悟] 1费 A 夜/回复 —— 护盾 + 眩晕
        "skill": {"name": "防卫壁", "type": "shield"},
        "ult": {"name": "结界牢", "type": "stun", "power": 5.8, "panel": "magic", "stun": 1.2},
        "mods": {},
        "design": "「攻击无效化」压成护盾；必杀带眩晕",
    },
    # ---------------------------------------------------- 2 费 ×6
    "629916": {   # 夜蛾[咒骸临战] 2费 SSS 行/术式 —— 召唤
        "skill": {"name": "到你出场了！莫啾！布拉潘！", "type": "summon"},
        "ult": {"name": "彻底指导！凯西！", "type": "slam", "radius": 99, "power": 1.2,
                "panel": "hybrid", "hybrid": True, "applyTaken": 0.5},
        "mods": {"aura_power": 0.12},
        "design": "「召唤咒骸」直接用 summon 机制；必杀是全体复合 + 50% 易伤",
    },
    "607834": {   # 家入[反转术式] 2费 B 影/体术 —— 唯一纯奶
        "skill": {"name": "反転術式（小）", "type": "heal"},
        "ult": {"name": "反転術式（大）", "type": "heal"},
        "mods": {"healAlly": {"cost": 12, "pct": 0.08, "maxHpPct": 0.7, "interval": 3}},
        "design": "全游戏唯一的纯治疗位：主动治疗 + 反转术式被动奶",
    },
    "652636": {   # 冥冥[群鸦翩舞之夜] 2费 A 幻/体术 —— 全体体术
        "skill": {"name": "无赦强袭", "type": "slam", "radius": 99, "power": 1.4, "panel": "phys"},
        "ult": {"name": "「神风」", "type": "strike", "power": 6.0, "panel": "phys"},
        "mods": {"ultStart": 15},
        "design": "全体 2 连击体术；与「美刃的轮舞」同角色 —— 可触发异格联动",
    },
    "629917": {   # 乐岩寺[咒力的旋律] 2费 S 夜/回复 —— 控制
        "skill": {"name": "咒力之音", "type": "stun", "power": 1.5, "panel": "magic", "stun": 1.5},
        "ult": {"name": "咒力的旋律", "type": "slam", "radius": 99, "power": 2.4,
                "panel": "magic", "applyWeaken": 0.5},
        "mods": {"aura_power": 0.08},
        "design": "「扰乱 + 眩晕」打控制；必杀是全体削弱 50%（与花御同源、数值更高）",
    },
    "607837": {   # 夜蛾[教育者] 2费 S 幻/术式 —— 高频易伤
        "skill": {"name": "去吧！凯西！", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.55, "panel": "magic", "applyTaken": 0.48},
        "ult": {"name": "咒骸大进击", "type": "barrage", "hits": 6, "sameTarget": True,
                "power": 0.8, "panel": "magic", "applyTaken": 0.5},
        "mods": {},
        "design": "4/6 连击每次都挂易伤 —— 越打越疼的滚雪球型",
    },
    "645834": {   # 与幸吉[目睹一切] 2费 S 夜/术式 —— 印记叠层
        "skill": {"name": "三阵特攻", "type": "strike", "power": 1.2,
                  "panel": "hybrid", "hybrid": True, "applyTaken": 0.2},
        "ult": {"name": "「大祓炮」", "type": "slam", "radius": 99, "power": 2.8, "panel": "magic"},
        "mods": {"debuffBonus": 0.08},
        "design": "「机械丸指示物越多倍率越高」做成按目标减益数增伤（复用弱体特攻）",
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

    for cid, spec in BATCH3.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old)
        sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"
        sk["source"] = "batch3"
        u["skill"] = sk

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch3"
        bv = num((u.get("wikiStats") or {}).get("必杀值"))
        if spec.get("ultCost"):
            u["ultCost"] = int(spec["ultCost"])
            u["ultCostSource"] = "design"
        elif bv > 0:
            u["ultCost"] = max(70, min(130, round(70 + (bv - 973) / (2334 - 973) * 60)))
            u["ultCostSource"] = "wiki"
        else:
            u["ultCost"] = 70 + int(u["cost"]) * 6
            u["ultCostSource"] = "default"
        u["ult"] = ult
        u["mods"] = spec.get("mods") or {}
        u["batch"] = 3
        u["design"] = spec.get("design", "")
        if not u.get("playable"):
            u["playable"] = True
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    playable = [u for u in units if u["playable"]]
    rep = {
        "applied": len(applied),
        "playable": len(playable),
        "costDist": dict(sorted(Counter(u["cost"] for u in playable).items())),
        "list": [{"name": a[0], "cost": a[1], "tier": a[2], "ultCost": a[3]} for a in applied],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[batch3] 应用 %d 枚，可玩池 %d" % (len(applied), len(playable)))
    print("[batch3] 费用分布 %s" % rep["costDist"])
    for name, cost, tier, uc in applied:
        print("   %-24s %s费 %-3s 必杀槽 %d" % (name, cost, tier, uc))


if __name__ == "__main__":
    main()
