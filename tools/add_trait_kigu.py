# -*- coding: utf-8 -*-
r"""
add_trait_kigu.py —— 新增羁绊「咒具师」

设计：
  Lv1（2人）：装备 ≥2 件咒具的单位，全属性 +12%
  Lv2（3人）：每装备一件咒具，额外 +8% 体术 / 术式

归属：以咒具/工具战斗的角色（七海建人、伏黑甚尔、禅院真希、三轮霞、冥冥、猪野琢真、机械丸）
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TID = "咒具"
NAME = "咒具师"

# ---------------- 1) traits.json ----------------
tp = os.path.join(ROOT, "data", "raw", "traits.json")
t = json.load(io.open(tp, encoding="utf-8"))
ts = t["traits"] if isinstance(t, dict) and "traits" in t else t

if not any(x["id"] == TID for x in ts):
    ts.append({
        "id": TID,
        "type": "class",
        "name": NAME,
        "color": "#c8a45c",
        "tiers": [
            {"count": 2, "text": "随身咒具：装备 2 件及以上咒具的单位，全属性 +12%。"},
            {"count": 3, "text": "咒具精通：每装备一件咒具，额外获得 +8% 体术与术式。"}
        ]
    })
    json.dump(t, io.open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[trait] 已加入「%s」" % NAME)
else:
    print("[trait] 已存在")

# ---------------- 2) 给角色打标 ----------------
KEYS = ["七海建人", "伏黑甚尔", "禅院真希", "三轮霞", "冥冥", "猪野琢真", "机械丸"]
up = os.path.join(ROOT, "data", "units.json")
d = json.load(io.open(up, encoding="utf-8"))
units = d["units"] if isinstance(d, dict) and "units" in d else d

n = 0
for u in units:
    base = u.get("baseCharacter") or ""
    if any(k in base for k in KEYS):
        tr = u.setdefault("traits", [])
        if TID not in tr:
            # 最多保留 3 个羁绊，避免角色过于全能
            if len(tr) < 3:
                tr.append(TID)
                n += 1
json.dump(d, io.open(up, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[trait] 已给 %d 个角色打上「%s」" % (n, TID))

# ---------------- 3) 引擎实现 ----------------
bp = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(bp, encoding="utf-8").read()
if "咒具" not in s:
    anchor = "    /* —— 阵营羁绊 —— */"
    block = '''    /* —— 咒具师（按携带咒具数量成长） —— */
    if (traits.indexOf('咒具') >= 0 && self._tier(t, '咒具') >= 1) {
      var _ic = (u.def.items || []).length;
      if (_ic >= 2) {
        u.ad *= 1.12; u.spell *= 1.12;
        u.maxHp *= 1.12; u.hp = u.maxHp;                      // Lv1 随身咒具
        if (self._tier(t, '咒具') >= 2) {
          var _b = 1 + 0.08 * _ic;                            // Lv2 咒具精通
          u.ad *= _b; u.spell *= _b;
        }
      }
    }
''' + anchor
    assert anchor in s, "anchor"
    s = s.replace(anchor, block, 1)
    io.open(bp, "w", encoding="utf-8").write(s)
    print("[trait] 引擎已实现")
else:
    print("[trait] 引擎已有实现")
