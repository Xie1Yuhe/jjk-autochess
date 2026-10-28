# -*- coding: utf-8 -*-
r"""
power_audit.py —— 给每张棋子的「战斗力」建一个可复现的量化指标

为什么要它：
  「调整强度」如果没有度量，就只能凭感觉。这里定义一个透明的综合战斗值，
  用来看「同一费用档里谁明显偏强/偏弱」，以及「档位跨度是否合理」。

指标构成（都做了归一化，最终以 1000 为「平均卡」）：

  生存  EHP = hp / (1 - 减伤) + 护盾/复活折算
  输出  DPS = 主面板 × 攻速 × (1 + 黑闪/暴击期望)
  技能  技能收益 = 倍率 × 段数 × 面板 → 折算成「每 100 咒力能打出多少伤害」
  必杀  必杀收益 = 必杀倍率 × 段数 / 必杀槽需求 × 100
  功能  光环/治疗/复活/嘲讽/控制/易伤 折算成固定权重

注意：这是**设计用**的相对指标，不是精确战斗模拟。
它的用途是「找出同档内的异常值」，不是预测胜负。

用法：
    python tools\power_audit.py
输出：
    POWER_AUDIT.md
"""
import json
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
OUT = os.path.join(ROOT, "POWER_AUDIT.md")

PANEL_W = {"体术": "phys", "术式": "magic", "复合": "hybrid"}


def panel_of(sk, u):
    p = sk.get("panel")
    if p:
        return p
    if sk.get("hybrid"):
        return "hybrid"
    return "phys" if u.get("dmg") == "体术" else "magic"


def main_panel(u, panel):
    ad, sp = u.get("ad") or 0, u.get("spell") or 0
    if panel == "phys":
        return ad
    if panel == "magic":
        return sp
    return (ad + sp) / 2.0


def ehp(u, mods):
    hp = u.get("hp") or 1
    armor = mods.get("armor") or 0
    mres = mods.get("mres") or 0
    red = 1 - (1 - min(0.8, armor)) * (1 - min(0.8, mres))
    e = hp / max(0.2, 1 - red)
    if mods.get("reviveLeft"):
        e *= 1 + 0.45 * (mods.get("revivePct") or 0.35)
    if mods.get("invulnStart"):
        e *= 1 + 0.12 * min(4, mods["invulnStart"])
    if mods.get("healAlly"):
        e *= 1.08
    if mods.get("regen"):
        e *= 1.06
    return e


def dps(u, mods):
    panel = "phys" if u.get("dmg") == "体术" else "magic"
    base = main_panel(u, panel)
    asr = u.get("as") or 0.8
    crit = 1 + 0.5 * min(0.75, mods.get("bf") or 0)
    return base * asr * crit


def skill_value(u, sk):
    """技能折算：一次技能循环（攒 100 咒力）能打出的伤害"""
    if not sk:
        return 0.0
    cast_count = 100.0 / max(20.0, u.get("mana") or 100)
    panel = panel_of(sk, u)
    m = main_panel(u, panel)
    t = sk.get("type")
    if t in ("heal", "shield", "buff", "empower", "taunt", "summon"):
        # 功能技：按「等效输出」折算，避免它们在纯伤害指标里归零
        base = m * 0.9
    else:
        pw = sk.get("power") or 1.0
        hits = sk.get("hits") or 1
        base = m * pw * hits
    extra = 1.0
    if sk.get("applyTaken"):
        extra += sk["applyTaken"] * 1.2
    if sk.get("stun"):
        extra += 0.20
    if sk.get("dot"):
        extra += sk["dot"] * 8
    if sk.get("enterState"):
        extra += 0.25
    if sk.get("domain"):
        extra += 0.35
    if sk.get("stackOnCast"):
        extra += 0.18
    return base * cast_count * extra


def ult_value(u, ul, mods):
    if not ul or not ul.get("combat"):
        return 0.0
    cycles = 100.0 / max(40.0, (u.get("ultCost") or 100))
    panel = panel_of(ul, u)
    m = main_panel(u, panel)
    pw = ul.get("power") or 1.0
    hits = ul.get("hits") or 1
    extra = 1.0
    if ul.get("domain"):
        extra += 0.9
    if ul.get("applyTaken"):
        extra += ul["applyTaken"] * 1.2
    if ul.get("stun"):
        extra += 0.25
    if ul.get("dot"):
        extra += ul["dot"] * 8
    if ul.get("execute"):
        extra += 0.3
    if ul.get("scaleByCounter"):
        extra += 0.3
    return m * pw * hits * cycles * extra


def utility(mods):
    s = 0.0
    if mods.get("aura_power"):
        s += 100 * mods["aura_power"]
    if mods.get("aura_haste"):
        s += 80 * mods["aura_haste"]
    if mods.get("healAlly"):
        s += 55
    if mods.get("reviveLeft"):
        s += 60
    if mods.get("taunt"):
        s += 25
    if mods.get("counterMult"):
        s += 40 * (mods["counterMult"] - 1)
    if mods.get("dodge"):
        s += 120 * mods["dodge"]
    if mods.get("elemHunter"):
        s += 40
    if mods.get("extra_attack"):
        s += 45
    if mods.get("immuneControl"):
        s += 30
    return s


