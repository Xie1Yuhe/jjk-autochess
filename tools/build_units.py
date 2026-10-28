# -*- coding: utf-8 -*-
r"""
build_units.py —— 把 wiki 角色页（tools/wiki_parsed/*.json）转化成自走棋棋子表 data/units.json

设计原则（详见 DESIGN.md「技能转化决策」）：
  1. **不编造**：skill/ultimate/passive 的 wiki 原文一律原样保留在 *_wiki 字段里，
     转化出来的机制写在 effect 字段，并标注 source（取自哪个 wiki 技能）与 confidence。
  2. **自动战斗可落地**：每个技能必须有明确触发时机（trigger），不允许"手动选目标"。
  3. **数值可比**：wiki 是 5 破口径，按分位映射到自走棋的 700–1050 生命区间。
  4. **已调优的 44 名棋子保持原数值/羁绊/机制**，只补 wiki 溯源，避免回归。

输出：
  data/units.json      全部 111 个角色条目（含异格）
  data/traits.json     沿用（由 build_data.py 合并）
  tools/units_report.json  转化统计

用法：
    python tools\build_units.py
"""
import json
import glob
import os
import re
import sys
import statistics

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSED = os.path.join(ROOT, "tools", "wiki_parsed")
OLD_UNITS = r"E:\我想做游戏\咒术自走棋\data\units.json"
OUT = os.path.join(ROOT, "data", "units.json")
REPORT = os.path.join(ROOT, "tools", "units_report.json")

# ------------------------------------------------------------ 图标哈希映射
ELEMENT = {"bb88732818": "夜", "d43ace0408": "影", "072fb86c1d": "幻",
           "43002a622a": "行", "3357d00f5e": "影", "d75cbbd570": "幻"}
ROLE = {"55cdeb7a28": "攻击", "48ee6eb3f8": "攻击", "e9bfb40a48": "弱体",
        "0c8b32b60f": "弱体", "e4a0d35b04": "弱体", "2408d7dcbd": "防御",
        "c3d8d786ec": "妨害", "859b2b13e4": "妨害", "4ca58c29d9": "强化",
        "fedb4e80b5": "回复"}
DTYPE = {"ff695fb439": "体术", "e546d6df2d": "术式", "11bccde49d": "回复"}

# ------------------------------------------------ 本体 → 第二羁绊（手工裁定）
# 依据：wiki 无阵营字段，这部分来自原作设定（东京校/京都校/特级/咒灵），
# 已实装棋子的羁绊优先沿用旧值，保证不回归。
FACTION = {
    # 东京校
    "虎杖悠仁": "东京校", "伏黑惠": "东京校", "钉崎野蔷薇": "东京校",
    "熊猫": "东京校", "狗卷棘": "东京校", "禅院真希": "东京校",
    "夜蛾正道": "东京校", "家入硝子": "东京校", "灰原雄": "东京校",
    "伊地知洁高": "东京校", "结木海斗": "东京校",
    # 京都校
    "三轮霞": "京都校", "加茂宪纪": "京都校", "东堂葵": "京都校",
    "西宫桃": "京都校", "禅院真依": "京都校", "究极机械丸": "京都校",
    "与幸吉": "京都校", "日下部笃也": "京都校", "乐岩寺嘉伸": "京都校",
    # 特级（特级术师 / 诅咒之王）
    "五条悟": "特级", "两面宿傩": "特级", "夏油杰": "特级", "乙骨忧太": "特级",
    # 咒灵
    "真人": "咒灵", "漏瑚": "咒灵", "花御": "咒灵", "陀艮": "咒灵",
    "胀相": "咒灵",
    # 其余按伤害类型分到 体术 / 术式
    "禅院直毘人": "体术", "伏黑甚尔": "体术", "米格尔": "体术",
    "漆英司": "体术", "东堂葵 ": "京都校",
    "里梅": "咒灵", "加茂宪伦": "术式", "冥冥": "术式", "猪野琢真": "术式",
    "七海建人": "术式", "吉野顺平": "术式",
}

