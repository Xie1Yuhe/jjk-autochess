# -*- coding: utf-8 -*-
r"""
gen_docs.py —— 由数据生成 DESIGN.md 与 DEVLOG.md 的表格部分，保证文档与数据不脱节。

用法：
    python tools\gen_docs.py
"""
import json
import os
import sys
import datetime
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT_DESIGN = os.path.join(ROOT, "DESIGN.md")
OUT_DEVLOG = os.path.join(ROOT, "DEVLOG.md")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


SKILL_LABEL = {
    "strike": "单体突袭", "slam": "范围重击", "barrage": "多段连击", "beam": "直线贯穿",
    "dot": "持续侵蚀", "drain": "夺魂吸取", "stun": "咒言眩晕", "heal": "治疗回复",
    "shield": "护盾守护", "buff": "强化己方", "domain": "领域展开", "summon": "召唤式神",
}
PASSIVE_LABEL = {
    "bf": "黑闪", "dodge": "闪避", "taunt": "守护", "mana_on_cast": "咒力循环",
    "erode": "侵蚀", "mana_steal": "削咒", "lifesteal": "吸血", "slow_on_hit": "迟滞",
    "regen_aura": "再生光环", "aura_haste": "疾速光环", "aura_power": "增幅光环",
}
CONF_LABEL = {"authored": "人工调优", "high": "规则命中", "low": "**待复核**", "missing": "**待补**"}