def main():
    units = json.load(open(UNITS, encoding="utf-8"))

    rows = []
    for u in units:
        mods = u.get("mods") or {}
        e = ehp(u, mods)
        d = dps(u, mods)
        sv = skill_value(u, u.get("skill") or {})
        uv = ult_value(u, u.get("ult") or {}, mods)
        ut = utility(mods)
        # 综合：几何平均 + 加法项
        core = (e ** 0.42) * (d ** 0.38) * ((sv + uv + 1) ** 0.20)
        score = core + ut
        rows.append({
            "id": u["id"], "name": u["name"], "cost": u["cost"],
            "tier": u.get("tier"), "elem": u["element"], "dmg": u["dmg"],
            "ehp": e, "dps": d, "skill": sv, "ult": uv, "util": ut,
            "score": score,
        })

    # 归一化到「平均 = 1000」
    avg = sum(r["score"] for r in rows) / len(rows)
    for r in rows:
        r["idx"] = r["score"] / avg * 1000

    L = []
    A = L.append
    A("# POWER_AUDIT.md —— 战斗力量化审计")
    A("")
    A("> 由 `python tools\\power_audit.py` 生成。**用于找同档异常值**，不是胜负预测。")
    A("> 综合值以「全池平均 = 1000」归一化。")
    A("")

    by_cost = defaultdict(list)
    for r in rows:
        by_cost[r["cost"]].append(r)

    A("## 1. 各费用档分布（看档内离散度）")
    A("")
    A("| 费用 | 张数 | 均值 | 最低 | 最高 | 极差倍率 |")
    A("|---|---|---|---|---|---|")
    for c in sorted(by_cost):
        g = by_cost[c]
        v = sorted(x["idx"] for x in g)
        A("| %d | %d | %.0f | %.0f | %.0f | **%.2f×** |" % (
            c, len(g), sum(v) / len(v), v[0], v[-1], v[-1] / max(1, v[0])))
    A("")

    A("## 2. 档位（SSS→C）对应的实际强度")
    A("")
    A("| 档位 | 张数 | 平均综合值 | 主要费用 |")
    A("|---|---|---|---|")
    by_tier = defaultdict(list)
    for r in rows:
        by_tier[r["tier"] or "-"].append(r)
    order = ["SSS", "SS", "S", "A", "B", "C", "-"]
    for t in order:
        g = by_tier.get(t)
        if not g:
            continue
        costs = defaultdict(int)
        for x in g:
            costs[x["cost"]] += 1
        top = sorted(costs.items(), key=lambda kv: -kv[1])[:2]
        A("| %s | %d | %.0f | %s |" % (
            t, len(g), sum(x["idx"] for x in g) / len(g),
            "、".join("%d费" % c for c, _ in top)))
    A("")

    A("## 3. 每个费用档内的极端值（重点看这里）")
    A("")
    for c in sorted(by_cost):
        g = sorted(by_cost[c], key=lambda x: -x["idx"])
        A("### %d 费（%d 张）" % (c, len(g)))
        A("")
        A("| 排名 | 棋子 | 综合值 | 生存 | 输出 | 技能 | 必杀 | 功能 |")
        A("|---|---|---|---|---|---|---|---|")
        show = g[:3] + ([None] if len(g) > 6 else []) + g[-3:]
        for i, r in enumerate(show):
            if r is None:
                A("| … | … | | | | | | |")
                continue
            A("| %s | %s | **%.0f** | %.0f | %.0f | %.0f | %.0f | %.0f |" % (
                ("↑%d" % (i + 1)) if r in g[:3] else ("↓%d" % (len(g) - (2 - (i - len(show) + 3)))),
                r["name"], r["idx"], r["ehp"], r["dps"], r["skill"], r["ult"], r["util"]))
        A("")

    A("## 4. 全池最偏强的 15 张 / 最偏弱的 15 张")
    A("")
    s = sorted(rows, key=lambda x: -x["idx"])
    A("| | 棋子 | 费 | 档位 | 综合值 |")
    A("|---|---|---|---|---|")
    for r in s[:15]:
        A("| 强 | %s | %d | %s | **%.0f** |" % (r["name"], r["cost"], r["tier"], r["idx"]))
    for r in s[-15:]:
        A("| 弱 | %s | %d | %s | **%.0f** |" % (r["name"], r["cost"], r["tier"], r["idx"]))
    A("")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[power] %s  %d 行" % (OUT, len(L)))
    for c in sorted(by_cost):
        g = by_cost[c]
        v = sorted(x["idx"] for x in g)
        print("   %d费: 均值 %.0f  范围 %.0f~%.0f  极差 %.2f×" % (
            c, sum(v) / len(v), v[0], v[-1], v[-1] / max(1, v[0])))


if __name__ == "__main__":
    main()
