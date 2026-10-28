# -*- coding: utf-8 -*-
r"""
add_traits_2.py —— 新增两条羁绊：反转术式 / 十种影法术

反转术式（反转）
  Lv1（2人）：全队每秒回复 0.6% 生命
  Lv2（3人）：血量首次 ≤30% 时立刻回复 25%（每场一次）

十种影法术（影法）
  Lv1（2人）：召唤物全属性 +20%
  Lv2（3人）：召唤物额外继承本体 10% 体术
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEW = [
    {
        "id": "反转", "type": "class", "name": "反转术式", "color": "#7ef0c0",
        "tiers": [
            {"count": 2, "text": "治愈之光：全队每秒回复 0.6% 生命。"},
            {"count": 3, "text": "反转生得：血量首次降至 30% 以下时，立刻回复 25% 生命（每场一次）。"}
        ]
    },
    {
        "id": "影法", "type": "class", "name": "十种影法术", "color": "#8fb4ff",
        "tiers": [
            {"count": 2, "text": "式神召唤：召唤物全属性 +20%。"},
            {"count": 3, "text": "影之继承：召唤物额外继承本体 10% 体术。"}
        ]
    },
]

# ---------------- 1) traits.json ----------------
tp = os.path.join(ROOT, "data", "raw", "traits.json")
t = json.load(io.open(tp, encoding="utf-8"))
ts = t["traits"] if isinstance(t, dict) and "traits" in t else t
have = {x["id"] for x in ts}
for item in NEW:
    if item["id"] not in have:
        ts.append(item)
        print("[trait] 加入 %s" % item["name"])
json.dump(t, io.open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------- 2) 分配角色 ----------------
ASSIGN = {
    "反转": ["家入硝子", "乙骨忧太", "秤金次", "禅院真依", "九十九由基"],
    "影法": ["伏黑惠", "魔虚罗"],
}
up = os.path.join(ROOT, "data", "units.json")
d = json.load(io.open(up, encoding="utf-8"))
units = d["units"] if isinstance(d, dict) and "units" in d else d

for tid, keys in ASSIGN.items():
    n = 0
    for u in units:
        base = u.get("baseCharacter") or ""
        if any(k in base for k in keys):
            tr = u.setdefault("traits", [])
            if tid not in tr and len(tr) < 3:
                tr.append(tid)
                n += 1
    print("[trait] %s 分配给 %d 个角色" % (tid, n))
json.dump(d, io.open(up, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------- 3) 引擎 ----------------
bp = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(bp, encoding="utf-8").read()

if "治愈之光（反转术式 Lv1）" not in s:
    anchor = "    /* —— 咒具师（按携带咒具数量成长） —— */"
    block = '''    /* —— 反转术式 —— */
    if (self._tier(t, '反转') >= 1) {                          // 治愈之光（反转术式 Lv1）
      u.mods.regen = true;
      u.mods.regenPct = Math.max(u.mods.regenPct || 0, 0.006);
    }
''' + anchor
    assert anchor in s, "anchor 咒具师"
    s = s.replace(anchor, block, 1)

if "regenPct || 0.02" not in s:
    old = "      u.hp = Math.min(u.maxHp, u.hp + u.maxHp * 0.02 * dt);"
    new = ("      var _rp = u.mods.regenPct || 0.02;                    // 反转术式 Lv1 可覆盖回复速率\n"
           "      u.hp = Math.min(u.maxHp, u.hp + u.maxHp * _rp * dt);")
    assert old in s, "regen tick"
    s = s.replace(old, new, 1)

if "反转生得（反转术式 Lv2）" not in s:
    anchor2 = "    if (u.mods.mana_drain) {"
    block2 = '''    // 反转生得（反转术式 Lv2）：首次低血自动回复
    if (this._tier(u.team, '反转') >= 2 && !u.mods.hpSave && u.alive && u.hp > 0
        && u.hp < u.maxHp * 0.3) {
      u.mods.hpSave = true;
      u.hp = Math.min(u.maxHp, u.hp + u.maxHp * 0.25);
      this._emit({ t: 'heal', pos: { x: u.pos.x, y: u.pos.y }, targetId: u.id, amount: u.maxHp * 0.25 });
    }
''' + anchor2
    s = s.replace(anchor2, block2, 1)

if "影法 Lv1" not in s:
    old3 = "    clone.maxHp = u.maxHp * 0.3;"
    new3 = ("    var _shT = this._tier(u.team, '影法');\n"
            "    var _shMul = _shT >= 1 ? 1.2 : 1;              // 影法 Lv1 召唤物 +20%\n"
            "    clone.maxHp = u.maxHp * 0.3 * _shMul;")
    assert old3 in s, "clone hp"
    s = s.replace(old3, new3, 1)
    s = s.replace("    clone.ad = u.ad * 0.35;\n    clone.spell = u.spell * 0.35;",
                  "    clone.ad = u.ad * 0.35 * _shMul + (_shT >= 2 ? u.ad * 0.10 : 0);  // Lv2 继承 10% 体术\n"
                  "    clone.spell = u.spell * 0.35 * _shMul;", 1)

io.open(bp, "w", encoding="utf-8").write(s)
print("[trait] 引擎已实现两条羁绊")
