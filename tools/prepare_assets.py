# -*- coding: utf-8 -*-
r"""
资产管线：把 Godot 版抓下来的 gamekee 立绘 / 卡面重新处理成网页友好的 WebP。

输入： E:\我想做游戏\咒术自走棋\assets\portraits\   (原 256x256 头像 + 240x336 卡面 + manifest.json)
输出： <webroot>\assets\units\<id>.webp     角色头像（棋盘/卡牌主视觉）
       <webroot>\assets\cards\<id>.webp     卡面立绘（商店大卡 / 详情 / 图鉴 / 标题页）
       <webroot>\assets\grain.webp          全局颗粒噪点叠加层
输出清单：<webroot>\tools\asset_report.json

用法：
    python tools\prepare_assets.py
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC = r"E:\我想做游戏\咒术自走棋\assets\portraits"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_UNITS = os.path.join(ROOT, "assets", "units")
OUT_CARDS = os.path.join(ROOT, "assets", "cards")
UNITS_JSON = os.path.join(ROOT, "data", "units.json")

CARD_W, CARD_H = 240, 336
ICON_SIZE = 256


def ensure(path):
    os.makedirs(path, exist_ok=True)


def save_webp(img, dest, quality=88):
    img.save(dest, "WEBP", quality=quality, method=6)
    return os.path.getsize(dest)


def crop_to_card(icon):
    """没有卡面的角色：用头像按 240:336 比例居中裁切，补成竖幅卡面。"""
    target_ratio = CARD_W / CARD_H
    w, h = icon.size
    cur = w / h
    if cur > target_ratio:          # 太宽 -> 裁两侧
        nw = int(h * target_ratio)
        left = (w - nw) // 2
        box = (left, 0, left + nw, h)
    else:                            # 太高 -> 裁上下
        nh = int(w / target_ratio)
        top = max(0, (h - nh) // 2 - 20)
        box = (0, top, w, top + nh)
    return icon.crop(box).resize((CARD_W, CARD_H), Image.LANCZOS)


def make_grain(size=160, seed=7):
    import random
    rnd = random.Random(seed)
    img = Image.new("L", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            px[x, y] = rnd.randint(96, 160)
    rgba = Image.new("RGBA", (size, size))
    rgba.putalpha(img)
    return rgba


def main():
    ensure(OUT_UNITS)
    ensure(OUT_CARDS)

    manifest = json.load(open(os.path.join(SRC, "manifest.json"), encoding="utf-8"))
    units = json.load(open(UNITS_JSON, encoding="utf-8"))
    icons = manifest["icons"]
    cards = manifest["cards"]

    report = {"units": {}, "total_bytes": 0, "missing": []}

    for u in units:
        uid = u["id"]
        rec = {}

        # ---- 头像 ----
        ipath = os.path.join(SRC, icons[uid])
        icon = Image.open(ipath).convert("RGBA")
        if icon.size != (ICON_SIZE, ICON_SIZE):
            icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
        dest = os.path.join(OUT_UNITS, uid + ".webp")
        rec["icon_bytes"] = save_webp(icon, dest, 86)

        # ---- 卡面 ----
        cname = cards.get(uid)
        if cname:
            card = Image.open(os.path.join(SRC, cname)).convert("RGBA")
            if card.size != (CARD_W, CARD_H):
                card = card.resize((CARD_W, CARD_H), Image.LANCZOS)
        else:
            card = crop_to_card(Image.open(ipath).convert("RGBA"))
            report["missing"].append(uid)
        dest = os.path.join(OUT_CARDS, uid + ".webp")
        rec["card_bytes"] = save_webp(card, dest, 90)

        report["units"][uid] = rec
        report["total_bytes"] += rec["icon_bytes"] + rec["card_bytes"]

    # ---- 颗粒层（全局质感，CSS 里 mix-blend-mode: overlay 铺满） ----
    grain = make_grain(160)
    gdest = os.path.join(ROOT, "assets", "grain.webp")
    report["grain_bytes"] = save_webp(grain, gdest, 72)

    json.dump(report, open(os.path.join(ROOT, "tools", "asset_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("[assets] units=%d  cards=%d  synthesized_cards=%d" %
          (len(units), len(units) - len(report["missing"]), len(report["missing"])))
    print("[assets] total image bytes: %.1f KB" % (report["total_bytes"] / 1024.0))
    print("[assets] grain: %d bytes" % report["grain_bytes"])


if __name__ == "__main__":
    sys.exit(main())
