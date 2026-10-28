# -*- coding: utf-8 -*-
r"""
build_data.py —— 生成网页端可直接 <script> 引入的数据包 data/game-data.js

输入：
    data/units.json         Phase 7 重新生成的棋子全表（111 条，含异格；playable 标记谁进商店）
    data/raw/traits.json    羁绊
    data/raw/items.json     咒具
    data/raw/pve.json       PvE 波次
    data/raw/ai_plans.json  AI 阵容蓝图

为什么不用 fetch：这样双击 index.html（file:// 协议）也能跑，不需要起本地服务器。

用法：
    python tools\build_data.py
"""
import json
import os
import shutil
import sys
import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
OUT_DIR = DATA

QUALITY = {
    1: {"key": "B", "label": "B", "index": 0},
    2: {"key": "B", "label": "B", "index": 0},
    3: {"key": "A", "label": "A", "index": 1},
    4: {"key": "S", "label": "S", "index": 2},
    5: {"key": "SS", "label": "SS", "index": 3},
}
ELEMENT_LABEL = {"夜": "夜行", "影": "影袭", "幻": "幻术", "行": "行咒"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    units_all = load(os.path.join(DATA, "units.json"))
    traits = load(os.path.join(RAW, "traits.json"))
    items = load(os.path.join(RAW, "items.json"))
    pve = load(os.path.join(RAW, "pve.json"))
    plans = load(os.path.join(RAW, "ai_plans.json"))
    links = load(os.path.join(DATA, "links.json"))
    elements = load(os.path.join(DATA, "elements.json"))

    playable = [u for u in units_all if u.get("playable")]
    out_units = []
    for u in playable:
        d = {
            "id": u["id"],
            "name": u["name"],
            "title": u.get("variant") or u.get("wikiTitle", ""),
            "cost": u["cost"],
            "element": u["element"],
            "role": u.get("role", "攻击"),
            "dmg": u.get("dmg", "术式"),
            "traits": list(u.get("traits") or []),
            "hp": u["hp"], "ad": u["ad"], "spell": u["spell"], "as": u["as"],
            "range": u["range"], "mana": u["mana"], "start_mana": u["start_mana"],
            "skill": {k: u["skill"].get(k) for k in (
                "name", "type", "power", "desc", "hits", "sameTarget", "radius", "panel",
                "hybrid", "sure", "crit", "stun", "dot", "dotDur", "applyTaken", "taunt",
                "guard", "armNext", "debuffBonus", "debuffMax", "lastHitBf", "amp", "dur",
                "execute", "applyWeaken", "enterState", "stateWhy", "altSkill", "stackOnCast", "scaleByCounter",
                  "chain")},
            "ult": u.get("ult") or None,
            "ultCost": u.get("ultCost") or None,
            "mods": u.get("mods") or None,
            "batch": u.get("batch") or None,
            "passive": {k: u["passive"].get(k) for k in ("name", "type", "kind", "value", "desc")},
            "ultimate": {"name": u["ultimate"].get("name", ""), "effect": u["ultimate"].get("effect", "")},
            "icon": "assets/units/%s.webp" % u["id"],
            "card": "assets/cards/%s.webp" % u["id"],
            "quality": QUALITY[int(u["cost"])],
            "rarity": u.get("rarity", "SR"),
            "rarityColor": u.get("rarityColor", "#4d9bff"),
            "raritySource": u.get("raritySource", ""),
            "tier": u.get("tier", ""),
            "tierLabel": u.get("tierLabel", ""),
            "tierColor": u.get("tierColor", "#8b95a7"),
            "element_label": ELEMENT_LABEL.get(u["element"], u["element"]),
            "baseCharacter": u.get("baseCharacter", ""),
            "variant": u.get("variant", ""),
        }
        out_units.append(d)

    traits_out = []
    for t in traits:
        d = dict(t)
        d["glyph"] = t["name"][0]
        traits_out.append(d)

    data = {
        "meta": {
            "title": "咒术回战：幻影夜行 · 自走棋",
            "version": "1.2.0-web-phase7",
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "counts": {
                "unitsPlayable": len(out_units),
                "unitsTotal": len(units_all),
                "altFormGroups": len({u["baseCharacter"] for u in units_all}) and
                sum(1 for b in {u["baseCharacter"] for u in units_all}
                    if sum(1 for y in units_all if y["baseCharacter"] == b) > 1),
                "traits": len(traits_out), "items": len(items), "pve": len(pve), "plans": len(plans),
            },
            "source": "gamekee《咒术回战 幻影夜行》wiki（tools/fetch_wiki.py 抓取）",
        },
        "units": out_units,
        "unitIndex": {u["id"]: {"name": u["name"], "base": u["baseCharacter"], "variant": u["variant"],
                                "playable": u["playable"], "cost": u["cost"]} for u in units_all},
        "traits": traits_out,
        "links": links,
    "decks": (lambda: (__import__('json').load(open(os.path.join(RAW, 'decks.json'), encoding='utf-8'))
                        if os.path.exists(os.path.join(RAW, 'decks.json')) else {"size": 0, "decks": []}))(),
        "elements": elements,
        "tierlist": {"source": "https://www.gamekee.com/jk/652351.html"},
        "items": items,
        "pve": pve,
        "plans": plans,
    }

    body = json.dumps(data, ensure_ascii=False, indent=1)
    js = "/* 自动生成：python tools/build_data.py —— 请勿手改本文件 */\n"
    js += "window.JJK_DATA = " + body + ";\n"
    dest = os.path.join(OUT_DIR, "game-data.js")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)

    print("[data] playable=%d / total=%d  traits=%d items=%d pve=%d plans=%d -> %.1f KB" %
          (len(out_units), len(units_all), len(traits_out), len(items), len(pve), len(plans),
           os.path.getsize(dest) / 1024.0))


if __name__ == "__main__":
    main()