# 特级/最强 → 费用下限（原作强度，wiki 无稀有度字段时的兜底）
COST_FLOOR = {
    "五条悟": 5, "两面宿傩": 5, "夏油杰": 4, "乙骨忧太": 5, "伏黑甚尔": 5,
    "禅院直毘人": 4, "里梅": 4, "真人": 4, "漏瑚": 4, "花御": 4, "陀艮": 4,
}

# ------------------------------------------------------ 技能关键词 → 机制
# 顺序敏感：先判定的优先
# 顺序即优先级：先判"整场/召唤/控制"，再判"群体/多段"，最后才判单体强化类。
# 注意："回复咒力" 不是治疗，所以治疗规则必须同时要求出现"生命"或"治疗"。
SKILL_RULES = [
    (["领域展开", "领域"], "domain", "领域展开 → 全场 AoE + 自身增伤 8 秒", ["领域展开", "领域"]),
    (["召唤", "式神", "玉犬", "鵺", "蛤蟆", "咒骸"], "summon", "召唤系 → 造成伤害并召唤式神分身",
     ["召唤", "式神", "玉犬", "鵺", "蛤蟆", "咒骸"]),
    (["眩晕", "无法行动", "行动不能"], "stun", "控制 → 单体伤害 + 眩晕", ["眩晕", "无法行动"]),
    (["对敌方全体", "敌方全体"], "slam", "群体 → 以目标为圆心 1 格 AoE", ["对敌方全体", "敌方全体"]),
    (["3连击", "三连击", "3次", "连击"], "barrage", "多段 → 对随机敌人打 3 段", ["3连击", "连击"]),
    (["护盾", "屏障", "伤害减免"], "shield", "护盾 → 自身与相邻友军获得护盾", ["护盾", "屏障"]),
    (["持续伤害", "毒", "烧伤", "出血", "侵蚀"], "dot", "持续伤害 → 单体伤害 + 5 秒侵蚀",
     ["持续伤害", "出血", "烧伤", "侵蚀"]),
    (["直线", "贯通", "贯穿"], "beam", "直线 → 同排贯穿", ["直线", "贯通", "贯穿"]),
    (["治疗", "回复生命", "回复自身生命", "回复全体生命"], "heal", "治疗 → 治疗生命最低的友军",
     ["治疗", "回复生命"]),
    (["赋予自身", "自身术式提升", "自身体术提升", "自身造成伤害提升"], "buff", "自我强化 → 全队攻击提升 6 秒",
     ["赋予自身", "自身"]),
    (["降低", "易伤", "弱体"], "drain", "削弱 → 伤害 + 抽走目标咒力", ["降低", "易伤", "弱体"]),
    (["选定敌人", "对敌方单体"], "strike", "单体 → 对当前目标高倍率一击", ["选定敌人"]),
]
DEFAULT_SKILL = ("strike", "单体 → 对当前目标高倍率一击")

# ------------------------------------------------------ 被动关键词 → 机制
PASSIVE_RULES = [
    (["回合开始", "波次开始", "Wave开始时", "wave开始时", "战斗开始时"],
     ["咒力", "回复咒力"], "mana_on_cast", "开场/回合回咒力 → 施法后额外回咒力"),
    (["击杀", "击败时", "击败敌人"], [], "lifesteal", "击杀收益 → 造成伤害时吸血"),
    (["暴击", "黑闪"], [], "bf", "暴击/黑闪 → 概率双倍伤害"),
    (["回避", "闪避", "回避率"], [], "dodge", "回避 → 概率完全闪避"),
    (["挑衅"], [], "taunt", "挑衅 → 提高被选取权重并减伤"),
    (["持续伤害", "侵蚀", "毒", "出血"], [], "erode", "侵蚀 → 普攻附带持续伤害"),
    (["赋予全体队友", "全体队友", "友方全体", "我方全体", "赋予全体"], [], "aura_power", "团队增益 → 全队攻击提升"),
    (["攻击速度", "行动速度", "攻速"], [], "aura_haste", "疾速 → 全队攻速提升"),
    (["回复自身", "HP回复", "回复生命", "治疗"], [], "regen_aura", "回复 → 每秒回复最大生命"),
    (["降低", "削减", "烧掉", "吸取"], ["咒力"], "mana_steal", "削咒 → 普攻烧对手咒力"),
]
DEFAULT_PASSIVE = ("erode", "侵蚀 → 普攻附带持续伤害")

PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def num(s):
    try:
        return int(float(str(s).replace(",", "")))
    except Exception:
        return 0


def max_pct(text):
    vals = [float(x) for x in PCT_RE.findall(text or "")]
    return max(vals) if vals else 0.0


def resolve(rec, key, table):
    return next((table[h] for h in rec["iconHashes"].get(key, []) if h in table), None)


def classify_skill(text):
    for rule in SKILL_RULES:
        kws, typ, note = rule[0], rule[1], rule[2]
        for kw in kws:
            if kw in text:
                return typ, note, kw
    # 兜底：文本里出现"治疗/回复生命"才算治疗，否则默认单体
    if ("治疗" in text) or ("回复" in text and "生命" in text):
        return "heal", "治疗 → 治疗生命最低的友军", "治疗"
    return DEFAULT_SKILL[0], DEFAULT_SKILL[1], ""


def classify_passive(text):
    for rule in PASSIVE_RULES:
        kws, needed, typ, note = rule[0], rule[1], rule[2], rule[3]
        for kw in kws:
            if kw in text:
                if needed and not any(n in text for n in needed):
                    continue
                return typ, note, kw
    return DEFAULT_PASSIVE[0], DEFAULT_PASSIVE[1], ""


def pctile(sorted_vals, v):
    n = len(sorted_vals)
    lo = sum(1 for x in sorted_vals if x < v)
    return lo / max(1, n)


