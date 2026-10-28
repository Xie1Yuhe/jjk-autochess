# -*- coding: utf-8 -*-
r"""
gen_roster.py —— 生成 ROSTER.md（全量角色/棋子名单 + 技能设计总表）

用途：给后续「新增角色」和「调整老角色」当索引。
数据源就是 data/units.json，所以 **跑一次就等于和代码同步**，不会出现文档和实现对不上。

用法：
    python tools\gen_roster.py
"""
import json
import os
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
LINKS = os.path.join(ROOT, "data", "links.json")
OUT = os.path.join(ROOT, "ROSTER.md")

SKILL_LABEL = {
    "strike": "单体", "slam": "范围/全体", "barrage": "多段连击", "beam": "直线贯穿",
    "dot": "持续伤害", "drain": "削咒", "stun": "眩晕", "heal": "治疗",
    "shield": "护盾", "buff": "全队增益", "empower": "自我增伤", "summon": "召唤",
    "domain": "领域", "taunt": "嘲讽",
}


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    links = json.load(open(LINKS, encoding="utf-8"))
    playable = [u for u in units if u.get("playable")]

    by_base = defaultdict(list)
    for u in units:
        by_base[u["baseCharacter"]].append(u)
    for k in by_base:
        by_base[k].sort(key=lambda x: (x["cost"], x.get("variant") or ""))

    L = []
    A = L.append
    A("# ROSTER.md —— 全量棋子名单与技能设计总表")
    A("")
    A("> 本文档由 `python tools\\gen_roster.py` 从 `data/units.json` 自动生成，**改数据后重跑即可同步**。")
    A("> 用途：新增角色、调整老角色时先查这里，避免机制重复或数值打架。")
    A("")
    A("## 0. 总览")
    A("")
    A("| 项目 | 数值 |")
    A("|---|---|")
    A("| 棋子总数 | **%d** |" % len(units))
    A("| 已实装（可进商店） | **%d / %d** |" % (len(playable), len(units)))
    A("| 本体角色 | **%d** |" % len(by_base))
    A("| 异格形态（同角色多张卡） | **%d 组 / %d 张** |"
      % (sum(1 for v in by_base.values() if len(v) > 1),
         sum(len(v) for v in by_base.values() if len(v) > 1)))
    A("| 有必杀技 | **%d** |" % sum(1 for u in units if (u.get("ult") or {}).get("combat")))
    A("| 异格联动 | **%d 组** |" % len(links))
    A("")

    cost_d = Counter(u["cost"] for u in units)
    A("### 费用分布")
    A("")
    A("| 费用 | 1 | 2 | 3 | 4 | 5 |")
    A("|---|---|---|---|---|---|")
    A("| 数量 | %s |" % " | ".join(str(cost_d.get(c, 0)) for c in range(1, 6)))
    A("")
    rar_d = Counter(u["rarity"] for u in units)
    A("### 品质分布（来自官方强度榜标注）")
    A("")
    A("| 品质 | SSR | SR | R |")
    A("|---|---|---|---|")
    A("| 数量 | %d | %d | %d |" % (rar_d.get("SSR", 0), rar_d.get("SR", 0), rar_d.get("R", 0)))
    A("")
    tier_d = Counter(u.get("tier") for u in units)
    A("### 强度档位分布（官方排行榜）")
    A("")
    A("| 档位 | SSS | SS | S | A | B | C |")
    A("|---|---|---|---|---|---|---|")
    A("| 数量 | %s |" % " | ".join(str(tier_d.get(k, 0)) for k in ("SSS", "SS", "S", "A", "B", "C")))
    A("")
    A("---")
    A("")
    A("## 1. 异格联动总表")
    A("")
    A("| 联动 | 成员 | 机制 |")
    A("|---|---|---|")
    for lk in links:
        A("| **%s** | %s | %s |" % (lk["name"], " + ".join(lk.get("memberNames", [])), lk.get("mechanic", "")))
    A("")
    A("---")
    A("")
    A("## 2. 全量棋子（按本体角色分组）")
    A("")
    A("字段说明：**费用 / 品质 / 档位 / 特性 / 伤害类型 / 招牌技（机制）/ 必杀 / 设计要点**")
    A("")

    for base in sorted(by_base.keys(), key=lambda b: (by_base[b][0]["cost"], b)):
        forms = by_base[base]
        A("### %s（%d 张）" % (base, len(forms)))
        A("")
        A("| 形态 | 费用 | 品质 | 档位 | 特性 | 伤害 | 招牌技 | 必杀 | 设计要点 | 批次 |")
        A("|---|---|---|---|---|---|---|---|---|---|")
        for u in forms:
            sk = u.get("skill") or {}
            ul = u.get("ult") or {}
            sk_txt = "%s（%s）" % (sk.get("name", "-"), SKILL_LABEL.get(sk.get("type"), sk.get("type", "-")))
            ul_txt = "%s" % (ul.get("name", "-") if ul.get("combat") else "—")
            design = u.get("design") or ""
            if not design:
                sk2 = u.get("skill") or {}
                pv = u.get("passive") or {}
                design = "规则引擎转化：%s ×%s；被动 %s" % (
                    SKILL_LABEL.get(sk2.get("type"), sk2.get("type") or "-"),
                    sk2.get("power"), pv.get("name") or "无")
            design = design.replace("|", "/")
            if len(design) > 60:
                design = design[:58] + "…"
            A("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                u.get("variant") or "（本体）", u["cost"], u.get("rarity", "-"), u.get("tier", "-"),
                u["element"], u["dmg"], sk_txt, ul_txt, design,
                ("批次%d" % u["batch"]) if u.get("batch") else "原有"))
        A("")

    A("---")
    A("")
    A("## 3. 按费用与档位查表（方便配阵容）")
    A("")
    for c in range(1, 6):
        group = [u for u in units if u["cost"] == c]
        A("### %d 费（%d 张）" % (c, len(group)))
        A("")
        A("| 棋子 | 档位 | 特性 | 伤害 | 必杀 |")
        A("|---|---|---|---|---|")
        for u in sorted(group, key=lambda x: (x.get("tier") or "Z", x["name"])):
            ul = u.get("ult") or {}
            A("| %s | %s | %s | %s | %s |" % (
                u["name"], u.get("tier", "-"), u["element"], u["dmg"],
                ul.get("name", "-") if ul.get("combat") else "—"))
        A("")

    A("---")
    A("")
    A("## 3.5 待复核清单（原有 30 张）")
    A("")
    A("这 %d 张来自 Phase 7 **之前**的规则引擎转化（关键词匹配 + 分位插值），" % len([u for u in units if not u.get("batch")]))
    A("机制可跑、数值合理，但**没有经过手写的机制签名复核**。建议后续逐张重做，优先级按档位从高到低。")
    A("")
    legacy = sorted([u for u in units if not u.get("batch")], key=lambda x: x["cost"])
    A("| 棋子 | 费用 | 档位 | 招牌技 | 现有被动 |")
    A("|---|---|---|---|---|")
    for u in legacy:
        sk = u.get("skill") or {}
        pv = u.get("passive") or {}
        A("| %s | %d | %s | %s（%s） | %s |" % (
            u["name"], u["cost"], u.get("tier", "-"),
            sk.get("name", "-"), SKILL_LABEL.get(sk.get("type"), sk.get("type", "-")),
            pv.get("name") or "无"))
    A("")
    A("---")
    A("")
    A("## 4. 未实装清单")
    A("")
    miss = [u for u in units if not u.get("playable")]
    if not miss:
        A("**无。111 张全部可进商店。**")
    else:
        A("| 棋子 | 费用 | 原因 |")
        A("|---|---|---|")
        for u in miss:
            A("| %s | %d | 待设计 |" % (u["name"], u["cost"]))
    A("")
    A("---")
    A("")
    A("## 5. 怎么新增 / 调整角色")
    A("")
    A("### 新增一个角色（完整流程）")
    A("")
    A("```powershell")
    A("python tools\\fetch_wiki.py       # 1. 从 gamekee 抓角色页（增量缓存）")
    A("python tools\\parse_tierlist.py   # 2. 刷新强度榜（品质/档位来源）")
    A("python tools\\build_units.py      # 3. 规则引擎转成棋子基础数据")
    A("python tools\\apply_rarity.py     # 4. 费用 + 可玩卡池")
    A("python tools\\apply_tierlist.py   # 5. 官方品质 + 强度档位")
    A("python tools\\apply_batchN.py     # 6. 手写这张卡的 skill / ult / mods / design")
    A("python tools\\build_data.py       # 7. 打包成 data/game-data.js")
    A("python tools\\prepare_assets.py   # 8. 头像/卡面（缺卡面自动合成）")
    A("python tools\\apply_cost_curve.py # 9. 按档位+人气重排费用")
    A("python tools\\gen_text.py        # 10. **从数据生成技能/必杀/被动描述**")
    A("python tools\\gen_roster.py       # 11. 重新生成本文档")
    A("python tools\\gen_docs.py         # 12. 重新生成 DESIGN.md")
    A("```")
    A("")
    A("### 调整一个老角色")
    A("")
    A("| 想改什么 | 改哪里 |")
    A("|---|---|")
    A("| 技能机制/倍率 | 对应 `tools/apply_batchN.py` 的 `BATCHn` 字典，改完重跑该脚本 |")
    A("| 被动/领域/退场 | 同上，改 `mods` 字段 |")
    A("| 必杀槽需求 | 同上，加 `\"ultCost\": N` 覆盖（默认按必杀值换算） |")
    A("| 品质 | `tools/apply_tierlist.py` 的 `RARITY_BY_CARD` |")
    A("| 费用 | `tools/apply_rarity.py` 的 `TARGET_DIST` / `COST_BASE` |")
    A("| 属性克制 | `data/elements.json`（纯数据，不用改代码） |")
    A("| 异格联动 | `data/links.json` + `battle.js` 的 `_applyLinkMods` |")
    A("")
    A("### 改完必须跑")
    A("")
    A("```powershell")
    A("node tools\\selftest.mjs        # 逻辑自测")
    A("node tools\\balance.mjs         # 平衡（目标 简单≈85% / 普通≈50% / 困难≈25%）")
    A("```")
    A("")
    A("> `battle.js` 里的 8 类原语（必杀槽 / 计数器 / 无敌 / 复活 / 退场 / 反击 /")
    A("> 复合伤害 / 自损）与技能修饰器（stun / dot / crit / applyTaken / applyWeaken /")
    A("> taunt / armNext / execute / debuffBonus / lastHitBf / sure / hybrid / radius / hits）")
    A("> 都是**数据驱动**的，加新卡通常只写数据、不改引擎。")
    A("")

    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("[roster] %s  %d 行" % (OUT, len(L)))
    print("[roster] 棋子 %d（本体 %d，异格组 %d），全部可玩 %s"
          % (len(units), len(by_base),
             sum(1 for v in by_base.values() if len(v) > 1),
             "是" if len(playable) == len(units) else "否"))


if __name__ == "__main__":
    main()
