# -*- coding: utf-8 -*-
r"""
audit_item_effects.py —— 核对咒具文案 vs 实际生效的属性

输出三张表：
  A. 每件咒具的文案、stat 键、引擎是否真的处理该键
  B. 文案说「攻击/体术/伤害」但 stat 键对不上的（疑似 bug）
  C. 大招文案含「全队伤害提升」的角色，其 ult 字段实际是什么
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

items = json.load(io.open(os.path.join(ROOT, "data", "raw", "items.json"), encoding="utf-8"))
battle = io.open(os.path.join(ROOT, "js", "core", "battle.js"), encoding="utf-8").read()

# 从 _applyItem 里抽取实际处理的键
i = battle.index("BattleSim.prototype._applyItem")
j = battle.index("BattleSim.prototype.", i + 40)
seg = battle[i:j]
handled = sorted(set(re.findall(r"st\.([a-zA-Z_]+)", seg)))
print("引擎 _applyItem 实际处理的 stat 键：")
print("  " + ", ".join(handled))
print()

KEY_MEAN = {
    "ad": "体术", "spell": "术式", "hp": "生命", "as": "攻速",
    "start_mana": "初始咒力", "armor": "护甲", "mres": "术式减伤",
    "bf": "黑闪率", "dodge": "闪避", "counter": "反击倍率",
    "regen": "每秒回复", "revive": "复活", "heal_ally": "治疗友军",
    "stun_on_cast": "施法眩晕", "domain_plus": "领域提前", "taken": "受到伤害",
}

print("=== A. 咒具文案 vs stat 键 ===")
problems = []
for it in items:
    stat = it.get("stat") or {}
    keys = list(stat.keys())
    unknown = [k for k in keys if k not in handled]
    if unknown:
        problems.append((it["name"], "未处理的键 " + ",".join(unknown)))
    txt = it.get("text", "")
    label = " / ".join("%s +%s" % (KEY_MEAN.get(k, k), v) for k, v in stat.items())
    print("  %-16s %-22s stat: %-38s %s" % (it["name"], txt, label, ("⚠ " + ",".join(unknown)) if unknown else ""))

print("\n=== B. 文案与 stat 键矛盾 ===")
for it in items:
    txt = it.get("text", "")
    stat = it.get("stat") or {}
    # 文案提到体术却没 ad；提到术式却没 spell；提到攻速却没 as
    issues = []
    if "体术" in txt and "ad" not in stat:
        issues.append("文案说体术，但没有 ad 键")
    if "术式强度" in txt and "spell" not in stat:
        issues.append("文案说术式强度，但没有 spell 键")
    if "攻速" in txt and "as" not in stat:
        issues.append("文案说攻速，但没有 as 键")
    if "攻击" in txt:
        issues.append("文案出现「攻击」字样")
    if issues:
        print("  %-16s %s" % (it["name"], "；".join(issues)))

print("\n=== C. 大招「全队伤害提升」实际实现 ===")
units = json.load(io.open(os.path.join(ROOT, "data", "units.json"), encoding="utf-8"))
us = units["units"] if isinstance(units, dict) and "units" in units else units
seen = set()
for u in us:
    for sec in ("ult", "ultimate"):
        ult = u.get(sec)
        if not isinstance(ult, dict):
            continue
        blob = json.dumps(ult, ensure_ascii=False)
        if "全队伤害提升" not in blob:
            continue
        sig = tuple(sorted(k for k in ult.keys() if ult[k] not in (None, False, 0, "", [], {})))
        if sig in seen:
            continue
        seen.add(sig)
        print("  %s" % u["name"])
        print("    ult 字段: %s" % ", ".join("%s=%s" % (k, json.dumps(ult[k], ensure_ascii=False)[:40]) for k in sig))
        ally = [k for k in ult if "ally" in k.lower() or "amp" in k.lower() or "bf" in k.lower()]
        print("    团队类字段: %s" % (ally or "（无 —— 文案说的全队效果没有对应字段）"))
