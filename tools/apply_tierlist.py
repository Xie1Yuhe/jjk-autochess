# -*- coding: utf-8 -*-
r"""
apply_tierlist.py —— 用官方强度榜（wiki 652351「强度榜（速查）」）修订品质与强度档位

数据来源
    https://www.gamekee.com/jk/652351.html
    页面结构：content_json 里有一个 illustrated-book 节点，
    6 个分档（SSS/SS/S/A/B/C），每个条目直接带
        {"name": 缩写名, "avatar": 头像, "jumpHref": "https://www.gamekee.com/jk/<cid>.html"}
    所以「档次 → 角色 id」是确定映射，不需要 OCR 或点击跳转。
    抓取结果见 tools/tierlist_raw.json（由 tools/parse_tierlist.py 生成）。

品质口径（官方标注，不是推断）
    榜单给卡名加前缀的唯一目的就是标稀有度：
        有 `SR` 前缀 → SR 卡；有 `R` 前缀 → R 卡；**没有前缀 → SSR 卡**
    实测分布：SSS/SS 档 0 张带前缀，C 档 16 张里 10 张带前缀 —— 规律自洽。
    结果：91 SSR / 11 SR / 9 R，与用户描述的「大部分是 SSR」一致。

    注意：品质是**按卡**而不是按角色 —— 狗卷棘有 R 卡，也有 SSR 卡。

费用不动
    费用反映的是「在本作自走棋里的数值强度」（wiki 5 破数值分位，已过 60 局平衡验证）；
    榜单评的是手游 PVE 就业强度。两者不是一回事，强行同步会把 1 费池变成 C 档专场。
    实测也证明二者几乎不相关：1 费里既有 C 档也有 SSS 档。

用法（必须排在 apply_rarity.py 之后，因为它会覆盖 rarity）：
    python tools\apply_tierlist.py
"""
import json
import os
import re
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
RAW = os.path.join(ROOT, "tools", "tierlist_raw.json")
REPORT = os.path.join(ROOT, "tools", "tierlist_report.json")

RARITY_COLOR = {"R": "#7f8ea3", "SR": "#4d9bff", "SSR": "#f0c34a"}

# 档位 → 展示用的中文名与颜色（从强到弱）
TIERS = [
    ("SSS", "顶级强者", "#ff4d6d"),
    ("SS", "超模角色", "#ff9f43"),
    ("S", "强力角色", "#a3e635"),
    ("A", "标准强度", "#4d9bff"),
    ("B", "对策角色", "#8b95a7"),
    ("C", "怪人协会", "#5f6673"),
]
TIER_META = {k: (label, color) for k, label, color in TIERS}


def label_rarity(name):
    """从榜单卡名读稀有度：只有 R / SR 会带前缀，其余视为 SSR。"""
    if re.match(r"^SR", name or ""):
        return "SR"
    if re.match(r"^R(?![a-zA-Z])", name or ""):
        return "R"
    return None


def main():
    units = json.load(open(UNITS, encoding="utf-8"))
    raw = json.load(open(RAW, encoding="utf-8"))
    tier_of = raw["tierOf"]
    name_of = raw["nameOf"]

    before = Counter(u.get("rarity") for u in units)
    changed = []
    missing = []

    for u in units:
        cid = u["id"]
        if cid not in tier_of:
            missing.append(u["name"])
            continue
        tier = tier_of[cid]
        label, color = TIER_META[tier]
        u["tier"] = tier
        u["tierLabel"] = label
        u["tierColor"] = color
        u["tierName"] = name_of.get(cid, "")

        explicit = label_rarity(name_of.get(cid, ""))
        new = explicit or "SSR"
        u["raritySource"] = "tierlist-label" if explicit else "tierlist-implied"
        if u.get("rarity") != new:
            changed.append((u["name"], u.get("rarity"), new))
        u["rarity"] = new
        u["rarityColor"] = RARITY_COLOR[new]

    after = Counter(u["rarity"] for u in units)
    tier_dist = Counter(u.get("tier") for u in units)

    json.dump(units, open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    playable = [u for u in units if u.get("playable")]
    rep = {
        "source": "https://www.gamekee.com/jk/652351.html",
        "coverage": "%d/%d" % (len(units) - len(missing), len(units)),
        "missing": missing,
        "rarityBefore": dict(before),
        "rarityAfter": dict(after),
        "rarityPlayable": dict(Counter(u["rarity"] for u in playable)),
        "tierDist": dict(tier_dist),
        "tierDistPlayable": dict(Counter(u.get("tier") for u in playable)),
        "changedRarity": [{"name": n, "from": a, "to": b} for n, a, b in changed],
    }
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[tierlist] 覆盖 %s，缺失 %d" % (rep["coverage"], len(missing)))
    print("[tierlist] 品质 %s → %s" % (dict(before), dict(after)))
    print("[tierlist] 可玩 58 的品质: %s" % rep["rarityPlayable"])
    print("[tierlist] 档位分布: %s" % dict(sorted(tier_dist.items(), key=lambda kv: TIER_META[kv[0]][0] and [t[0] for t in TIERS].index(kv[0]))))
    print("[tierlist] 显式标注的卡:")
    for u in units:
        if u.get("raritySource") == "tierlist-label":
            print("    %-24s %s  %s档" % (u["name"], u["rarity"], u.get("tier")))
    print("[tierlist] 品质变化 %d 条" % len(changed))


if __name__ == "__main__":
    main()
