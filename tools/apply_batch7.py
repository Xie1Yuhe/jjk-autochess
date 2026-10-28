# -*- coding: utf-8 -*-
r"""
apply_batch7.py —— 重做原有 30 张（Phase 7 之前的规则引擎产物）

这 30 张原来是由关键词匹配 + 分位插值生成的，机制可跑但没有手写签名。
本脚本给每一张手写 skill / ult / mods / design，并标 batch=0（原有重做）。

用法：
    python tools\apply_batch7.py
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
REPORT = os.path.join(ROOT, "tools", "batch7_report.json")

BATCH7 = {
    # ---------------------------------------------------- 1 费
    "614519": {   # 加茂宪纪[寄宿于血中的决心] 影/回复 —— 赤鳞跃动
        "skill": {"name": "虎爪", "type": "slam", "radius": 99, "power": 0.9, "panel": "magic"},
        "ult": {"name": "穿血", "type": "strike", "power": 6.0, "panel": "magic"},
        "mods": {"ultStart": 20},
        "design": "「赤鳞跃动」状态→技能从单体变全体；必杀是单点高倍率，一卡双形态",
    },
    "701554": {   # 漆英司[连锁纹「全开速」] 行/体术 —— 连锁计数
        "skill": {"name": "连锁纹", "type": "barrage", "hits": 6, "sameTarget": True,
                  "power": 0.45, "panel": "phys"},
        "ult": {"name": "连锁纹「全开速」", "type": "barrage", "hits": 6, "sameTarget": True,
                "power": 0.75, "panel": "phys", "crit": 1.5},
        "mods": {"counter_counter": "chain", "max_chain": 10, "grow_chain": 0.02, "mana_on_cast": 15},
        "design": "「连锁计数越高暴击率越高」→ 计数成长；6 连击是 1 费里最高的段数",
    },
    "648046": {   # 狗卷棘[夜隐咒言师] 幻/回复 —— 眩晕 + 幻属易伤
        "skill": {"name": "「崩裂吧」", "type": "stun", "power": 0.5, "panel": "magic",
                  "stun": 1.5, "applyTaken": 0.40},
        "ult": {"name": "「破裂吧」", "type": "slam", "radius": 99, "power": 2.5,
                "panel": "magic", "applyTaken": 0.40},
        "mods": {"regen": True},
        "design": "咒言的「崩裂」→ 眩晕 + 40% 易伤；必杀把单体咒言扩散到全场",
    },
    "607839": {   # 禅院真希[越是弱小越是聚集] 影/体术 —— 全体体术
        "skill": {"name": "回旋斩", "type": "slam", "radius": 99, "power": 1.3, "panel": "phys"},
        "ult": {"name": "连续旋转斩", "type": "slam", "radius": 99, "power": 2.4, "panel": "phys"},
        "mods": {"armor": 0.05, "regen": True},
        "design": "「0 消耗 + 全体体术」→ 低频但稳定的群体输出；天与咒缚给常驻韧性",
    },
    "617492": {   # 究极机械丸[刀源解放] 行/术式 —— 破韧复合
        "skill": {"name": "推力加算", "type": "strike", "power": 1.1, "panel": "hybrid",
                  "hybrid": True, "armNext": 0.5},
        "ult": {"name": "「绝技抉剔」&「大祓砲」", "type": "strike", "power": 6.0,
                "panel": "hybrid", "hybrid": True},
        "mods": {},
        "design": "「break 伤害量提升」→ 破韧（下一次技能 +50%）；复合伤害对应原作的体术+术式",
    },
    "694133": {   # 西宫桃[付丧操术] 幻/回复 —— 群体易伤 + 闪避
        "skill": {"name": "风薙", "type": "slam", "radius": 99, "power": 0.8,
                  "panel": "magic", "applyTaken": 0.25},
        "ult": {"name": "付丧操术「镰异断」", "type": "slam", "radius": 99, "power": 2.2, "panel": "magic"},
        "mods": {"dodge": 0.15},
        "design": "「赋予幻特性受到伤害提升」→ 群体易伤；「回避状态」→ 15% 闪避",
    },
    # ---------------------------------------------------- 2 费
    "606636": {   # 吉野顺平[幼鱼和逆罚] 行/回复 —— 毒 DOT
        "skill": {"name": "触手突刺", "type": "dot", "power": 1.8, "panel": "magic",
                  "dot": 0.03, "dotDur": 4, "applyTaken": 0.20},
        "ult": {"name": "不要搞错生命的价值啊", "type": "dot", "power": 4.0, "panel": "magic",
                "dot": 0.04, "dotDur": 4},
        "mods": {"debuffBonus": 0.08},
        "design": "「毒持续伤害 + 受到伤害提升」→ DOT + 易伤；被动按队伍增益数量增伤压成按减益增伤",
    },
    "661933": {   # 家入硝子[咻咻] 夜/体术 —— 治疗 + 隐身
        "skill": {"name": "手术刀投掷", "type": "heal"},
        "ult": {"name": "咻的一下搞定", "type": "heal"},
        "mods": {"healAlly": {"cost": 15, "pct": 0.12, "maxHpPct": 0.6, "interval": 4}, "dodge": 0.15},
        "design": "「给夜特性队友加体术术式」压成治疗 + 闪避；「隐密」= 15% 闪避",
    },
    "724611": {   # 日下部笃也[薄暮的冷光] 幻/体术 —— 简易领域反击
        "skill": {"name": "斩崩", "type": "slam", "radius": 99, "power": 1.5,
                  "panel": "phys", "applyTaken": 0.15},
        "ult": {"name": "乱击一闪", "type": "slam", "radius": 99, "power": 3.0,
                "panel": "phys", "applyTaken": 0.15},
        "mods": {"counterMult": 1.25, "armor": 0.10},
        "design": "「简易领域 + 反击」→ 全体体术 + 1.25 倍反击；第二张日下部（与「化解锐刃」分工：这张偏输出）",
    },
    "620332": {   # 熊猫[需要帮助吗] 幻/体术 —— 嘲讽 + 复活
        "skill": {"name": "腊肠时间", "type": "empower", "amp": 0.15, "dur": 3.0,
                  "taunt": 1.5, "guard": 0.30},
        "ult": {"name": "猩猩的秘密", "type": "strike", "power": 4.5, "panel": "phys"},
        "mods": {"reviveLeft": 1, "revivePct": 0.35},
        "design": "「腊肠指示物越多回血越多」→ 嘲讽 + 减伤维持；核转换复活保留",
    },
    "658698": {   # 猪野琢真[心无骄慢] 影/术式 —— 灵龟（闪避换降伤）
        "skill": {"name": "拳打", "type": "empower", "amp": 0.2, "dur": 4.0, "guard": 0.2},
        "ult": {"name": "来访瑞兽", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 4.5, "panel": "magic"},
        "mods": {"dodge": 0.20, "armor": 0.10},
        "design": "「灵龟状态：闪避 +20% 但造成伤害 -30%」→ 闪避 + 减伤，不自带降伤（自走棋里降伤会毁掉他的输出定位）",
    },
    "640904": {   # 结木海斗[心怀意志] 行/术式 —— 眩晕 + 削弱
        "skill": {"name": "斜劈斩", "type": "stun", "power": 1.35, "panel": "magic",
                  "stun": 1.2, "applyWeaken": 0.27},
        "ult": {"name": "结祈转掌", "type": "strike", "power": 5.0, "panel": "hybrid", "hybrid": True},
        "mods": {"aura_power": 0.08},
        "design": "「造成伤害降低 27.1% + 眩晕」→ 眩晕 + 削弱；必杀是复合伤害",
    },
    "615301": {   # 钉崎野蔷薇[相性极差] 幻/回复 —— 钉子计数 + 必黑闪
        "skill": {"name": "刍灵咒法「簪」", "type": "strike", "power": 1.9,
                  "panel": "hybrid", "hybrid": True, "armNext": 1.0},
        "ult": {"name": "锐利的一击", "type": "strike", "power": 6.9,
                "panel": "hybrid", "hybrid": True, "crit": 1.3},
        "mods": {"counter_counter": "nail", "max_nail": 11, "grow_nail": 0.02},
        "design": "「钉子指示物越多自身增伤越高（最高 942%）」→ 计数成长；必杀必定黑闪（crit 1.3）",
    },
    "671525": {   # 陀艮[无尽的式神] 行/回复 —— 领域型半坦
        "skill": {"name": "踢飞", "type": "slam", "radius": 99, "power": 1.4,
                  "panel": "magic", "applyTaken": 0.10},
        "ult": {"name": "领域展开「荡蕴平线」", "type": "slam", "radius": 99, "power": 1.8,
                "panel": "magic", "applyTaken": 0.10},
        "mods": {"armor": 0.15, "mres": 0.15, "ultStart": 20},
        "design": "「领域期间减伤 35% + 术式 +40%」→ 护甲魔抗各 15% + 开场必杀值",
    },
    # ---------------------------------------------------- 3 费
    "607978": {   # 乙骨忧太[把力量借给我] 幻/术式 —— 复合 4 段
        "skill": {"name": "配合我 里香", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 0.9, "panel": "hybrid", "hybrid": True},
        "ult": {"name": "纯爱哒哟", "type": "slam", "radius": 99, "power": 4.0, "panel": "magic"},
        "mods": {"manaOnCrit": 10, "bf": 0.10},
        "design": "「体术+术式混合 4 段」→ 复合 4 连击；必杀 1999% 全体术式压成 4.0",
    },
    "680362": {   # 乙骨忧太[诅咒的女王] 影/术式 —— 反击 + 里香
        "skill": {"name": "袈裟斩", "type": "empower", "amp": 0.8, "dur": 4.0},
        "ult": {"name": "特级过咒怨灵 祈本里香", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 2.4, "panel": "magic"},
        "mods": {"counterMult": 1.2},
        "design": "「祈本里香状态：术式 +80%」→ 自我增伤；被动反击（里香护主）",
    },
    "698359": {   # 夜蛾正道[枢要守望者] 影/术式 —— 增益 + 追击
        "skill": {"name": "指导", "type": "empower", "amp": 0.65, "dur": 3.0},
        "ult": {"name": "咒骸大作战", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 0.9, "panel": "magic", "applyWeaken": 0.15},
        "mods": {"extra_attack": True, "aura_power": 0.08},
        "design": "「友方行动结束时追打」→ 常驻追击；「指导」= 自我增伤",
    },
    "633431": {   # 禅院真希[大刀乱舞] 夜/体术 —— 零消耗暴击
        "skill": {"name": "连击", "type": "strike", "power": 1.8, "panel": "phys", "crit": 1.45},
        "ult": {"name": "怒涛乱舞", "type": "strike", "power": 9.6, "panel": "phys"},
        "mods": {"mana_on_cast": 12},
        "design": "「0 消耗 + 暴击率 +100%」→ 施法后大量回咒，靠频率取胜；技能必定暴击",
    },
    "640934": {   # 虎杖悠仁[zone] 行/体术 —— 追加行动
        "skill": {"name": "拳打", "type": "barrage", "hits": 2, "sameTarget": True,
                  "power": 1.35, "panel": "phys"},
        "ult": {"name": "「黑闪」", "type": "strike", "power": 9.0, "panel": "phys", "crit": 1.33},
        "mods": {"bf": 0.25, "extra_attack": True},
        "design": "「zone 状态：黑闪率 +50% + 追加行动」→ 高黑闪 + 常驻追击",
    },
    "707237": {   # 钉崎野蔷薇[出片常夏] 影/回复 —— 群体术式易伤
        "skill": {"name": "刍灵咒法【共鸣】", "type": "slam", "radius": 99, "power": 1.5,
                  "panel": "magic", "applyTaken": 0.30},
        "ult": {"name": "刍灵咒法【簪】", "type": "slam", "radius": 99, "power": 2.0,
                "panel": "magic", "applyTaken": 0.30},
        "mods": {"ultStart": 20},
        "design": "「全体 + 钉子计数 + 术式易伤 30%」→ 群体易伤核，第三张钉崎",
    },
    # ---------------------------------------------------- 4 费
    "622642": {   # 五条悟[苍之最强] 行/术式 —— 无敌 + 全体
        "skill": {"name": "无限的收束", "type": "strike", "power": 2.2,
                  "panel": "magic", "applyWeaken": 0.30},
        "ult": {"name": "术式顺转 功率最大「苍」", "type": "slam", "radius": 99,
                "power": 3.0, "panel": "magic", "crit": 1.4},
        "mods": {"invulnStart": 2.0},
        "design": "「攻击无效化 2 回合」→ 开场 2 秒无敌；必杀是 5 连击全体术式（压成单段 3.0）",
    },
    "676882": {   # 伏黑惠[兔之搅乱] 幻/术式 —— 召唤 + 高易伤
        "skill": {"name": "除灵斩", "type": "summon"},
        "ult": {"name": "式神连续召唤", "type": "strike", "power": 5.0,
                "panel": "magic", "applyTaken": 0.50},
        "mods": {"dodge": 0.15},
        "design": "「召唤脱兔分担 50% 伤害」→ summon + 15% 闪避；必杀 50% 易伤",
    },
    "639616": {   # 伏黑惠[成对的牵绊] 夜/术式 —— 召唤 + 夜属易伤
        "skill": {"name": "回转踢", "type": "summon"},
        "ult": {"name": "「玉犬」双击", "type": "barrage", "hits": 2, "sameTarget": True,
                "power": 2.5, "panel": "magic", "applyTaken": 0.20},
        "mods": {"mana_on_cast": 10},
        "design": "第二张召唤型伏黑；「玉犬在场时咒耗降低」→ 施法回咒",
    },
    "707238": {   # 伏黑惠[清凉海风] 夜/回复 —— 全体术式主 C
        "skill": {"name": "「满象」", "type": "slam", "radius": 99, "power": 1.6,
                  "panel": "magic", "applyTaken": 0.30},
        "ult": {"name": "式神连携", "type": "slam", "radius": 99, "power": 3.0, "panel": "magic"},
        "mods": {"manaOnCrit": 10},
        "design": "「夜特性受到伤害提升 30%」+ 1500% 全体 5 连击 → 夜队主 C",
    },
    "672458": {   # 胀相[履行哥哥的责任] 夜/术式 —— 血刃状态
        "skill": {"name": "「血刃」", "type": "empower", "amp": 0.5, "dur": 6.0},
        "ult": {"name": "「穿血」", "type": "empower", "amp": 0.5, "dur": 6.0, "applyTaken": 0.3},
        "mods": {"ultStart": 20},
        "design": "「赫鳞跃动·载」= 体术术式各 +50%、造成伤害 +50% → 双重增伤状态",
    },
    "605988": {   # 虎杖悠仁[咒力闪耀黑光] 夜/体术 —— 末段必黑闪
        "skill": {"name": "拳打", "type": "barrage", "hits": 4, "sameTarget": True,
                  "power": 1.1, "panel": "phys", "lastHitBf": True, "applyTaken": 0.60},
        "ult": {"name": "「黒閃」", "type": "barrage", "hits": 3, "sameTarget": True,
                "power": 4.0, "panel": "phys", "lastHitBf": True},
        "mods": {"bf": 0.15},
        "design": "「第 4 段攻击黑闪」→ lastHitBf；「暴击抵抗降低 60%」→ 60% 易伤",
    },
    # ---------------------------------------------------- 5 费
    "623845": {   # 伏黑甚尔[术师杀手] 幻/体术 —— 驱散 + 全体处决
        "skill": {"name": "除灵斩", "type": "strike", "power": 2.0, "panel": "phys"},
        "ult": {"name": "全都不是问题", "type": "slam", "radius": 99, "power": 8.0, "panel": "phys"},
        "mods": {"armor": 0.15, "dodge": 0.20, "regen": True},
        "design": "「解除敌人攻击无效化与强化」→ 目前引擎无驱散，用高穿透倍率替代；天与暴君三件套保留",
    },
    "675539": {   # 禅院直毘人[唯快不破] 影/术式 —— 反击 + 破韧叠乘
        "skill": {"name": "最快的一击", "type": "strike", "power": 2.6,
                  "panel": "magic", "armNext": 1.5},
        "ult": {"name": "最快的术师", "type": "strike", "power": 7.0,
                "panel": "magic", "armNext": 3.0},
        "mods": {"counterMult": 1.5},
        "design": "「投射咒法：破韧伤害随层数最高 150%」→ 破韧叠乘（armNext 1.5/3.0）+ 高倍反击",
    },
    "652057": {   # 禅院真希[破晓启程] 影/体术 —— 4 连击末必暴
        "skill": {"name": "全力一刀", "type": "strike", "power": 6.0, "panel": "phys"},
        "ult": {"name": "刹那连击", "type": "barrage", "hits": 4, "sameTarget": True,
                "power": 2.6, "panel": "phys", "crit": 1.4},
        "mods": {"ultStart": 20},
        "design": "「第 4 击必定暴击」→ crit 1.4；5 费里少见的纯单体爆发（觉醒后的真希）",
    },
    "683413": {   # 虎杖悠仁[最大咒力输出] 幻/体术 —— 双模式黑闪
        "skill": {"name": "万字踢", "type": "strike", "power": 7.0, "panel": "phys", "armNext": 0.2},
        "ult": {"name": "黑闪", "type": "strike", "power": 10.5,
                "panel": "phys", "crit": 2.0, "sure": True},
        "mods": {"bf": 0.18, "manaOnCrit": 10},
        "design": "「轻快/猛攻双模式」→ 用破韧 + 高黑闪率表达；必杀必定黑闪且倍率随咒力成长（压成 10.5 固定）",
    },
}

TFT_COST = None


def num(s):
    try:
        return int(float(str(s).replace(",", "")))
    except Exception:
        return 0


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_id = {u["id"]: u for u in units}
    applied, missing = [], []

    for cid, spec in BATCH7.items():
        u = by_id.get(cid)
        if not u:
            missing.append(cid)
            continue
        old = dict(u.get("skill") or {})
        sk = dict(old)
        sk.update(spec["skill"])
        sk["wikiDesc"] = old.get("wikiDesc", "")
        sk["confidence"] = "authored"
        sk["source"] = "batch7"
        u["skill"] = sk

        ult = dict(spec["ult"])
        ult["combat"] = True
        ult["source"] = "batch7"
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
        u["batch"] = 0          # 0 = 原有 30 张（已重做）
        u["design"] = spec.get("design", "")
        applied.append((u["name"], u["cost"]))

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    left = [u["name"] for u in units if "batch" not in u or u.get("batch") is None]
    json.dump({"applied": len(applied), "remaining": left},
              open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[batch7] 重做 %d 张，仍有 %d 张无批次标记" % (len(applied), len(left)))
    if left:
        print("    ", "、".join(left[:10]))
    print("[batch7] 全部 111 张现在都有手写签名" if not left else "[batch7] 仍有遗留")


if __name__ == "__main__":
    main()
