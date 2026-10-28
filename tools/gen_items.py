# -*- coding: utf-8 -*-
r"""
gen_items.py —— 咒具（装备）数据

设计原则
  1. **名号必须出自原作**：游云、天逆鉾、黒縄、万里の鎖、屠坐魔、喉薬、獄門疆、
     呪胎九相図、天使の羽、宿儺之指、伏魔御厨子、釘と金槌 —— 全部是漫画/动画里真实出现的。
  2. **奇物也要**：五条悟在仙台出差买的伴手礼「毛豆奶油大福」（ずんだ大福）做成回复类装备，
     既符合原作梗，也给自走棋补一个前期续航件。
  3. 强度对齐自走棋节奏：散件（component）只给单条属性，成装（complete）给两条以上，
     且同档成装之间预算接近（约 2.4~2.8 个散件的价值）。
  4. 合成只吃散件，每个散件至少出现在 2 个配方里，避免死件。

用法：
    python tools\gen_items.py        # 写回 data/raw/items.json
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "items.json")

# ------------------------------------------------------------------ 散件
COMPONENTS = [
    {"id": "crystal", "name": "咒力结晶", "kind": "component", "icon": "crystal.svg",
     "lore": "浓缩到结晶化的咒力，术师随身带着应急。",
     "stat": {"spell": 18}, "text": "术式强度 +18"},
    {"id": "scroll", "name": "体术卷轴", "kind": "component", "icon": "scroll.svg",
     "lore": "记录体术运劲法门的旧卷轴。",
     "stat": {"ad": 12}, "text": "体术 +12"},
    {"id": "charm", "name": "护符", "kind": "component", "icon": "charm.svg",
     "lore": "咒术高专统一配发的护身符，聊胜于无。",
     "stat": {"hp": 180}, "text": "生命 +180"},
    {"id": "fang", "name": "玉犬之牙", "kind": "component", "icon": "fang.svg",
     "lore": "十种影法术·玉犬留下的牙，锋利得不像话。",
     "stat": {"as": 0.12}, "text": "攻速 +12%"},
    {"id": "fragment", "name": "咒具碎片", "kind": "component", "icon": "fragment.svg",
     "lore": "磨损的咒具残片，仍残留着咒力回路。",
     "stat": {"start_mana": 15}, "text": "初始咒力 +15"},
    {"id": "ward", "name": "结界符", "kind": "component", "icon": "ward.svg",
     "lore": "「帐」的边角料，能挡下一点冲击。",
     "stat": {"armor": 12}, "text": "减伤 +12%"},
    {"id": "kugi", "name": "钉与金槌", "kind": "component", "icon": "kugi.svg",
     "lore": "钉崎野蔷薇的刍灵咒法道具，钉入即共鸣。",
     "stat": {"bf": 0.08}, "text": "黑闪率 +8%"},
    {"id": "zunda", "name": "毛豆奶油大福", "kind": "component", "icon": "zunda.svg",
     "lore": "五条悟从仙台出差带回来的伴手礼，甜得发腻，但确实回血。",
     "stat": {"hp": 90, "regen": 1}, "text": "生命 +90，每秒回复 0.8% 生命"},
]

# ------------------------------------------------------------------ 成装
COMPLETES = [
    {"id": "yuyun", "name": "咒具·游云", "kind": "complete", "icon": "yuyun.svg",
     "recipe": ["scroll", "fang"],
     "lore": "三节棍形的特级咒具。威力取决于持有者的体术，是纯粹的力量放大器。",
     "stat": {"ad": 30, "as": 0.25}, "text": "体术 +30，攻速 +25%"},
    {"id": "ao", "name": "术式·苍", "kind": "complete", "icon": "ao.svg",
     "recipe": ["crystal", "fragment"],
     "lore": "五条家的术式顺转。「吸引」的具现，把周围的一切拉向中心。",
     "stat": {"spell": 40, "start_mana": 25}, "text": "术式强度 +40，初始咒力 +25"},
    {"id": "finger", "name": "特级咒物·宿傩之指", "kind": "complete", "icon": "finger.svg",
     "recipe": ["charm", "scroll"],
     "lore": "二十根手指，每一根都是诅咒之王的一部分。吞下去的人不是死了就是变了。",
     "stat": {"hp": 300, "ad": 22}, "text": "生命 +300，体术 +22"},
    {"id": "domain_talisman", "name": "领域符·伏魔御厨子", "kind": "complete", "icon": "domain.svg",
     "recipe": ["crystal", "charm"],
     "lore": "宿傩的领域。御厨子开张时，一切都在斩击的射程之内。",
     "stat": {"spell": 30, "hp": 150, "domain_plus": 4},
     "text": "术式强度 +30，生命 +150，领域展开提前 4 秒"},
    {"id": "tenka", "name": "特级咒具·天逆鉾", "kind": "complete", "icon": "spear.svg",
     "recipe": ["fragment", "ward"],
     "lore": "能中和一切术式的矛。伏黑甚尔靠它把五条悟逼到绝境。",
     "stat": {"spell": 22, "mres": 30},
     "text": "术式强度 +22，术式减伤 +30%（矛尖触到即中和术式）"},
    {"id": "kuro", "name": "咒具·黒縄", "kind": "complete", "icon": "rope.svg",
     "recipe": ["ward", "kugi"],
     "lore": "米格尔从故乡带来的黑绳，专门扰乱对手的术式运转。",
     "stat": {"armor": 15, "mres": 15},
     "text": "减伤 +15%，术式减伤 +15%（黒縄扰乱术式运转）"},
    {"id": "chain", "name": "咒具·万里の鎖", "kind": "complete", "icon": "chain.svg",
     "recipe": ["fang", "ward"],
     "lore": "甚尔藏在咒灵体内的锁链，长度没有尽头。",
     "stat": {"as": 0.15, "counter": 1.6},
     "text": "攻速 +15%，受到近战攻击时以 1.6 倍体术反击"},
    {"id": "zanshu", "name": "咒具·屠坐魔", "kind": "complete", "icon": "blade.svg",
     "recipe": ["scroll", "kugi"],
     "lore": "虎杖悠仁的短刀，缠着写有咒符的布。",
     "stat": {"ad": 26, "bf": 0.15}, "text": "体术 +26，黑闪率 +15%"},
    {"id": "nodo", "name": "咒具·喉薬", "kind": "complete", "icon": "potion.svg",
     "recipe": ["charm", "zunda"],
     "lore": "狗卷棘随身携带的喉药。咒言伤的是自己的喉咙，这瓶东西能吊住他。",
     "stat": {"hp": 200, "heal_ally": {"pct": 0.10, "interval": 5, "cost": 12}},
     "text": "生命 +200，每 5 秒消耗 12 咒力治疗残血友军 10% 生命"},
    {"id": "gokumon", "name": "特级咒物·獄門疆", "kind": "complete", "icon": "box.svg",
     "recipe": ["crystal", "kugi"],
     "lore": "把五条悟封进去的匣子。打开它需要另一个特级咒物。",
     "stat": {"spell": 35, "stun_on_cast": 0.6},
     "text": "术式强度 +35，施放技能时眩晕目标 0.6 秒"},
    {"id": "wing", "name": "咒物·天使之羽", "kind": "complete", "icon": "wing.svg",
     "recipe": ["fang", "zunda"],
     "lore": "死灭回游中「天使」的羽翼。它所照见的东西，会被剥离术式。",
     "stat": {"as": 0.20, "dodge": 0.15}, "text": "攻速 +20%，闪避 +15%"},
    {"id": "womb", "name": "咒物·呪胎九相図", "kind": "complete", "icon": "womb.svg",
     "recipe": ["charm", "fragment"],
     "lore": "九相图。胀相、血涂、坏相就是从这些图里生出来的。",
     "stat": {"hp": 220, "revive": 0.35},
     "text": "生命 +220，首次阵亡时以 35% 生命复活"},
]


def main():
    items = COMPONENTS + COMPLETES
    ids = set()
    for it in items:
        assert it["id"] not in ids, "重复 id: " + it["id"]
        ids.add(it["id"])
    for it in COMPLETES:
        for c in it["recipe"]:
            assert c in ids, "配方引用了不存在的散件: " + c
    # 每个散件至少出现在 2 个配方里
    use = {c["id"]: 0 for c in COMPONENTS}
    for it in COMPLETES:
        for c in it["recipe"]:
            use[c] += 1
    dead = [k for k, v in use.items() if v < 2]
    assert not dead, "这些散件配不到东西: %s" % dead

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[items] %d 件（散件 %d / 成装 %d）" % (len(items), len(COMPONENTS), len(COMPLETES)))
    for it in COMPLETES:
        print("   %-22s = %s" % (it["name"], " + ".join(it["recipe"])))


if __name__ == "__main__":
    main()
