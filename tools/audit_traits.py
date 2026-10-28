# -*- coding: utf-8 -*-
r"""
audit_traits.py —— 羁绊效果 vs 引擎实现 全面对照

输出：
  A. 每条羁绊的档位、门槛、声明效果
  B. 效果里用到的 mods 键，引擎是否真的消费
  C. 数值分布（哪条明显偏弱/偏强）
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
traits = json.load(io.open(os.path.join(ROOT, "data", "raw", "traits.json"), encoding="utf-8"))
ts = traits["traits"] if isinstance(traits, dict) and "traits" in traits else traits
battle = io.open(os.path.join(ROOT, "js", "core", "battle.js"), encoding="utf-8").read()

# 引擎里所有被读取的 mods 键
used_mods = set(re.findall(r"mods\.([a-zA-Z_]+)", battle))
used_top = set(re.findall(r"u\.([a-zA-Z_]+)\s*(?:[*=+\-<>!]|;|\))", battle))
print("引擎消费的 mods 键：")
print("  " + ", ".join(sorted(used_mods)))
print()

ref_declared = set()
print("=== A. 羁绊档位 ===")
for t in ts:
    print("\n■ %s（%s）" % (t.get("name"), t.get("id")))
    for tier in t.get("tiers", []):
        eff = tier.get("effect") or tier.get("mods") or {}
        label = tier.get("label") or tier.get("desc") or ""
        n = tier.get("count") or tier.get("need") or ""
        print("   %s 需 %s 人 │ %s" % (str(n), str(n), eff))
        if isinstance(eff, dict):
            for k in eff:
                ref_declared.add(k)

print("\n=== B. 声明但引擎没消费的键 ===")
missing = sorted(k for k in ref_declared if k not in used_mods and k not in used_top)
print("  " + (", ".join(missing) if missing else "无 —— 全部有实现"))

print("\n=== C. 档位数量与门槛 ===")
for t in ts:
    tiers = t.get("tiers", [])
    counts = [tier.get("count") or tier.get("need") for tier in tiers]
    print("  %-8s 档位 %d │ 门槛 %s" % (t.get("name"), len(tiers), counts))
