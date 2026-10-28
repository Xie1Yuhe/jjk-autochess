# -*- coding: utf-8 -*-
r"""
add_mahoraga.py —— 彩蛋角色【无限式神】魔虚罗

致敬历史上「式神召唤式神」的 bug：
  · 允许链式召唤（skill.chain = true）
  · 每代数值 = 上一代 × 0.3，即第 n 代 = 本体 × 0.3^n
  · 不设 3 只上限，但设 30 只的硬上限保护帧率
"""
import io
import json
import os
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "data", "units.json")
SRC_IMG = r"C:\Users\谢宇赫\Pictures\魔虚罗.jpg"
UID = "900001"

d = json.load(io.open(UNITS, encoding="utf-8"))
units = d["units"] if isinstance(d, dict) and "units" in d else d

# 已有就跳过
if any(u["id"] == UID for u in units):
    print("[mahoraga] 已存在，跳过")
else:
    # 以带 summon 的伏黑惠为模板，保证 traits / element 等取值合法
    tpl = [u for u in units if u.get("skill", {}).get("type") == "summon"][0]

    unit = dict(tpl)
    unit.update({
        "id": UID,
        "name": "[无限式神] 魔虚罗",
        "baseCharacter": "魔虚罗",
        "variant": "无限式神",
        "wikiTitle": "",
        "wikiUrl": "",
        "wikiComment": "彩蛋角色，非 wiki 内容",
        "release": "彩蛋",
        "cost": 4,
        "costSource": "easter-egg",
        "role": "召唤",
        "hp": 1500,
        "ad": 72,
        "spell": 72,
        "as": 0.72,
        "range": 2,
        "mana": 90,
        "start_mana": 55,
        "rarity": "SSR",
        "tier": "SS",
        "tierName": "彩蛋",
        "playable": True,
        "isEasterEgg": True,
        "design": (
            "彩蛋：致敬历史上「式神无限召唤」的 bug。"
            "允许链式召唤，第 n 代式神数值 = 本体 × 0.3^n；"
            "场上式神越多越强，但每一代都更脆。"
        ),
        "skill": {
            "name": "无限式神",
            "type": "summon",
            "trigger": "mana_full",
            "power": 2.0,
            "chain": True,
            "effect": "召唤 30% 的式神参战；式神也会继续召唤，代数越深越弱",
            "desc": "召唤 30% 的式神；式神可继续召唤（0.3^n 衰减）",
            "confidence": "inferred",
            "source": "easter-egg",
        },
        "ult": {
            "name": "八握剑异戒神将·适应",
            "type": "slam",
            "radius": 2,
            "power": 1.6,
            "panel": "hybrid",
            "hybrid": True,
            "applyTaken": 0.4,
            "combat": True,
            "desc": "对周围 2 格内敌人造成 1.6 倍复合伤害，并使其受到的伤害 +40%",
            "confidence": "inferred",
            "source": "easter-egg",
        },
    })
    units.append(unit)
    # 重新排序：按 cost 稳定排序，保证商店抽取权重正确
    units.sort(key=lambda x: (x.get("cost", 1), str(x.get("id"))))
    if isinstance(d, dict) and "units" in d:
        d["units"] = units
    json.dump(d, io.open(UNITS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[mahoraga] units.json 已加入，共 %d 个棋子" % len(units))

# ---------- 卡图 / 立绘 ----------
os.makedirs(os.path.join(ROOT, "assets", "cards"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "assets", "art"), exist_ok=True)

img = Image.open(SRC_IMG).convert("RGB")
w, h = img.size
# 居中裁成 240:336 的竖版
target = 240 / 336
if w / h > target:
    nw = int(h * target)
    img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
else:
    nh = int(w / target)
    img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))

card = img.resize((240, 336), Image.LANCZOS)
card.save(os.path.join(ROOT, "assets", "cards", UID + ".webp"), "WEBP", quality=86, method=6)

# 立绘尺寸参考已有 art
art_dir = os.path.join(ROOT, "assets", "art")
sample = None
for f in os.listdir(art_dir):
    if f.endswith(".webp"):
        sample = Image.open(os.path.join(art_dir, f)).size
        break
art_size = sample or (512, 720)
art = img.resize(art_size, Image.LANCZOS)
art.save(os.path.join(art_dir, UID + ".webp"), "WEBP", quality=84, method=6)
print("[mahoraga] 卡图 240x336 / 立绘 %s 已生成" % (art_size,))