def main():
    recs = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(PARSED, "*.json"))]
    recs = [r for r in recs if r.get("isCharacter", True)]
    # 兼容旧字段名
    for r in recs:
        r.setdefault("contentId", str(r.get("content_id", "")))
        r["contentId"] = str(r["contentId"])
    old = {str(u["id"]): u for u in json.load(open(OLD_UNITS, encoding="utf-8"))}

    # 已实装棋子的第二羁绊，用于给同一本体的其它异格继承
    second_by_base = {}
    for uid, u in old.items():
        r = next((x for x in recs if x["contentId"] == uid), None)
        if not r:
            continue
        tr = u.get("traits") or []
        second = next((t for t in tr if t not in ("夜", "影", "幻", "行")), None)
        if second:
            second_by_base.setdefault(r["baseCharacter"], second)

    # 统计分位基准
    hps = sorted(num(r["stats"].get("HP")) for r in recs)
    mains = sorted(max(num(r["stats"].get("体术")), num(r["stats"].get("术式"))) for r in recs)
    ults = sorted(num(r["stats"].get("必杀值")) for r in recs)

    rows = []
    stats_report = {"total": 0, "playable": 0, "inferredCost": 0, "passiveFromWiki": 0,
                    "skillFromWiki": 0, "noPassive": 0}

    for r in recs:
        st = r["stats"]
        hp_w = num(st.get("HP"))
        me_w = num(st.get("体术"))
        te_w = num(st.get("术式"))
        ult_w = num(st.get("必杀值"))
        main_w = max(me_w, te_w)

        hp_p = pctile(hps, hp_w)
        main_p = pctile(mains, main_w)
        ult_p = pctile(ults, ult_w)
        score = 0.45 * hp_p + 0.35 * main_p + 0.20 * ult_p

        element = resolve(r, "特性", ELEMENT) or "夜"
        role = resolve(r, "属性", ROLE) or "攻击"
        dtype = resolve(r, "伤害类型", DTYPE) or "术式"

        base = r["baseCharacter"]
        second = second_by_base.get(base) or FACTION.get(base)
        if not second:
            second = "体术" if dtype == "体术" else "术式"

        # ---- 费用：分位 → 1..5，特级角色有下限 ----
        bounds = [(0.14, 1), (0.32, 2), (0.58, 3), (0.84, 4), (1.01, 5)]
        cost = next(c for b, c in bounds if score < b)
        cost = max(cost, COST_FLOOR.get(base, 1))

        # ---- 基础属性：5 破数据的线性映射 ----
        hp = int(round(690 + hp_p * 360))                       # 690 – 1050
        ad = int(round(40 + (me_w / 15095.0) * 20)) if me_w else 38   # 38 – 60
        spell = int(round(40 + (te_w / 14861.0) * 20)) if te_w else 38
        as_rate = 0.85 if dtype == "体术" else (0.75 if dtype == "回复" else 0.7)
        atk_range = 1 if (dtype == "体术" or role == "防御") else (4 if role == "强化" and spell >= 55 else 3)
        mana_max = max(90, min(140, num(st.get("最大咒力")) or 100))
        start_mana = max(20, min(70, num(st.get("初始咒力")) or 45))

        # ---- 主动技能：取 wiki 三个指挥技能里消耗最高/最靠后的一个 ----
        skills = r["skills"] or []
        sig = None
        if skills:
            spend = sorted(skills, key=lambda s: (num(s.get("cost")), skills.index(s)))
            sig = spend[-1]
        stype, snote, skw = classify_skill((sig or {}).get("desc", ""))
        power = max_pct((sig or {}).get("desc", ""))
        power = round(max(1.0, min(3.3, power / 120.0)), 2) if power else 1.6

        # ---- 必杀技 ----
        ult = (r["ultimates"] or [None])[0]
        utype, unote, _ = classify_skill((ult or {}).get("desc", ""))
        upow = max_pct((ult or {}).get("desc", ""))
        upow = round(max(1.4, min(4.0, upow / 150.0)), 2) if upow else 2.2

        # ---- 被动：取第一条有名字的 wiki 被动 ----
        pas = next((p for p in r["passives"] if p.get("name")), None)
        ptype, pnote, pkw = classify_passive((pas or {}).get("desc", ""))
        pval = max_pct((pas or {}).get("desc", ""))
        pval = round(min(0.35, max(0.02, pval / 100.0 * 0.6)), 3) if pval else 0.12

        uid = r["contentId"]
        prev = old.get(uid)

        row = {
            "id": uid,
            "name": ("[%s] %s" % (r["variant"], base)) if r["variant"] else base,
            "baseCharacter": base,
            "variant": r["variant"],
            "wikiTitle": r["wikiTitle"],
            "wikiUrl": r["wikiUrl"],
            "release": r["release"],
            "cost": cost,
            "costSource": "authored" if prev else "inferred",
            "element": element,
            "elementLabel": {"夜": "夜行", "影": "影袭", "幻": "幻术", "行": "行咒"}[element],
            "role": role,
            "dmg": dtype,
            "traits": [element, second],
            "hp": hp, "ad": ad, "spell": spell, "as": as_rate, "range": atk_range,
            "mana": mana_max, "start_mana": start_mana,
            # ---- 转化后的机制 ----
            "skill": {
                "name": (sig or {}).get("name") or "咒力冲击",
                "type": stype,
                "power": power,
                "trigger": "mana_full",
                "effect": snote,
                "desc": snote,
                "source": (sig or {}).get("name", ""),
                "matched": skw,
                "confidence": ("missing" if not sig else ("high" if skw else "low")),
                "wikiDesc": (sig or {}).get("desc", ""),
            },
            "ultimate": {
                "name": (ult or {}).get("name") or "",
                "type": utype,
                "power": upow,
                "trigger": "star2_after_cast" if cost >= 4 else "flavor",
                "effect": unote,
                "desc": unote,
                "wikiDesc": (ult or {}).get("desc", ""),
            },
            "passive": {
                "name": (pas or {}).get("name") or "",
                "type": ptype,
                "value": pval,
                "effect": pnote,
                "desc": ("%s · %s" % ((pas or {}).get("name", ""), pnote)).strip(" ·")
                        if pas else "（wiki 未收录被动，机制待补）",
                "matched": pkw,
                "confidence": ("missing" if not pas else ("high" if pkw else "low")),
                "wikiDesc": (pas or {}).get("desc", ""),
            },
            "allSkills": [{"name": s["name"], "cost": s["cost"], "desc": s["desc"]} for s in skills],
            "allPassives": [{"name": s["name"], "desc": s["desc"]} for s in r["passives"] if s.get("name")],
            "wikiStats": st,
            "wikiComment": r.get("comment", ""),
            "playable": uid in old,
        }

        # ---- 已实装棋子：机制与数值沿用旧版（避免回归），只补 wiki 溯源 ----
        if prev:
            for k in ("cost", "hp", "ad", "spell", "as", "range", "mana", "start_mana"):
                row[k] = prev[k]
            row["traits"] = list(prev["traits"])
            row["skill"] = dict(prev["skill"])
            row["skill"].update({
                "trigger": "mana_full",
                "wikiDesc": (sig or {}).get("desc", ""),
                "source": (sig or {}).get("name", ""),
                "confidence": "authored",
            })
            row["passive"] = dict(prev["passive"])
            row["passive"].update({
                "wikiDesc": (pas or {}).get("desc", ""),
                "confidence": "authored",
            })
            stats_report["playable"] += 1
        else:
            stats_report["inferredCost"] += 1

        if not pas:
            stats_report["noPassive"] += 1
        if sig and sig.get("desc"):
            stats_report["skillFromWiki"] += 1
        stats_report["total"] += 1
        rows.append(row)

    rows.sort(key=lambda x: (x["cost"], x["baseCharacter"], x["variant"]))
    # 保持字段顺序：把 id/name 放前面更易读
    ordered = []
    for x in rows:
        keys = ["id", "name", "baseCharacter", "variant", "wikiTitle", "wikiUrl", "release",
                "cost", "costSource", "element", "elementLabel", "role", "dmg", "traits",
                "hp", "ad", "spell", "as", "range", "mana", "start_mana",
                "skill", "ultimate", "passive", "allSkills", "allPassives",
                "wikiStats", "wikiComment", "playable"]
        ordered.append({k: x[k] for k in keys})
    json.dump(ordered, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    stats_report["altFormGroups"] = len({x["baseCharacter"] for x in rows}) and \
        sum(1 for b in {x["baseCharacter"] for x in rows}
            if sum(1 for y in rows if y["baseCharacter"] == b) > 1)
    stats_report["costDist"] = {c: sum(1 for x in rows if x["cost"] == c) for c in (1, 2, 3, 4, 5)}
    stats_report["elementDist"] = {e: sum(1 for x in rows if x["element"] == e) for e in ("夜", "影", "幻", "行")}
    stats_report["skillTypeDist"] = {}
    for x in rows:
        t = x["skill"]["type"]
        stats_report["skillTypeDist"][t] = stats_report["skillTypeDist"].get(t, 0) + 1
    stats_report["passiveTypeDist"] = {}
    for x in rows:
        t = x["passive"]["type"]
        stats_report["passiveTypeDist"][t] = stats_report["passiveTypeDist"].get(t, 0) + 1
    json.dump(stats_report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(json.dumps(stats_report, ensure_ascii=False, indent=1))
    print("\n样例（新转化的 5 个）：")
    for x in [y for y in rows if not y["playable"]][:5]:
        print("  %-22s cost%d %s/%s traits=%s" % (x["name"], x["cost"], x["element"], x["dmg"], x["traits"]))
        print("     技能[%s] %s | %s" % (x["skill"]["type"], x["skill"]["name"], x["skill"]["effect"]))
        print("     必杀 %s → %s" % (x["ultimate"]["name"], x["ultimate"]["effect"]))
        print("     被动 %s → %s" % (x["passive"]["name"] or "(无)", x["passive"]["effect"]))
    print("\n写入", OUT)


if __name__ == "__main__":
    main()
