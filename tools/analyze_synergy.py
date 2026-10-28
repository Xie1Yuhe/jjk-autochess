# -*- coding: utf-8 -*-
r"""
analyze_synergy.py —— 分析棋子之间的联动性，为「预设卡组」提供依据

分析维度：
  1. 羁绊（traits）覆盖：每条羁绊有几张卡、档位要求多少张
  2. 四特性（行/幻/夜/影）分布：影响属性克制
  3. 机制引擎：带状态 / 领域 / 召唤 / 光环 / 复活 / 计数 的卡
  4. 角色协同：异格联动成员、同角色多形态
  5. 交叉矩阵：某张卡同时属于哪几条羁绊

用法：python tools\analyze_synergy.py
输出：SYNERGY.md
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
TRAITS = os.path.join(ROOT, "data", "raw", "traits.json")
LINKS = os.path.join(ROOT, "data", "links.json")
OUT = os.path.join(ROOT, "SYNERGY.md")

ENGINE_KEYS = {
    "enterState": "状态切换",
    "domain": "领域展开",
    "altSkill": "双技能",
    "stackOnCast": "叠层",
    "scaleByCounter": "计数放大",
}


def engines_of(u):
    out = []
    sk = u.get("skill") or {}
    ul = u.get("ult") or {}
    for k, label in ENGINE_KEYS.items():
        if sk.get(k) or ul.get(k):
            out.append(label)
    mods = u.get("mods") or {}
    if mods.get("summon") or (sk.get("type") == "summon"):
        out.append("召唤")
    if mods.get("aura_power") or mods.get("aura_haste"):
        out.append("光环")
    if mods.get("reviveLeft"):
        out.append("复活")
    if mods.get("counterMult"):
        out.append("反击")
    if any(k.startswith("grow_") or k.startswith("counter_") for k in mods):
        out.append("计数")
    if mods.get("healAlly"):
        out.append("治疗")
    if mods.get("taunt"):
        out.append("嘲讽")
    return out


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    traits = json.load(open(TRAITS, encoding="utf-8"))
    links = json.load(open(LINKS, encoding="utf-8"))
    trait_by_id = {t["id"]: t for t in traits}

    L = []
    A = L.append
    A("# SYNERGY.md —— 棋子联动性分析（预设卡组的依据）")
    A("")
    A("> 由 `python tools\\analyze_synergy.py` 生成。")
    A("")

    # ---------------- 1. 羁绊覆盖
    A("## 1. 羁绊覆盖情况")
    A("")
    A("| 羁绊 | 类型 | 总卡数 | 档位要求 | 能否凑满最高档 |")
    A("|---|---|---|---|---|")
    by_trait = defaultdict(list)
    for u in units:
        for t in u.get("traits") or []:
            by_trait[t].append(u)
    for t in traits:
        tid = t["id"]
        lst = by_trait.get(tid, [])
        need = [x["count"] for x in t.get("tiers", [])]
        top = max(need) if need else 0
        ok = "✅" if len(lst) >= top else ("⚠ 差 %d" % (top - len(lst)))
        A("| %s | %s | %d | %s | %s |" % (
            t.get("name", tid), t.get("type", ""), len(lst),
            "/".join(str(n) for n in need), ok))
    A("")

    # ---------------- 2. 四特性分布
    A("## 2. 四特性分布")
    A("")
    el = Counter(u["element"] for u in units)
    A("| 特性 | 数量 |")
    A("|---|---|")
    for k in ("行", "幻", "夜", "影"):
        A("| %s | %d |" % (k, el.get(k, 0)))
    A("")

    # ---------------- 3. 机制引擎
    A("## 3. 机制引擎分布（哪些卡能当“核心”）")
    A("")
    eng = defaultdict(list)
    for u in units:
        for e in engines_of(u):
            eng[e].append(u["name"])
    A("| 引擎 | 张数 | 代表棋子 |")
    A("|---|---|---|")
    for k, v in sorted(eng.items(), key=lambda kv: -len(kv[1])):
        A("| %s | %d | %s |" % (k, len(v), "、".join(v[:4]) + ("…" if len(v) > 4 else "")))
    A("")

    # ---------------- 4. 交叉：羁绊组合
    A("## 4. 天然成型的羁绊组合（两张卡以上重叠）")
    A("")
    pair = Counter()
    for u in units:
        ts = sorted(u.get("traits") or [])
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pair[(ts[i], ts[j])] += 1
    A("| 组合 | 同时满足的卡数 |")
    A("|---|---|")
    for (a, b), n in pair.most_common(14):
        A("| %s + %s | %d |" % (
            trait_by_id.get(a, {}).get("name", a),
            trait_by_id.get(b, {}).get("name", b), n))
    A("")

    # ---------------- 5. 联动与同角色
    A("## 5. 异格联动（必须同时上两个异格）")
    A("")
    for lk in links:
        members = lk.get("memberNames") or []
        have = [m for m in (lk.get("members") or []) if any(u["id"] == m for u in units)]
        A("- **%s**：%s（成员齐全：%s）" % (
            lk["name"], " + ".join(members), "是" if len(have) == len(lk.get("members", [])) else "否"))
    A("")

    # ---------------- 6. 每条羁绊的成员清单（组卡时用）
    A("## 6. 各羁绊成员清单")
    A("")
    for t in traits:
        tid = t["id"]
        lst = sorted(by_trait.get(tid, []), key=lambda x: x["cost"])
        if not lst:
            continue
        A("### %s（%d 张）" % (t.get("name", tid), len(lst)))
        A("")
        A("| 棋子 | 费用 | 特性 | 其它羁绊 | 引擎 |")
        A("|---|---|---|---|---|")
        for u in lst:
            others = [trait_by_id.get(x, {}).get("name", x) for x in (u.get("traits") or []) if x != tid]
            A("| %s | %d | %s | %s | %s |" % (
                u["name"], u["cost"], u["element"],
                "、".join(others) or "—",
                "、".join(engines_of(u)) or "—"))
        A("")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[synergy] %s  %d 行" % (OUT, len(L)))
    print("[synergy] 羁绊 %d 条；四特性 %s" % (len(traits), dict(el)))


if __name__ == "__main__":
    main()
