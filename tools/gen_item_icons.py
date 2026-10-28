# -*- coding: utf-8 -*-
r"""
gen_item_icons.py —— 为 20 件咒具生成矢量图标（SVG）

说明：
  本项目没有 AI 绘图能力，也不适合直接把漫画原图裁下来当图标（版权 / 清晰度 / 风格割裂）。
  所以这里用**手写 SVG** 画一套统一风格的道具图标：
  暗底 + 金线 + 单一物体剪影，和 UI 的「墨与金」基调一致，任意分辨率都清晰。

用法：
    python tools\gen_item_icons.py
输出：
    assets/items/*.svg
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "items")

GOLD = "#e8c85a"
BONE = "#f2e9d8"
DIM = "#8a7a52"
RED = "#d8443f"
JADE = "#4fc79a"
VIOLET = "#a78bfa"
INK = "#120f18"


def frame(body, accent=GOLD):
    """统一外框：暗底圆角 + 描边 + 一点高光。"""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
        '<defs>'
        f'<radialGradient id="g" cx="50%" cy="38%" r="72%">'
        f'<stop offset="0%" stop-color="#2a2338"/><stop offset="62%" stop-color="#171322"/>'
        f'<stop offset="100%" stop-color="{INK}"/></radialGradient>'
        '<linearGradient id="m" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#fff6dd"/><stop offset="46%" stop-color="{GOLD}"/>'
        f'<stop offset="100%" stop-color="{DIM}"/></linearGradient>'
        f'<linearGradient id="mr" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{GOLD}"/><stop offset="100%" stop-color="{DIM}"/></linearGradient>'
        '</defs>'
        '<rect x="1" y="1" width="94" height="94" rx="20" fill="url(#g)"/>'
        f'<rect x="1.5" y="1.5" width="93" height="93" rx="19.5" fill="none" '
        f'stroke="{accent}" stroke-opacity="0.42" stroke-width="1.2"/>'
        '<rect x="5" y="4" width="86" height="40" rx="16" fill="#ffffff" opacity="0.035"/>'
        f'{body}'
        '</svg>'
    )


ART = {}

# ---------------------------------------------------------------- 散件
ART["crystal.svg"] = frame(
    '<path d="M48 14 L70 40 L48 82 L26 40 Z" fill="url(#m)" opacity="0.95"/>'
    '<path d="M48 14 L48 82" stroke="#0d0a14" stroke-opacity="0.5" stroke-width="1.6"/>'
    '<path d="M26 40 L70 40" stroke="#0d0a14" stroke-opacity="0.4" stroke-width="1.4"/>'
    '<path d="M48 20 L58 38 L48 44 L38 38 Z" fill="#fff8e2" opacity="0.55"/>'
)

ART["scroll.svg"] = frame(
    '<rect x="26" y="24" width="44" height="48" rx="5" fill="#efe4c8" opacity="0.9"/>'
    '<rect x="32" y="34" width="32" height="2.6" fill="#7a6a48" opacity="0.75"/>'
    '<rect x="32" y="42" width="32" height="2.6" fill="#7a6a48" opacity="0.75"/>'
    '<rect x="32" y="50" width="22" height="2.6" fill="#7a6a48" opacity="0.75"/>'
    '<rect x="32" y="58" width="27" height="2.6" fill="#7a6a48" opacity="0.55"/>'
    '<rect x="20" y="20" width="10" height="56" rx="5" fill="url(#m)"/>'
    '<rect x="66" y="20" width="10" height="56" rx="5" fill="url(#m)"/>'
)

ART["charm.svg"] = frame(
    '<path d="M48 12 L58 22 L48 30 L38 22 Z" fill="url(#m)"/>'
    '<path d="M48 28 L48 36" stroke="url(#m)" stroke-width="3"/>'
    '<rect x="30" y="34" width="36" height="50" rx="8" fill="#5b1b2c"/>'
    '<rect x="30" y="34" width="36" height="50" rx="8" fill="none" stroke="url(#m)" stroke-width="2"/>'
    '<rect x="43" y="48" width="10" height="24" rx="4" fill="url(#m)" opacity="0.9"/>'
    '<circle cx="48" cy="62" r="4" fill="#5b1b2c"/>'
)

ART["fang.svg"] = frame(
    '<path d="M34 16 C34 16, 66 26, 62 54 C60 70, 48 82, 44 84 '
    'C46 66, 42 50, 30 38 Z" fill="url(#m)"/>'
    '<path d="M38 26 C38 26, 55 34, 54 50" stroke="#fff8e2" stroke-opacity="0.5" '
    'stroke-width="2.4" fill="none"/>'
    '<path d="M30 38 C34 48, 40 56, 44 68" stroke="#0d0a14" stroke-opacity="0.35" '
    'stroke-width="1.6" fill="none"/>'
)

ART["fragment.svg"] = frame(
    '<path d="M30 30 L50 20 L58 44 L40 56 Z" fill="url(#m)"/>'
    '<path d="M58 44 L74 52 L68 76 L46 70 Z" fill="url(#mr)" opacity="0.82"/>'
    '<path d="M20 56 L34 52 L36 72 L22 74 Z" fill="url(#mr)" opacity="0.6"/>'
    '<path d="M34 36 L48 32" stroke="#fff8e2" stroke-opacity="0.45" stroke-width="2"/>'
)

ART["ward.svg"] = frame(
    '<rect x="34" y="14" width="28" height="68" rx="4" fill="#efe4c8" opacity="0.93"/>'
    '<path d="M48 20 L48 34 M40 28 L56 28 M48 40 L48 52 M40 52 L56 52 M48 58 L48 72" '
    'stroke="#8a2b2b" stroke-width="2.8" stroke-linecap="round"/>'
    '<circle cx="48" cy="62" r="5" fill="none" stroke="#8a2b2b" stroke-width="2"/>'
)

ART["kugi.svg"] = frame(
    '<rect x="22" y="22" width="30" height="16" rx="4" fill="url(#m)"/>'
    '<rect x="34" y="38" width="6" height="30" rx="3" fill="#c9b48a"/>'
    '<path d="M58 22 L74 22 L74 30 L58 30 Z" fill="url(#m)"/>'
    '<path d="M66 30 L66 78" stroke="#d7d2c4" stroke-width="5" stroke-linecap="round"/>'
    '<path d="M66 78 L62 84 L70 84 Z" fill="#d7d2c4"/>'
    '<circle cx="66" cy="84" r="2.4" fill="#8a2b2b"/>'
)

ART["zunda.svg"] = frame(
    '<ellipse cx="48" cy="60" rx="28" ry="24" fill="#f5ebd6"/>'
    '<path d="M20 58 C20 40, 34 26, 48 26 C62 26, 76 40, 76 58 '
    'C68 50, 58 46, 48 46 C38 46, 28 50, 20 58 Z" fill="#5f8f3e"/>'
    '<ellipse cx="40" cy="38" rx="5" ry="3.4" fill="#7fbb52" opacity="0.9"/>'
    '<ellipse cx="55" cy="34" rx="4.4" ry="3" fill="#7fbb52" opacity="0.8"/>'
    '<ellipse cx="44" cy="64" rx="9" ry="5" fill="#ffffff" opacity="0.5"/>'
    '<path d="M26 74 C34 82, 62 82, 70 74" stroke="#c9b48a" stroke-width="1.6" fill="none" opacity="0.6"/>'
)

# ---------------------------------------------------------------- 成装
ART["yuyun.svg"] = frame(
    '<rect x="14" y="44" width="26" height="9" rx="4.5" fill="url(#m)"/>'
    '<rect x="40" y="43" width="16" height="11" rx="5" fill="#8a7a52"/>'
    '<rect x="56" y="44" width="26" height="9" rx="4.5" fill="url(#m)"/>'
    '<rect x="30" y="24" width="9" height="26" rx="4.5" fill="url(#m)" opacity="0.9"/>'
    '<rect x="58" y="24" width="9" height="26" rx="4.5" fill="url(#m)" opacity="0.9"/>'
    '<circle cx="48" cy="48" r="4" fill="#fff2c8" opacity="0.85"/>'
    '<path d="M20 48 L36 48" stroke="#fff8e2" stroke-opacity="0.4" stroke-width="2"/>'
)

ART["ao.svg"] = frame(
    '<circle cx="48" cy="48" r="30" fill="none" stroke="url(#m)" stroke-width="4" opacity="0.9"/>'
    '<circle cx="48" cy="48" r="21" fill="none" stroke="url(#m)" stroke-width="3" opacity="0.72"/>'
    '<circle cx="48" cy="48" r="12" fill="none" stroke="url(#m)" stroke-width="2.4" opacity="0.55"/>'
    '<circle cx="48" cy="48" r="5" fill="#cfe4ff"/>'
    '<path d="M48 18 A30 30 0 0 1 76 40" stroke="#cfe4ff" stroke-width="2.6" fill="none" opacity="0.8"/>'
    '<path d="M76 56 A30 30 0 0 1 52 78" stroke="#cfe4ff" stroke-width="2" fill="none" opacity="0.5"/>'
)

ART["finger.svg"] = frame(
    '<path d="M40 16 C52 16, 58 24, 58 34 L58 66 C58 78, 52 84, 46 84 '
    'C40 84, 34 78, 34 66 L34 34 C34 24, 38 16, 40 16 Z" fill="#e6d3bd"/>'
    '<path d="M40 16 C52 16, 58 24, 58 34 L58 44 C50 40, 42 40, 34 44 L34 34 C34 24, 38 16, 40 16 Z" '
    'fill="#c9b49c" opacity="0.7"/>'
    '<rect x="40" y="44" width="12" height="18" rx="5" fill="#cfc6b4"/>'
    '<path d="M34 60 C40 66, 52 66, 58 60" stroke="#8a2b2b" stroke-width="2.4" fill="none" opacity="0.85"/>'
    '<path d="M34 70 L58 70" stroke="#2a1a20" stroke-width="3" opacity="0.6"/>'
)

ART["domain.svg"] = frame(
    '<rect x="18" y="18" width="60" height="60" rx="6" fill="none" stroke="url(#m)" stroke-width="2.6"/>'
    '<circle cx="48" cy="48" r="21" fill="none" stroke="url(#m)" stroke-width="2" opacity="0.75"/>'
    '<path d="M48 12 L48 84 M12 48 L84 48" stroke="url(#m)" stroke-width="1.4" opacity="0.4"/>'
    '<path d="M27 27 L69 69 M69 27 L27 69" stroke="url(#m)" stroke-width="1.2" opacity="0.28"/>'
    '<path d="M48 27 L58 48 L48 69 L38 48 Z" fill="url(#m)" opacity="0.85"/>'
    '<circle cx="48" cy="48" r="4" fill="#ff6b6b"/>'
)

ART["spear.svg"] = frame(
    '<path d="M48 10 L58 30 L48 40 L38 30 Z" fill="url(#m)"/>'
    '<path d="M48 40 L48 84" stroke="#c9b48a" stroke-width="5" stroke-linecap="round"/>'
    '<path d="M40 44 L56 44 L54 52 L42 52 Z" fill="url(#m)" opacity="0.9"/>'
    '<path d="M40 60 L56 60 L54 66 L42 66 Z" fill="url(#m)" opacity="0.75"/>'
    '<path d="M48 14 L48 36" stroke="#fff8e2" stroke-opacity="0.6" stroke-width="1.8"/>'
)

ART["rope.svg"] = frame(
    '<path d="M22 30 C40 18, 56 42, 74 30 C82 24, 82 40, 74 46 '
    'C56 58, 40 34, 22 46 C14 52, 14 36, 22 30 Z" fill="none" '
    'stroke="#2b2434" stroke-width="10" stroke-linejoin="round"/>'
    '<path d="M22 30 C40 18, 56 42, 74 30 C82 24, 82 40, 74 46 '
    'C56 58, 40 34, 22 46 C14 52, 14 36, 22 30 Z" fill="none" '
    'stroke="url(#m)" stroke-width="3.4" stroke-dasharray="7 5"/>'
    '<path d="M74 46 L80 66" stroke="#2b2434" stroke-width="7" stroke-linecap="round"/>'
    '<path d="M74 46 L80 66" stroke="url(#m)" stroke-width="2.2" stroke-dasharray="5 4"/>'
    '<path d="M76 66 L84 74 M76 66 L70 76" stroke="url(#m)" stroke-width="2.4" stroke-linecap="round"/>'
)

ART["chain.svg"] = frame(
    '<rect x="14" y="40" width="20" height="14" rx="7" fill="none" stroke="url(#m)" stroke-width="4"/>'
    '<rect x="30" y="44" width="20" height="14" rx="7" fill="none" stroke="url(#mr)" stroke-width="4"/>'
    '<rect x="46" y="40" width="20" height="14" rx="7" fill="none" stroke="url(#m)" stroke-width="4"/>'
    '<rect x="62" y="44" width="20" height="14" rx="7" fill="none" stroke="url(#mr)" stroke-width="4"/>'
    '<path d="M34 34 L34 26 M58 34 L58 26" stroke="#8a7a52" stroke-width="2" opacity="0.6"/>'
    '<circle cx="34" cy="72" r="5" fill="url(#m)" opacity="0.8"/>'
    '<circle cx="62" cy="72" r="5" fill="url(#m)" opacity="0.55"/>'
)

ART["blade.svg"] = frame(
    '<path d="M56 12 L66 22 L38 50 L30 42 Z" fill="#d8dde6"/>'
    '<path d="M56 12 L66 22 L52 36 L46 30 Z" fill="#f2f6fb" opacity="0.85"/>'
    '<path d="M30 42 L22 50 L34 62 L42 54 Z" fill="url(#m)"/>'
    '<rect x="36" y="52" width="8" height="26" rx="3.4" fill="#3b2a22" '
    'transform="rotate(-45 40 65)"/>'
    '<path d="M38 58 L48 68 M42 54 L52 64" stroke="#c9b48a" stroke-width="1.6" opacity="0.8"/>'
    '<circle cx="26" cy="58" r="3.4" fill="url(#m)"/>'
)

ART["potion.svg"] = frame(
    '<path d="M42 16 L58 16 L58 30 L58 34 C70 40, 74 52, 72 64 '
    'C70 78, 58 84, 48 84 C38 84, 26 78, 24 64 C22 52, 26 40, 38 34 L42 30 Z" '
    'fill="#2c3b46" stroke="url(#m)" stroke-width="2.4"/>'
    '<path d="M29 58 C38 52, 58 52, 67 58 C64 74, 58 80, 48 80 C38 80, 32 74, 29 58 Z" '
    f'fill="{JADE}" opacity="0.55"/>'
    '<rect x="40" y="10" width="20" height="8" rx="3" fill="url(#m)"/>'
    '<path d="M36 62 C42 58, 54 58, 60 62" stroke="#bff5e0" stroke-width="2" fill="none" opacity="0.7"/>'
)

ART["box.svg"] = frame(
    '<path d="M48 16 L78 32 L78 64 L48 80 L18 64 L18 32 Z" fill="#241d2e" stroke="url(#m)" stroke-width="2.4"/>'
    '<path d="M48 16 L78 32 L48 48 L18 32 Z" fill="#3a2f46"/>'
    '<path d="M48 48 L48 80" stroke="url(#m)" stroke-width="2"/>'
    '<path d="M18 32 L48 48 L78 32" fill="none" stroke="url(#m)" stroke-width="1.6" opacity="0.6"/>'
    '<circle cx="48" cy="58" r="7" fill="none" stroke="url(#m)" stroke-width="2.2"/>'
    '<path d="M48 51 L48 65 M41 58 L55 58" stroke="url(#m)" stroke-width="1.8"/>'
    '<circle cx="48" cy="58" r="2.6" fill="#ff6b6b"/>'
)

ART["wing.svg"] = frame(
    '<path d="M62 12 C44 20, 30 34, 26 54 C24 66, 30 76, 40 82 '
    'C44 66, 52 46, 70 26 Z" fill="url(#m)" opacity="0.95"/>'
    '<path d="M62 12 C70 20, 72 32, 66 42 C58 34, 54 28, 52 20 Z" fill="#fff2c8" opacity="0.7"/>'
    '<path d="M40 60 C36 68, 34 74, 34 80 M52 44 C48 56, 46 66, 46 74" '
    'stroke="#0d0a14" stroke-opacity="0.3" stroke-width="1.6" fill="none"/>'
    '<path d="M70 26 C62 34, 56 42, 52 52" stroke="#fff8e2" stroke-opacity="0.4" '
    'stroke-width="2" fill="none"/>'
)

ART["womb.svg"] = frame(
    '<rect x="24" y="18" width="48" height="60" rx="5" fill="#efe4c8" opacity="0.92"/>'
    '<rect x="18" y="14" width="10" height="68" rx="5" fill="url(#m)"/>'
    '<rect x="68" y="14" width="10" height="68" rx="5" fill="url(#m)"/>'
    '<path d="M32 30 C42 24, 56 34, 64 26 M32 46 C44 40, 54 52, 64 44 M32 62 C42 56, 56 66, 64 58" '
    f'stroke="{RED}" stroke-width="2.6" fill="none" opacity="0.8"/>'
    '<circle cx="48" cy="46" r="6" fill="none" stroke="#8a2b2b" stroke-width="1.8" opacity="0.7"/>'
)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, svg in ART.items():
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(svg)
    print("[icons] 生成 %d 个图标 -> assets/items/" % len(ART))
    missing = [n for n in ART if not os.path.exists(os.path.join(OUT, n))]
    if missing:
        print("  缺失:", missing)


if __name__ == "__main__":
    main()