def main():
    units = load(os.path.join(DATA, "units.json"))
    traits = load(os.path.join(DATA, "raw", "traits.json"))
    items = load(os.path.join(DATA, "raw", "items.json"))
    rep = load(os.path.join(ROOT, "tools", "units_report.json"))
    wiki = load(os.path.join(ROOT, "tools", "wiki_report.json"))
    links = load(os.path.join(DATA, "links.json"))

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    by_base = defaultdict(list)
    for u in units:
        by_base[u["baseCharacter"]].append(u)
    multi = {k: v for k, v in by_base.items() if len(v) > 1}

    L = []
    A = L.append
    A("# DESIGN.md —— 《咒术回战 幻影夜行 · 自走棋》设计文档")
    A("")
    A("> 由 `python tools/gen_docs.py` 从 `data/units.json` / `data/traits.json` 自动生成，"
      "**请勿手改表格部分**。最后生成：%s" % now)
    A("")
    A("- 玩法机制调研与差距分析见 [DESIGN_RESEARCH.md](DESIGN_RESEARCH.md)")
    A("- 数据缺口与处理方式见 [DATA_GAP.md](DATA_GAP.md)")
    A("- 网页端实现说明见 [README.md](README.md)")
    A("")
    A("---")
    A("")
    A("## 1. 经济与节奏")
    A("")
    A("| 项 | 数值 |")
    A("|---|---|")
    A("| 初始金币 / 等级 | 6 金 / 2 级 |")
    A("| 每回合基础收入 | 5 金 |")
    A("| 利息 | 每 10 金 +1，上限 5（50 金吃满） |")
    A("| 连势奖励 | 1–2 连 +1；3–4 连 +2；5 连以上 +3（胜负同档） |")
    A("| PvE 回合补贴 | +3 金 |")
    A("| 刷新商店 | 2 金 |")
    A("| 买经验 | 4 金 = 4 经验 |")
    A("| 升级经验阶梯 | 0, 2, 6, 10, 16, 26, 38, 52, 70, 92（2→9 级） |")
    A("| 出售返还 | 费用 × 1 / 3 / 9（1★ / 2★ / 3★） |")
    A("| 失败扣血 | `2 + 敌方存活数 × 2 + ⌊回合/3⌋` |")
    A("| 生命上限 | 100 |")
    A("")
    A("商店概率（按等级）：")
    A("")
    A("| 等级 | 1费 | 2费 | 3费 | 4费 | 5费 |")
    A("|---|---|---|---|---|---|")
    for lv, odds in [(2, [100, 0, 0, 0, 0]), (3, [75, 25, 0, 0, 0]), (4, [55, 30, 15, 0, 0]),
                     (5, [45, 33, 20, 2, 0]), (6, [35, 35, 25, 5, 0]), (7, [22, 30, 30, 15, 3]),
                     (8, [15, 25, 30, 25, 5]), (9, [10, 15, 25, 30, 20])]:
        A("| %d | %s |" % (lv, " | ".join(str(x) for x in odds)))
    A("")
    A("卡池：1 费 18 张、2 费 14、3 费 11、4 费 8、5 费 6。")
    A("")
    A("---")
    A("")
    A("## 2. 羁绊全表（%d 条 / %d 档）" % (len(traits), sum(len(t["tiers"]) for t in traits)))
    A("")
    for t in traits:
        kind = {"element": "元素", "class": "职业", "faction": "阵营"}.get(t["type"], "")
        n = sum(1 for u in units if t["id"] in (u.get("traits") or []))
        A("### %s（%s，%d 名棋子）" % (t["name"], kind, n))
        A("")
        for tier in t["tiers"]:
            A("- **%d 人**：%s" % (tier["count"], tier["text"]))
        A("")
    A("---")
    A("")
    A("## 3. 咒具（%d 件）" % len(items))
    A("")
    A("| 名称 | 类型 | 属性 | 效果 |")
    A("|---|---|---|---|")
    for it in items:
        stat = "、".join("%s+%s" % (k, v) for k, v in (it.get("stat") or {}).items())
        A("| %s | %s | %s | %s |" % (it["name"], "成装" if it["kind"] == "complete" else "组件", stat, it["text"]))
    A("")
    A("---")
    A("")
    A("## 4. 异格（%d 组，覆盖 %d 个本体 / 共 %d 个角色）" % (len(multi), len(by_base), len(units)))
    A("")
    A("同一角色的不同卡面是**独立棋子**：费用、元素、技能、定位都可能不同。")
    A("")
    A("| 本体 | 形态数 | 形态（费用 / 元素） |")
    A("|---|---|---|")
    for base, vs in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        forms = " / ".join("%s %d费%s" % (v["variant"] or "(无)", v["cost"], v["element"]) for v in vs)
        A("| %s | %d | %s |" % (base, len(vs), forms))
    A("")
    A("---")
    A("")
    A("## 4.5 品质（R / SR / SSR）与强度档位")
    A("")
    A("来源：**官方强度榜（速查）** —— <https://www.gamekee.com/jk/652351.html>，"
      "由 `tools/parse_tierlist.py` 解析、`tools/apply_tierlist.py` 写入。")
    A("")
    A("榜单命名规则是 `元素 + 角色简称`，作者**只给非 SSR 的卡加 `R` / `SR` 前缀**"
      "（`R虎杖`、`SR七海`、`影七SP`…），没有前缀的就是 SSR 卡。"
      "实测规律自洽：SSS/SS 档 0 张带前缀，C 档 16 张里 10 张带前缀。")
    A("")
    A("| 品质 | 判定依据（榜单标注） | 数量（可玩 / 全部） | 费用区间 |")
    A("|---|---|---|---|")
    for rk, why in (("SSR", "无前缀（绝大多数）"), ("SR", "带 `SR` 前缀"), ("R", "带 `R` 前缀")):
        n_play = sum(1 for u in units if u.get("rarity") == rk and u.get("playable"))
        n_all = sum(1 for u in units if u.get("rarity") == rk)
        costs = sorted(set(u["cost"] for u in units if u.get("rarity") == rk))
        A("| **%s** | %s | %d / %d | %s 费 |" % (rk, why, n_play, n_all, "·".join(str(c) for c in costs)))
    A("")
    A("### 强度档位（榜单原始分档）")
    A("")
    A("| 档位 | 含义 | 全部 | 可玩 |")
    A("|---|---|---|---|")
    for code, label in (("SSS", "顶级强者"), ("SS", "超模角色"), ("S", "强力角色"),
                        ("A", "标准强度"), ("B", "对策角色"), ("C", "怪人协会")):
        n_all = sum(1 for u in units if u.get("tier") == code)
        n_play = sum(1 for u in units if u.get("tier") == code and u.get("playable"))
        A("| **%s** | %s | %d | %d |" % (code, label, n_all, n_play))
    A("")
    A("> **品质与档位是两个独立维度**：品质是卡面稀有度（官方标注），档位是强度排行（官方点评）。")
    A("> 例如 `[疾走] 三轮霞` 是 **SSR + SSS 档**（顶级辅助），`[宿傩的容器] 虎杖悠仁` 是 **R + C 档**（初始卡）。")
    A("> **费用也不跟档次挂钩**：榜单评的是手游 PVE 就业强度，费用反映的是本作自走棋里的数值强度；")
    A("> 实测两者几乎不相关（1 费里既有 C 档也有 SSS 档），强行同步会把低费池变成 C 档专场。")
    A("")
    A("---")
    A("")
    A("## 4.6 异格联动（隐藏协同）")
    A("")
    A("同一角色的两个异格**同时上场**时触发，改动的是**技能机制**而不只是数值。")
    A("")
    for LK in links:
        A("### %s（`%s`）" % (LK["name"], LK["id"]))
        A("")
        A("- **成员**：%s" % " + ".join(LK.get("memberNames", [])))
        A("- **机制**：%s" % LK.get("mechanic", ""))
        A("- **效果**：%s" % "、".join("`%s`" % e for e in LK.get("effects", [])))
        A("- %s" % LK.get("desc", ""))
        A("")
    A("---")
    A("")
    A("## 5. 技能转化决策")
    A("")
    A("### 5.1 转化原则")
    A("")
    A("| 幻影夜行 | 自走棋 | 说明 |")
    A("|---|---|---|")
    A("| 稀有度 SSR/SR/R | 费用 5/3/1-2 | **wiki 无稀有度字段**，见 DATA_GAP §2.2：44 名沿用人工费用，其余按分位推断 |")
    A("| 属性（攻击/防御/强化/弱体/妨害/回复） | `role`（展示用）+ 决定射程 | 防御/体术 → 射程 1，其余 → 射程 3–4 |")
    A("| 特性（夜/影/幻/行） | 第一个羁绊（元素羁绊） | 直接对应 |")
    A("| 伤害类型（体术/术式/回复） | 第二个羁绊的兜底 + 攻速档位 | 体术 0.85 / 术式 0.70 / 回复 0.75 |")
    A("| 指挥技能（3 个） | **主动技能**：咒力满时自动释放 | 取消耗最高/最靠后的一个作为「招牌技」 |")
    A("| 必杀技 | 4–5 费棋子的**终结技**（2★ 后强化） | `ultimate.trigger = star2_after_cast` |")
    A("| 被动 | 常驻/触发型被动 | 关键词 → 11 种已实现的被动类型 |")
    A("| 领域展开 | 特级羁绊的全场机制 / 棋子主动技 | 见 `battle.js` `_tickDomains` |")
    A("")
    A("### 5.2 关键词 → 机制（主动技能）")
    A("")
    A("| 关键词 | 机制 | 落地效果 |")
    A("|---|---|---|")
    A("| 领域展开 / 领域 | `domain` | 全场 AoE + 自身增伤 8 秒且必中 |")
    A("| 召唤 / 式神 / 玉犬 / 鵺 | `summon` | 造成伤害并召唤 30% 属性的式神 |")
    A("| 眩晕 / 无法行动 | `stun` | 单体伤害 + 1.5 秒眩晕 |")
    A("| 对敌方全体 | `slam` | 以目标为圆心 1 格 AoE |")
    A("| 3连击 / 连击 | `barrage` | 对随机敌人打 3 段 |")
    A("| 护盾 / 屏障 | `shield` | 自身与相邻友军获得 20% 最大生命护盾 |")
    A("| 持续伤害 / 毒 / 出血 | `dot` | 单体伤害 + 5 秒侵蚀 |")
    A("| 直线 / 贯通 | `beam` | 同排贯穿 |")
    A("| 治疗 / 回复生命 | `heal` | 治疗生命最低的友军 25% |")
    A("| 降低 / 易伤 / 弱体 | `drain` | 伤害 + 抽走目标 20 咒力 |")
    A("| 其它单体 | `strike` | 对当前目标高倍率一击 |")
    A("")
    A("> 关键约束：**所有技能都必须有明确触发时机**（`trigger` 字段），"
      "不允许出现「手动选目标」这类自动战斗无法执行的设计。")
    A("")
    A("### 5.3 关键词 → 机制（被动）")
    A("")
    A("| 关键词 | 机制 | 落地效果 |")
    A("|---|---|---|")
    A("| 回合开始/波次开始 + 咒力 | `mana_on_cast` | 施法后额外回咒力 |")
    A("| 暴击 / 黑闪 | `bf` | 概率造成 2 倍伤害 |")
    A("| 回避 | `dodge` | 概率完全闪避 |")
    A("| 挑衅 | `taunt` | 提高被选取权重 + 18% 减伤 |")
    A("| 持续伤害 / 侵蚀 | `erode` | 普攻附带最大生命百分比伤害 |")
    A("| 全体队友 / 友方全体 | `aura_power` | 全队攻击提升 |")
    A("| 攻速 | `aura_haste` | 全队攻速提升 |")
    A("| 回复自身 / HP回复 | `regen_aura` | 每秒回复最大生命 |")
    A("| 击杀 | `lifesteal` | 造成伤害时吸血 |")
    A("| 降低咒力 | `mana_steal` | 普攻烧对手咒力 |")
    A("")
    A("### 5.4 转化置信度统计")
    A("")
    A("| 置信度 | 主动技能 | 被动 |")
    A("|---|---|---|")
    conf_s = Counter(u["skill"].get("confidence", "?") for u in units)
    conf_p = Counter(u["passive"].get("confidence", "?") for u in units)
    for k in ("authored", "high", "low", "missing"):
        A("| %s | %d | %d |" % (CONF_LABEL[k], conf_s.get(k, 0), conf_p.get(k, 0)))
    A("")
    A("> `low` / `missing` 的条目属于**待复核**，不是最终设计；原文都保留在 `wikiDesc` 里。")
    A("")
    A("---")
    A("")
    A("## 6. 棋子全表（%d 条）" % len(units))
    A("")
    A("列说明：**费用 / 元素 / 伤害类型 / 羁绊 / 生命 / 攻击 / 术式 / 射程 / 主动技能（机制+来源）/ 被动（机制+置信度）**")
    A("")
    for cost in (1, 2, 3, 4, 5):
        group = [u for u in units if u["cost"] == cost]
        if not group:
            continue
        A("### %d 费（%d 名）" % (cost, len(group)))
        A("")
        A("| 棋子 | 品质 | 元素 | 伤害 | 羁绊 | HP | 攻 | 术 | 射 | 主动技能 | 被动 |")
        A("|---|---|---|---|---|---|---|---|---|---|---|")
        for u in sorted(group, key=lambda x: (x["baseCharacter"], x["variant"])):
            tr = "·".join(u["traits"])
            sk = "%s（%s）" % (u["skill"].get("name", ""), SKILL_LABEL.get(u["skill"]["type"], u["skill"]["type"]))
            pa = u["passive"]
            pa_s = "%s（%s）" % (pa.get("name") or "无", PASSIVE_LABEL.get(pa["type"], pa["type"]))
            if pa.get("confidence") in ("low", "missing"):
                pa_s += " ⚠"
            mark = "" if u.get("playable") else " ·未实装"
            A("| %s%s | %s | %s | %s | %s | %d | %d | %d | %d | %s | %s |" %
              (u["name"], mark, u.get("rarity", "SR"), u["element"], u["dmg"], tr,
               u["hp"], u["ad"], u["spell"], u["range"], sk, pa_s))
        A("")
    A("---")
    A("")
    A("## 7. 下一步（Phase 7 后续模块）")
    A("")
    A("1. **异格联动**：同本体多形态同时上场时激活隐藏协同（至少 2 组），见 DEVLOG 的 P0 条目。")
    A("2. **待复核机制**：`low` 的 24 个主动技能 + 20 个被动逐个手写。")
    A("3. **UI 灵动化**：卡牌/羁绊/顶栏/跳字按 Phase 7 第三部分重构。")
    A("4. **P3 经济补丁**：胜利 +1 金、卖出 -1、伤害查表。")
    A("")

    open(OUT_DESIGN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("[design] %s  %d 行" % (OUT_DESIGN, len(L)))

    # ------------------------------------------------------------------ DEVLOG
    D = []
    B = D.append
    B("# DEVLOG.md —— 迭代日志（Web 版 Phase 7）")
    B("")
    B("> 只记录**这一轮**（网页端 Phase 7）做过什么、踩了什么坑、数据从哪来。")
    B("> Godot 阶段的历史日志见 `..\\咒术自走棋\\DEVLOG.md`。")
    B("")
    B("---")
    B("")
    B("## 迭代 P7-1 · Wiki 全量角色页抓取与异格还原（第一步交付）")
    B("")
    B("**目标**：把 Godot 阶段「30 个棋子硬编码」的假数据，换成从 wiki 逐个读出来的真实角色，"
      "并且把同一角色的不同异格作为独立棋子。")
    B("")
    B("### 做了什么")
    B("")
    B("| 步骤 | 产出 |")
    B("|---|---|")
    B("| 1. 抓在线目录树 | `tools/wiki_tree.json`，角色条目 **111** |")
    B("| 2. 逐页抓详情（增量缓存） | `tools/wiki_cache/content_*.json` |")
    B("| 3. 解析成结构化记录 | `tools/wiki_parsed/*.json`（技能/必杀/被动全文 + 属性图标） |")
    B("| 4. 图标哈希反查属性 | 特性 111/111、伤害类型 111/111、属性 110/111 |")
    B("| 5. 繁体页面归一 | 7 个异体字页面合并进本体（30 组异格） |")
    B("| 6. 规则引擎转化 | `tools/build_units.py` → `data/units.json`（111 条） |")
    B("| 7. 接入游戏 | `tools/build_data.py` 只取 `playable`（44 条）→ `data/game-data.js` |")
    B("")
    B("### 数据来源（每个异格都能溯源）")
    B("")
    B("`data/units.json` 里每条都有 `wikiUrl`，格式：`https://www.gamekee.com/jk/<content_id>.html`。")
    B("抓取与解析全程可复现：")
    B("")
    B("```powershell")
    B("python tools\\fetch_wiki.py      # 增量抓取 + 解析")
    B("python tools\\build_units.py     # 转化成自走棋棋子")
    B("python tools\\build_data.py      # 生成网页可用数据包")
    B("python tools\\gen_docs.py        # 重新生成本文档与 DESIGN.md 的表格")
    B("```")
    B("")
    B("### 踩到的坑")
    B("")
    B("1. **`content_id` 是整数不是字符串** —— 第一次跑 `build_units.py` 时 44 个已实装棋子"
      "全部 join 失败（`wiki.get('633431')` 取不到 `633431`）。修：统一 `str(cid)`。")
    B("2. **图鉴目录里混了 3 篇攻略**（强度榜/词条解释/一图流）—— 它们在旧缓存里被当成角色解析，"
      "导致\"无属性\"统计虚高。修：只取目录树「角色」节点的叶子。")
    B("3. **同一角色有繁体页面** —— `伏黒恵`/`釘崎野薔薇`/`禪院真希`/`狗巻棘`/`竜胆咲`/"
      "`伊地知潔高`/`結木海斗` 各自被拆成两个本体。修：`TRAD_MAP` 归 10 个异体字。")
    B("4. **「回复咒力」被误判成治疗** —— 关键词规则里 `回复` 太宽，13 个技能被分到 `heal`。"
      "修：治疗必须同时出现「治疗」或「回复生命」，并把 AoE/连击规则提到治疗之前。")
    B("5. **必杀值不是稀有度** —— 一度想用它推费用，实测 `【最强】五条悟 = 973`（最低档），"
      "证伪。见 DATA_GAP §2.3。")
    B("6. **稀有度字段根本不存在** —— wiki 全文没有 SSR/SR。费用只能人工锚点 + 分位推断。")
    B("7. **异格前缀在 140px 卡面上会被省略号截断** —— `【夜隐咒言师】狗卷棘` 太长。"
      "修：卡面拆成两行（金色小字前缀 + 白色本体名），见 `css/cards.css` 的 `.sc-variant`。")
    B("")
    B("### 验收")
    B("")
    B("```")
    B("node tools\\selftest.mjs   → 39 / 39 通过")
    B("浏览器 E2E（28 项交互）    → 28 / 28 通过")
    B("data/units.json           → 111 条，40 本体，30 异格组")
    B("```")
    B("")
    B("> 回归说明：`playable` 仍然只有原来的 44 条，且它们的数值/羁绊/机制被**原样保留**"
      "（`costSource: \"authored\"`），所以战斗平衡没有发生变化。"
      "新角色进商店要等「异格联动」模块一起上，避免卡池被稀释。")
    B("")
    B("### 已知遗留（下一步）")
    B("")
    B("| 优先级 | 项 |")
    B("|---|---|")
    B("| P0 | 异格联动：同本体多形态同时上场触发隐藏协同（≥2 组） |")
    B("| P0 | 把 30 组异格里的高人气组合放进可玩卡池 |")
    B("| P1 | 24 个 `low` 主动技能 + 20 个 `low` 被动 + 10 个 `missing` 被动手写复核 |")
    B("| P1 | UI 灵动化三件套（卡牌 / 羁绊 / 顶栏 + 跳字） |")
    B("| P2 | 5 费卡池扩到 9 张、2/3 星令牌缩放 |")
    B("| P3 | 胜利 +1 金、卖出 -1、伤害查表 |")
    B("")
    # DEVLOG.md 由人工维护（迭代日志不适合自动生成），这里不写文件
    print("[devlog] 跳过（人工维护）")
    print("[stats] 费用分布 %s" % rep["costDist"])
    print("[stats] 异格组 %d" % rep["altFormGroups"])


if __name__ == "__main__":
    main()
