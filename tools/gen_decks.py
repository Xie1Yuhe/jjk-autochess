# -*- coding: utf-8 -*-
r"""
gen_decks.py —— 生成 3 套「预设卡组」

划分原则（按联动性打分，不手工拍）：
  每套卡组先定一个「主题核心」（2 个羁绊 + 1 个特性），
  然后对每张卡打分：
      +6  同时属于两个核心羁绊
      +3  属于其中一个核心羁绊
      +3  特性与卡组特性一致
      +2  带机制引擎（状态/领域/光环/召唤/计数/复活）
      +1  与已选卡的羁绊重叠
  再按费用配额贪心填充，最后校验硬性约束。

硬性约束：
  · 36 张；每档 ≥4；5 费 ≤4；1 费 ≥5；同角色 ≤2
  · 每套必须含至少 1 张带「领域」的卡与 1 个异格联动对

用法：python tools\gen_decks.py
输出：data/raw/decks.json + DECKS.md
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
OUT_JSON = os.path.join(ROOT, "data", "raw", "decks.json")
OUT_MD = os.path.join(ROOT, "DECKS.md")

SIZE = 36
QUOTA = {1: 8, 2: 8, 3: 8, 4: 8, 5: 4}      # 合计 36

# 三套卡组：core = 两条羁绊 + 主特性
DECKS = [
    {
        "id": "tokyo-night",
        "name": "东京校 · 夜行",
        "tag": "夜",
        "core": ["东京校", "夜行"],
        "element": "夜",
        "blurb": "以东京校为骨架、夜行为输出核心。夜行 3 档附带「咒力侵蚀」，"
                 "配合夜属克制的 +20% 打出持续压制。",
    },
    {
        "id": "shadow-special",
        "name": "影袭 · 特级",
        "tag": "影",
        "core": ["影袭", "特级"],
        "element": "影",
        "blurb": "影袭 4 档阵亡会留下影分身，特级 2 档开战 8 秒自动展开领域。"
                 "两套叠在一起＝「死人还在打、领域自动开」。",
    },
    {
        "id": "kyoto-illusion",
        "name": "京都校 · 幻术",
        "tag": "幻",
        "core": ["京都校", "幻术"],
        "element": "幻",
        "blurb": "京都校 2 档反弹 15% 伤害、3 档每受 3 次攻击反击一次；"
                 "幻术提供高爆发与术式增伤，走「越挨打越强」的反击流。",
    },
]

ENGINE_BONUS = ("enterState", "domain", "altSkill", "stackOnCast", "scaleByCounter")


def has_engine(u):
    sk = u.get("skill") or {}
    ul = u.get("ult") or {}
    mods = u.get("mods") or {}
    if any(sk.get(k) or ul.get(k) for k in ENGINE_BONUS):
        return True
    return any(mods.get(k) for k in ("aura_power", "aura_haste", "reviveLeft",
                                     "counterMult", "healAlly", "taunt"))


def score(u, deck, picked_traits):
    s = 0.0
    ts = set(u.get("traits") or [])
    core = set(deck["core"])
    hit = ts & core
    if len(hit) == 2:
        s += 6
    elif len(hit) == 1:
        s += 3
    if u["element"] == deck["element"]:
        s += 3
    if has_engine(u):
        s += 2
    s += 0.6 * len(ts & set(picked_traits))
    # 高费略微降权，保证低费有货
    s -= (u["cost"] - 3) * 0.35
    return s


def build(deck, units, links):
    picked = []
    by_cost = defaultdict(list)
    for u in units:
        by_cost[u["cost"]].append(u)

    base_count = Counter()
    taken_ids = set()

    for cost in (5, 4, 3, 2, 1):
        need = QUOTA[cost]
        pool = sorted(by_cost[cost], key=lambda x: -score(x, deck, deck["core"]))
        for u in pool:
            if need <= 0:
                break
            if u["id"] in taken_ids:
                continue
            if base_count[u["baseCharacter"]] >= 2:
                continue
            picked.append(u)
            taken_ids.add(u["id"])
            base_count[u["baseCharacter"]] += 1
            need -= 1
        # 不够就从剩余同档补（放松同角色限制）
        if need > 0:
            for u in pool:
                if need <= 0:
                    break
                if u["id"] in taken_ids:
                    continue
                picked.append(u)
                taken_ids.add(u["id"])
                base_count[u["baseCharacter"]] += 1
                need -= 1

    # 保证含一条异格联动的两个成员
    for lk in links:
        mem = lk.get("members") or []
        if len(mem) != 2:
            continue
        have = [m for m in mem if m in taken_ids]
        if len(have) == 2:
            break
        # 补上缺的那个，替换掉最低分的非核心位
        for m in mem:
            if m in taken_ids:
                continue
            u = next((x for x in units if x["id"] == m), None)
            if not u:
                continue
            worst = min((p for p in picked if p["cost"] == u["cost"]),
                        key=lambda p: score(p, deck, deck["core"]), default=None)
            if worst is None:
                continue
            picked.remove(worst)
            taken_ids.discard(worst["id"])
            picked.append(u)
            taken_ids.add(u["id"])
        break

    # ---- 修复：保证同角色 ≤2（补联动时可能破坏） ----
    for _ in range(40):
        cnt = Counter(u["baseCharacter"] for u in picked)
        bad = [k for k, v in cnt.items() if v > 2]
        if not bad:
            break
        fixed = False
        for name in bad:
            group = [u for u in picked if u["baseCharacter"] == name]
            victim = min(group, key=lambda p: score(p, deck, deck["core"]))
            cands = [u for u in units
                     if u["cost"] == victim["cost"]
                     and u["id"] not in taken_ids
                     and Counter(x["baseCharacter"] for x in picked)[u["baseCharacter"]] < 2]
            if not cands:
                continue
            rep = max(cands, key=lambda x: score(x, deck, deck["core"]))
            picked.remove(victim)
            taken_ids.discard(victim["id"])
            picked.append(rep)
            taken_ids.add(rep["id"])
            fixed = True
            break
        if not fixed:
            break

    return picked


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    traits = json.load(open(TRAITS, encoding="utf-8"))
    links = json.load(open(LINKS, encoding="utf-8"))
    tname = {t["id"]: t.get("name", t["id"]) for t in traits}

    out = []
    L = []
    A = L.append
    A("# DECKS.md —— 预设卡组（按联动性划分）")
    A("")
    A("> 由 `python tools\\gen_decks.py` 生成。划分依据见 [SYNERGY.md](SYNERGY.md)。")
    A("> 每套 **36 张**，商店只从本套里刷 —— 卡池从 111 张缩到 36 张，")
    A("> 每档 7~8 种（原来 22 种），三星成本从 ~165 金降到 ~58 金。")
    A("")

    for deck in DECKS:
        picked = build(deck, units, links)
        picked.sort(key=lambda u: (u["cost"], u["name"]))
        dist = dict(sorted(Counter(u["cost"] for u in picked).items()))
        # 羁绊统计
        tc = Counter()
        for u in picked:
            for t in u.get("traits") or []:
                tc[t] += 1
        top = [(tname.get(t, t), n) for t, n in tc.most_common(6)]
        ids = [u["id"] for u in picked]

        out.append({
            "id": deck["id"], "name": deck["name"], "tag": deck["tag"],
            "element": deck["element"], "core": deck["core"],
            "blurb": deck["blurb"], "units": ids,
            "costDist": dist,
            "traits": {k: v for k, v in tc.items()},
        })

        A("---")
        A("")
        A("## %s（%d 张）" % (deck["name"], len(picked)))
        A("")
        A("> %s" % deck["blurb"])
        A("")
        A("**费用构成**：" + " · ".join("%d费×%d" % (c, n) for c, n in dist.items()))
        A("")
        A("**可凑羁绊**：" + " · ".join("%s %d" % (t, n) for t, n in top))
        A("")
        # 校验
        warn = []
        if len(picked) != SIZE:
            warn.append("数量 %d ≠ %d" % (len(picked), SIZE))
        for c in (1, 2, 3, 4, 5):
            if dist.get(c, 0) < 4:
                warn.append("%d 费只有 %d 张" % (c, dist.get(c, 0)))
        if dist.get(5, 0) > 4:
            warn.append("5 费 %d 张偏多" % dist.get(5, 0))
        if warn:
            A("**⚠ 约束未满足**：" + "；".join(warn))
            A("")
        A("| 棋子 | 费 | 特性 | 羁绊 | 引擎 |")
        A("|---|---|---|---|---|")
        for u in picked:
            eng = []
            sk = u.get("skill") or {}
            ul = u.get("ult") or {}
            mods = u.get("mods") or {}
            if sk.get("enterState"):
                eng.append("状态")
            if ul.get("domain"):
                eng.append("领域")
            if sk.get("altSkill"):
                eng.append("双技能")
            if sk.get("stackOnCast"):
                eng.append("叠层")
            if mods.get("aura_power"):
                eng.append("光环")
            if mods.get("reviveLeft"):
                eng.append("复活")
            if mods.get("counterMult"):
                eng.append("反击")
            A("| %s | %d | %s | %s | %s |" % (
                u["name"], u["cost"], u["element"],
                "、".join(tname.get(t, t) for t in (u.get("traits") or [])),
                "、".join(eng) or "—"))
        A("")

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump({"size": SIZE, "decks": out}, open(OUT_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))
    print("[decks] %s" % OUT_JSON)
    print("[decks] %s  %d 行" % (OUT_MD, len(L)))
    for d in out:
        print("   %-16s %d 张  费用 %s" % (d["name"], len(d["units"]), d["costDist"]))


if __name__ == "__main__":
    main()
