# -*- coding: utf-8 -*-
r"""
apply_batch1.py —— 批次 1：15 枚核心棋子的完整落地

原则：品质定稀有，档位定方向，原始面板定数值，技能原文定机制。
本脚本只写**机制层**（skill / ult / mods / ultCost），面板数值仍由 apply_rarity 的
费用分位模型给出，保证相对强弱与原作一致。

设计说明见 BATCH1_SIGNATURES.md，每条 wiki 原文都在 units.json 的 skill/passive.wikiDesc 里。

用法（必须排在 apply_tierlist.py 之后）：
    python tools\apply_batch1.py
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
REPORT = os.path.join(ROOT, "tools", "batch1_report.json")

# ---------------------------------------------------------------- 15 枚
# 键：content_id；power 一律是「每段」倍率，不吃面板以外的加成
BATCH1 = {
    # ---------------------------------------------------- 虎杖悠仁
    "607988": {   # 1 费 · 宿傩的容器：三段拳 + 耐性
        "skill": {"name": "连続拳打", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.62, "panel": "phys"},
        "ult": {"name": "「逕庭拳」", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 1.75, "panel": "phys"},
        "mods": {"dotResist": 0.30},
        "design": "三段拳锁同一目标；「耐性」压成持续伤害减免 30%",
    },
    "706232": {   # 5 费 · 苍穹扣杀：黑闪计数 + 破韧 + 7 连击末段必黑闪
        "skill": {"name": "苍穹的一击", "type": "strike", "power": 3.2, "panel": "phys",
                  "armNext": 0.8},
        "ult": {"name": "夏日狂热", "type": "barrage", "hits": 7, "sameTarget": True,
                "power": 0.9, "panel": "phys", "sure": True, "lastHitBf": True},
        "mods": {"bf_count_key": "bf", "bf_count_need": 5, "bf_count_mult": 2.0},
        "design": "把原作的 18% 黑闪凹度改成受击/普攻计数，满 5 段必黑闪；破韧=下一次技能+80%",
    },
    # ---------------------------------------------------- 五条悟
    "661932": {   # 5 费 · 觉醒：唯我独尊 + 攻击无效化 + 反击
        "skill": {"name": "收束与打击", "type": "empower", "amp": 0.6, "dur": 3.5},
        "ult": {"name": "虚式「茈」", "type": "strike", "power": 6.5, "panel": "magic", "sure": True},
        "mods": {"invulnStart": 3.0, "invulnLowHp": 2.0, "counterMult": 0.8},
        "design": "开场 3s 攻击无效化；生命首次 ≤50% 再获 2s；受近战攻击反击",
    },
    "606026": {   # 4 费 · 最强：限时退场 + 全体术式
        "skill": {"name": "开始变得有趣了", "type": "empower", "amp": 1.2, "dur": 3.5},
        "ult": {"name": "術式反転「赫」", "type": "slam", "radius": 99, "power": 3.4, "panel": "magic"},
        "mods": {"retireAt": 7.0, "retireAura": 0.15},
        "design": "存活 7s 强制退场，退场时全队 +15% 术式/攻击（临终遗泽）",
    },
    "640936": {   # 5 费 · 无下限的内侧：无量空处
        "skill": {"name": "收束与打击", "type": "strike", "power": 2.6, "panel": "magic"},
        "ult": {"name": "领域展开「无量空处」", "type": "slam", "radius": 99, "power": 1.4,
                "panel": "magic", "stun": 1.5, "sure": True},
        "mods": {"retireAt": 11.0, "ultManaPenalty": {"lock": 2, "zero": True}, "ultStart": 30},
        "ultCost": 76,
        "design": "领域=全场眩晕 1.5s + 伤害，代价是 9s 后强制退场",
    },
    # ---------------------------------------------------- 两面宿傩
    "644233": {   # 4 费 · 真正的咒术：伏魔御厨子 + 反转术式
        "skill": {"name": "给我认清身份", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.55, "panel": "magic", "dot": 0.03, "dotDur": 5},
        "ult": {"name": "领域展开「伏魔御厨子」", "type": "barrage", "hits": 8, "sameTarget": True,
                "power": 0.4, "panel": "magic", "dot": 0.04, "dotDur": 5},
        "mods": {"healHitsEvery": 3, "healHitsPct": 0.08},
        "design": "裂伤用持续伤害表达；反转术式改成「每挨 3 次打回 8% 最大生命」的确定性回血",
    },
    "684163": {   # 5 费 · 火力胜负：必中必暴「开」
        "skill": {"name": "戏耍", "type": "barrage", "hits": 7, "sameTarget": True,
                  "power": 0.42, "panel": "magic", "dot": 0.02, "dotDur": 4},
        "ult": {"name": "「开」", "type": "strike", "power": 9.0, "panel": "magic",
                "crit": 2.0, "sure": True, "dot": 0.05, "dotDur": 4},
        "mods": {"immuneControl": True, "manaOnCrit": 15},
        "design": "「开」必定暴击+必中+炎DOT；诅咒之王=免疫控制+暴击回15咒力",
    },
    # ---------------------------------------------------- 夏油杰
    "607979": {   # 4 费 · 大义：易伤 + 击杀回咒
        "skill": {"name": "特级咒具「游云」", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.55, "panel": "magic", "applyTaken": 0.25},
        "ult": {"name": "极之番「旋涡」", "type": "slam", "radius": 99, "power": 2.4, "panel": "magic"},
        "mods": {"manaOnKill": 25},
        "design": "3 连击附带术式易伤；「吸收」= 击杀回 25 咒力，让他能反复开大",
    },
    "721094": {   # 5 费 · 终焉之物：全体术式 + 行易伤
        "skill": {"name": "咒灵操术（丙）", "type": "slam", "radius": 99, "power": 1.6,
                  "panel": "magic", "applyTaken": 0.15},
        "ult": {"name": "决意此途", "type": "slam", "radius": 99, "power": 4.0,
                "panel": "magic", "dot": 0.03, "dotDur": 3},
        "mods": {},
        "design": "全体 4 连击压成单段 1.6 倍；必杀挂炎 DOT；与大义形成「一个挂易伤、一个吃易伤」",
    },
    # ---------------------------------------------------- 乙骨忧太
    "699088": {   # 4 费 · 死刑执行人：复合伤害
        "skill": {"name": "连续斩", "type": "slam", "radius": 99, "power": 1.3,
                  "panel": "hybrid", "hybrid": True},
        "ult": {"name": "来吧「里香」", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.9, "panel": "hybrid", "hybrid": True},
        "mods": {"healAlly": {"cost": 15, "pct": 0.10, "maxHpPct": 0.6, "interval": 4}},
        "design": "复合伤害同时吃体术与术式；反转术式=消耗15咒力治疗残血友军10%最大生命",
    },
    # ---------------------------------------------------- 伏黑惠
    "609120": {   # 3 费 · 不完全的领域：复合 + 嵌合暗翳庭
        "skill": {"name": "除灵斩", "type": "strike", "power": 1.1,
                  "panel": "hybrid", "hybrid": True, "applyTaken": 0.2},
        "ult": {"name": "领域展开「嵌合暗翳庭」", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 1.0, "panel": "hybrid", "hybrid": True, "stun": 1.0},
        "mods": {"armor": 0.15, "mres": 0.15, "ultWhenLowMana": {"below": 15, "perSec": 40}},
        "design": "域=护甲/魔抗各15%减伤；低咒力时持续回必杀值（对应「马上就超越你」）",
    },
    # ---------------------------------------------------- 钉崎野蔷薇
    "639110": {   # 2 费 · 钉进去：共鸣 + 弱体特攻
        "skill": {"name": "钉锤殴打", "type": "barrage", "hits": 2, "sameTarget": True,
                  "power": 0.95, "panel": "hybrid", "hybrid": True,
                  "debuffBonus": 0.08, "debuffMax": 5},
        "ult": {"name": "芻霊呪法「共鸣」", "type": "strike", "power": 4.2, "panel": "magic",
                "sure": True, "debuffBonus": 0.25, "debuffMax": 5},
        "mods": {},
        "design": "「弱体特攻」= 目标每有 1 个减益，伤害 +8%（上限 5 层）；必杀 +25%/层",
    },
    # ---------------------------------------------------- 狗卷棘
    "637822": {   # 3 费 · 「破碎吧」：咒言易伤 + 必杀反噬
        "skill": {"name": "「粉碎吧」", "type": "strike", "power": 2.2,
                  "panel": "magic", "applyTaken": 0.27},
        "ult": {"name": "「破碎吧」", "type": "slam", "radius": 99, "power": 0.8,
                "panel": "magic", "applyTaken": 0.4},
        "mods": {"selfDamageOnUlt": 0.12},
        "design": "咒言伤喉咙 = 每次必杀自损 12% 最大生命（已确认口径）",
    },
    # ---------------------------------------------------- 三轮霞
    "646160": {   # 1 费 · 疾走：反击 + 拔刀计数
        "skill": {"name": "拔刀斩", "type": "barrage", "hits": 3, "sameTarget": True,
                  "power": 0.5, "panel": "phys"},
        "ult": {"name": "全力三段斩", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 1.1, "panel": "phys", "taunt": 1.5, "guard": 0.3},
        "mods": {"counterMult": 1.2, "counter_counter": "bato", "max_bato": 8, "grow_bato": 0.03},
        "design": "受近战攻击反击1.2倍攻击且拔刀计数+1；每层拔刀计数+3%攻击（上限8层）",
    },
    # ---------------------------------------------------- 熊猫
    "606014": {   # 2 费 · 别小看人偶：嘲讽 + 复活
        "skill": {"name": "熊猫直拳", "type": "taunt", "taunt": 2.0, "guard": 0.5},
        "ult": {"name": "激震掌", "type": "strike", "power": 3.6, "panel": "phys"},
        "mods": {"reviveLeft": 1, "revivePct": 0.4},
        "design": "嘲讽 2s + 减伤 50%；首次阵亡以 40% 生命复活（核转换）",
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

    for cid, spec in BATCH1.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        # 保留 wiki 原文，只覆盖机制层
        old_skill = dict(u.get("skill") or {})
        new_skill = dict(old_skill)
        new_skill.update(spec["skill"])
        new_skill["wikiDesc"] = old_skill.get("wikiDesc", "")
        new_skill["confidence"] = "authored"
        new_skill["source"] = "batch1"
        u["skill"] = new_skill

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch1"
        # 必杀值 → 必杀槽上限：必杀值越高越难攒
        # 必杀值实测区间 973–2334，线性映射到 70–130（越高越难攒）
        bv = num((u.get("wikiStats") or {}).get("必杀值"))
        if bv > 0:
            u["ultCost"] = max(70, min(130, round(70 + (bv - 973) / (2334 - 973) * 60)))
        else:
            # 没有必杀值数据时按费用推断：便宜的卡更快放出必杀（1 费 76 … 5 费 100）
            u["ultCost"] = 70 + int(u["cost"]) * 6
        if spec.get("ultCost"):
            u["ultCost"] = int(spec["ultCost"])
            u["ultCostSource"] = "design"
        else:
            u["ultCostSource"] = "wiki" if bv else "default"
        u["ult"] = ult
        u["mods"] = spec.get("mods") or {}
        u["batch"] = 1
        u["design"] = spec.get("design", "")
        applied.append((u["name"], u["cost"], u.get("tier"), u["ultCost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"applied": len(applied), "missing": missing,
               "list": [{"name": a[0], "cost": a[1], "tier": a[2], "ultCost": a[3]} for a in applied]},
              open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[batch1] 应用 %d 枚，缺失 %d" % (len(applied), len(missing)))
    for name, cost, tier, uc in applied:
        print("   %-24s %s费 %-3s 必杀槽 %d" % (name, cost, tier, uc))


if __name__ == "__main__":
    main()
