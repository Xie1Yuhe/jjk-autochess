# -*- coding: utf-8 -*-
r"""
gen_compare.py —— 生成 COMPARE_WIKI.md：逐卡「原作 → 我们的实现 → 差异」对照表

用途：人工核对 111 张棋子有没有把原作的核心特色做对。
数据源：
  · 原文   —— units.json 里的 skill/ultimate/passive 的 wikiDesc（从 gamekee 抓的正文）
  · 实现   —— 我们的 skill.type/desc、ult.desc、passive.desc 与 mods

自动差异提示（只是线索，需要人判断）：
  · 原文有「复活」但 mods 没有 reviveLeft
  · 原文有「吸引攻击/嘲讽」但 mods 没有 taunt
  · 原文有「概率回避」但 dodge 为 0
  · 原文小技能偏防御/辅助，我们却做成纯伤害
  · 原文必杀带「持续伤害」，我们必杀不是 dot
  · 原文提到「状态/变化」，我们没有任何状态类 mods

用法：
    python tools\gen_compare.py
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
OUT = os.path.join(ROOT, "COMPARE_WIKI.md")

TYPE_CN = {
    "strike": "单体", "slam": "范围/全体", "barrage": "多段连击", "beam": "直线",
    "dot": "持续伤害", "drain": "削咒", "stun": "眩晕", "heal": "治疗",
    "shield": "护盾", "buff": "全队增益", "empower": "自我强化",
    "summon": "召唤", "domain": "领域", "taunt": "嘲讽",
}

DEF_KW = ["受到伤害降低", "攻击无效", "回避", "回复自身", "回复全体", "护盾", "减伤"]
OFF_KW = ["对敌方全体", "对选定的敌人", "对选择的敌人", "造成"]
STATE_KW = ["状态", "变化", "形态", "模式"]


def has(t, kws):
    return any(k in (t or "") for k in kws)


def clip(s, n=200):
    s = (s or "").replace("\n", " ").replace("|", "/")
    return s if len(s) <= n else s[:n] + "…"


def flags(u):
    """自动差异提示"""
    out = []
    sk = u.get("skill") or {}
    ul = u.get("ult") or {}
    mods = u.get("mods") or {}
    sd = sk.get("wikiDesc") or ""
    ud = (u.get("ultimate") or {}).get("wikiDesc") or ""
    pd = (u.get("passive") or {}).get("wikiDesc") or ""
    blob = sd + ud + pd

    if "复活" in blob and not mods.get("reviveLeft"):
        out.append("原文有复活，我们没做")
    if ("吸引攻击" in blob or "嘲讽" in blob) and not mods.get("taunt"):
        out.append("原文有嘲讽，我们没做")
    if "概率回避" in blob and not (mods.get("dodge") or 0):
        out.append("原文有回避，我们没做")
    if has(sd, DEF_KW) and not has(sd, OFF_KW) and sk.get("type") in ("strike", "slam", "barrage", "dot", "drain"):
        out.append("原文小技能偏防御/辅助，我们做成了伤害")
    if "持续伤害" in ud and ul.get("type") != "dot":
        out.append("原文必杀带持续伤害，我们必杀不是 dot")
    if not sk.get("enterState") and has(blob, STATE_KW) and not any(
        k in mods for k in ("counter_counter", "grow_chain", "grow_nail", "grow_nada", "ultWhenLowMana")
    ) and not mods.get("bf_count_key"):
        out.append("原文提到状态切换/技能变化，我们没有对应状态机制")
    return out


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    by_base = {}
    for u in units:
        by_base.setdefault(u["baseCharacter"], []).append(u)
    for k in by_base:
        by_base[k].sort(key=lambda x: (x["cost"], x.get("variant") or ""))

    L = []
    A = L.append
    A("# COMPARE_WIKI.md —— 逐卡「原作 → 我们的实现」对照表")
    A("")
    A("> 由 `python tools\\gen_compare.py` 生成。**原文列是 gamekee 抓下来的技能正文**，")
    A("> 实现列是我们真正跑在游戏里的东西。看差异列来挑问题。")
    A("> ")
    A("> 差异列是**自动推断的线索**，不是结论——有些是误报（比如领域技能既有减伤又有伤害）。")
    A("")

    # 先扫一遍，把待核清单放到最前面
    pre = []
    for u in units:
        f = flags(u)
        if f:
            pre.append((u['name'], u['cost'], u.get('rarity', '-'), u['element'], f))
    pre.sort(key=lambda x: (x[1], x[0]))

    total = len(units)
    flagged = len(pre)

    A('## 待核清单（%d 张，按费用排序）' % flagged)
    A('')
    A('| 棋子 | 费用 | 品质 | 特性 | 疑似问题 |')
    A('|---|---|---|---|---|')
    for n, c, r, e, f in pre:
        A('| %s | %d | %s | %s | %s |' % (n, c, r, e, '；'.join(f)))
    A('')
    A('> 这些是**自动推断**的线索，需要你判断。有些是误报（例如领域技能既减伤又打伤害）。')
    A('')
    flagged = 0
    for base, list_ in sorted(by_base.items(), key=lambda kv: (kv[1][0]["cost"], kv[0])):
        A("---")
        A("")
        A("## %s（%d 张）" % (base, len(list_)))
        A("")
        for u in list_:
            sk = u.get("skill") or {}
            ul = u.get("ult") or {}
            pv = u.get("passive") or {}
            mods = u.get("mods") or {}
            f = flags(u)
            if f:
                flagged += 1
            A("### %s  ·  %d费 %s %s/&nbsp;%s" % (
                u["name"], u["cost"], u.get("rarity", "-"), u["element"], u["dmg"]))
            A("")
            A("| | 原作（wiki） | 我们的实现 |")
            A("|---|---|---|")
            A("| **小技能** | %s：%s | %s（%s） |" % (
                sk.get("name") or "-", clip(sk.get("wikiDesc"), 220),
                clip(sk.get("desc"), 120), TYPE_CN.get(sk.get("type"), sk.get("type"))))
            A("| **必杀** | %s：%s | %s |" % (
                ul.get("name") or "-", clip((u.get("ultimate") or {}).get("wikiDesc"), 220),
                clip(ul.get("desc") or "-", 140)))
            A("| **被动** | %s：%s | %s |" % (
                pv.get("name") or "-", clip(pv.get("wikiDesc"), 200),
                clip(pv.get("desc"), 140)))
            _es = sk.get("enterState")
            if _es:
                A("| **状态机制** | （原文的持续状态 / 技能变化） | **「%s」%.0f 秒**：%s%s%s |" % (
                    _es.get("name"), _es.get("dur", 20),
                    ("体术/术式 +%d%% " % round(_es.get("amp", 0) * 100)) if _es.get("amp") else "",
                    ("减伤 %d%% " % round(_es.get("guard", 0) * 100)) if _es.get("guard") else "",
                    ("→ 变招「%s」" % _es["skill"].get("name")) if _es.get("skill") else ""))
            A("| **机制参数** | — | `%s` |" % json.dumps(mods, ensure_ascii=False))
            A("")
            if f:
                A("**⚠ 待核：** " + "；".join(f))
                A("")

    A("---")
    A("")
    A("## 汇总")
    A("")
    A("| 项目 | 数值 |")
    A("|---|---|")
    A("| 棋子总数 | %d |" % total)
    A("| 自动标记待核 | **%d** |" % flagged)
    A("")
    A("> 剩下的 %d 张自动比对没发现明显问题，但仍建议扫一眼原文。" % (total - flagged))
    A("")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[compare] %s  %d 行" % (OUT, len(L)))
    print("[compare] 111 张，自动标记待核 %d 张" % flagged)


if __name__ == "__main__":
    main()
