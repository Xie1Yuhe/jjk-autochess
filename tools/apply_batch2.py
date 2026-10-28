# -*- coding: utf-8 -*-
r"""
apply_batch2.py —— 批次 2：14 枚棋子（领域型 + 剩余高人气角色）

七海建人 ×4、真人 ×2、漏瑚 ×2、花御、东堂葵、加茂宪伦、里梅、米格尔、陀艮、冥冥。

冥冥两个形态原先都未实装，本批把「美刃的轮舞」提升为可玩（可玩池 58 → 59）。

用法（排在 apply_batch1.py 之后）：
    python tools\apply_batch2.py
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
REPORT = os.path.join(ROOT, "tools", "batch2_report.json")

PROMOTE = ["722687"]   # 冥冥「美刃的轮舞」

BATCH2 = {
    # ------------------------------------------------------ 七海建人
    "632100": {   # 4费 SS 影/术式 —— 复合暴击引擎
        "skill": {"name": "尽快解决", "type": "barrage", "hits": 2, "sameTarget": True,
                  "power": 1.2, "panel": "hybrid", "hybrid": True},
        "ult": {"name": "十划咒法", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.4, "panel": "hybrid", "hybrid": True, "crit": 1.3},
        "mods": {"bf": 0.15, "manaOnCrit": 12, "aura_power": 0.08},
        "design": "复合 2 连击 + 高暴击；暴击回咒形成循环；全队影属增伤做成 aura_power",
    },
    "695641": {   # 3费 SSS 夜/术式 —— 不屈复活
        "skill": {"name": "十划咒法", "type": "slam", "radius": 99, "power": 1.6,
                  "panel": "hybrid", "hybrid": True},
        "ult": {"name": "做好觉悟了吧", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 1.2, "panel": "hybrid", "hybrid": True},
        "mods": {"reviveLeft": 1, "revivePct": 0.35, "armor": 0.10},
        "design": "「不屈」= 首次阵亡 35% 生命复活；全体复合 3 连击",
    },
    "668491": {   # 3费 SSS 幻/术式 —— 专拐
        "skill": {"name": "划断", "type": "strike", "power": 1.15, "panel": "hybrid",
                  "hybrid": True, "crit": 1.4, "applyTaken": 0.15},
        "ult": {"name": "十划咒法", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 1.3, "panel": "hybrid", "hybrid": True},
        "mods": {"mana_on_cast": 12, "aura_power": 0.10},
        "design": "必定暴击（crit 1.4）；给全队幻属增伤（aura_power）；多种回咒",
    },
    "621266": {   # 3费 S 行/术式 —— 弱点连打
        "skill": {"name": "咒力之拳", "type": "strike", "power": 1.5, "panel": "hybrid",
                  "hybrid": True, "applyTaken": 0.22},
        "ult": {"name": "一定要在这里祓除掉", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.0, "panel": "hybrid", "hybrid": True, "lastHitBf": True},
        "mods": {"ultStart": 15, "bf": 0.12, "elemHunter": 0.15},
        "design": "必杀第 4 段必定黑闪；技能附带「受到伤害提升」",
    },
    # ------------------------------------------------------ 真人
    "619763": {   # 3费 A 夜/术式 —— 即死处决
        "skill": {"name": "变形攻击", "type": "strike", "power": 2.4, "panel": "magic",
                  "execute": 0.25},
        "ult": {"name": "领域展开「自闭圆顿裏」", "type": "slam", "radius": 99, "power": 1.2,
                "panel": "magic", "execute": 0.30, "dot": 0.02, "dotDur": 4},
        "mods": {"regen": True, "elemHunter": 0.15},
        "design": "「根据术式值与目标剩余 HP 使敌人当场死亡」= 血量低于 25%/30% 直接处决",
    },
    "684667": {   # 3费 SSS 幻/术式 —— 易伤核
        "skill": {"name": "变形攻击", "type": "barrage", "hits": 2, "sameTarget": True,
                  "power": 0.9, "panel": "hybrid", "hybrid": True, "applyTaken": 0.5},
        "ult": {"name": "「遍杀即灵体」", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.0, "panel": "hybrid", "hybrid": True, "applyTaken": 0.5},
        "mods": {"debuffBonus": 0.10, "elemHunter": 0.10},
        "design": "单次挂 50% 易伤（全队受益）；被动对带减益目标再增伤",
    },
    # ------------------------------------------------------ 漏瑚
    "607872": {   # 5费 A 影/回复 —— 随机爆发
        "skill": {"name": "怪火", "type": "barrage", "hits": 3, "power": 0.9, "panel": "magic"},
        "ult": {"name": "領域展開「蓋棺鉄囲山」", "type": "slam", "radius": 99, "power": 1.6,
                "panel": "magic", "crit": 1.4},
        "mods": {"ultStart": 20, "regen": True},
        "design": "3 段随机目标（原作就是随机点名）；领域=全体术式暴击",
    },
    "677690": {   # 5费 S 幻/回复 —— DOT 铺场
        "skill": {"name": "热线", "type": "slam", "radius": 99, "power": 1.6,
                  "panel": "magic", "dot": 0.03, "dotDur": 3},
        "ult": {"name": "极之番「陨」", "type": "slam", "radius": 99, "power": 4.0,
                "panel": "magic", "dot": 0.05, "dotDur": 4},
        "mods": {"mana_on_cast": 10},
        "design": "全体炎 DOT 铺场；必杀是最高单发倍率的全体术式",
    },
    # ------------------------------------------------------ 花御
    "607873": {   # 4费 B 幻/回复 —— 削弱者
        "skill": {"name": "诅咒的种子", "type": "slam", "radius": 99, "power": 0.6,
                  "panel": "magic", "applyWeaken": 0.33},
        "ult": {"name": "領域展開「朶頤光海」", "type": "slam", "radius": 99, "power": 1.4,
                "panel": "magic", "applyWeaken": 0.33, "dot": 0.02, "dotDur": 4},
        "mods": {"regen": True},
        "design": "不靠输出，靠「降低敌方造成的伤害 33%」+ 再生续航；域=同一削弱机制放大",
    },
    # ------------------------------------------------------ 京都校 / 其他
    "618983": {   # 1费 A 影/体术 —— 计数强化/闪避
        "skill": {"name": "全力的直拳", "type": "strike", "power": 1.2, "panel": "phys",
                  "taunt": 1.0, "guard": 0.25},
        "ult": {"name": "小高高☆回忆", "type": "strike", "power": 3.6, "panel": "phys", "crit": 1.5},
        "mods": {"dodge": 0.2, "counterMult": 0.8},
        "design": "1 费前排：嘲讽+闪避+反击；必杀必定暴击",
    },
    "703204": {   # 3费 SSS 幻/回复 —— 群体弱体乘数
        "skill": {"name": "咒灵操术（甲）", "type": "slam", "radius": 99, "power": 1.6,
                  "panel": "magic", "applyTaken": 0.10},
        "ult": {"name": "未来的世界", "type": "slam", "radius": 99, "power": 3.2,
                "panel": "magic", "applyTaken": 0.20, "dot": 0.02, "dotDur": 3},
        "mods": {"debuffBonus": 0.06},
        "design": "全体术式 + 群体易伤；被动按敌方减益数量增伤（与钉崎同源、更偏群战）",
    },
    "691924": {   # 2费 SS 行/术式 —— 冻结叠层
        "skill": {"name": "冰刃", "type": "slam", "radius": 99, "power": 1.1,
                  "panel": "magic", "dot": 0.02, "dotDur": 6},
        "ult": {"name": "冰凝咒法「直瀑」", "type": "slam", "radius": 99, "power": 2.6,
                "panel": "magic", "dot": 0.03, "dotDur": 6},
        "mods": {"regen": True, "mres": 0.10},
        "design": "冻结=DOT 长持续（6s）；反转术式做成自愈，配合魔抗当法系半坦",
    },
    "642790": {   # 1费 SS 影/术式 —— 肉盾型易伤
        "skill": {"name": "组合技", "type": "strike", "power": 0.9, "panel": "magic",
                  "applyTaken": 0.25},
        "ult": {"name": "你的对手是我", "type": "strike", "power": 1.4, "panel": "magic",
                "applyTaken": 0.5},
        "mods": {"armor": 0.15, "dodge": 0.2},
        "design": "自身减伤 40% + 体术易伤，做成「能扛又能给全队开物伤口子」的 1 费功能位",
    },
    # ------------------------------------------------------ 冥冥（本批提升为可玩）
    "722687": {   # 3费 S 夜/体术 —— 计数成长 + 追击
        "skill": {"name": "视觉共享", "type": "strike", "power": 1.4, "panel": "phys"},
        "ult": {"name": "用益潜力就是生命♡", "type": "strike", "power": 4.0, "panel": "phys",
                "applyTaken": 0.15},
        "mods": {"extra_attack": True, "counter_counter": "kuro", "max_kuro": 15, "grow_kuro": 0.02},
        "design": "「黑鸟操术」层数→攻击成长；友方行动结束追击做成 extra_attack",
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

    promoted = []
    for cid in PROMOTE:
        u = by_id.get(cid)
        if u and not u.get("playable"):
            u["playable"] = True
            promoted.append(u["name"])

    applied, missing = [], []
    for cid, spec in BATCH2.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old)
        sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"
        sk["source"] = "batch2"
        u["skill"] = sk

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch2"
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
        u["batch"] = 2
        u["design"] = spec.get("design", "")
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    playable = [u for u in units if u["playable"]]
    from collections import Counter
    rep = {
        "applied": len(applied),
        "promoted": promoted,
        "playable": len(playable),
        "costDist": dict(Counter(u["cost"] for u in playable)),
        "list": [{"name": a[0], "cost": a[1], "tier": a[2], "ultCost": a[3]} for a in applied],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[batch2] 应用 %d 枚，提升可玩 %s，可玩池 %d" % (len(applied), promoted, len(playable)))
    print("[batch2] 费用分布 %s" % dict(sorted(rep["costDist"].items())))
    for name, cost, tier, uc in applied:
        print("   %-24s %s费 %-3s 必杀槽 %d" % (name, cost, tier, uc))


if __name__ == "__main__":
    main()
