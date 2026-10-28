# -*- coding: utf-8 -*-
r"""
make_promo2.py —— 苹果发布会风格的宣传片（约 95 秒）

设计原则：
  · 一镜一个信息点，节奏慢、留白多
  · 数字逐个计数弹出，文字淡入上浮（ease-out）
  · 截图缓慢推镜 + 细线标注指向 UI 元素
  · 咒具合成用卡片动效演示
  · 1600x900 / 30fps

输出：docs/promo.mp4
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

W, H, FPS = 1600, 900, 30
SHOTS = os.path.join(os.environ.get("TEMP", "."), "promo")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "promo_v2.mp4")

F_REG = r"C:\Windows\Fonts\msyh.ttc"
F_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
GOLD = (255, 214, 128)
CYAN = (128, 226, 255)
WHITE = (255, 252, 246)
GRAY = (176, 170, 188)
BG = (8, 6, 14)


def F(size, bold=False):
    return ImageFont.truetype(F_BOLD if bold else F_REG, size)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- 画布工具
def canvas():
    return Image.new("RGB", (W, H), BG)


def vgrad(img, top=(10, 8, 16), bot=(4, 3, 8)):
    g = Image.new("RGB", (1, H))
    px = g.load()
    for y in range(H):
        k = y / H
        px[0, y] = (int(top[0] + (bot[0] - top[0]) * k),
                    int(top[1] + (bot[1] - top[1]) * k),
                    int(top[2] + (bot[2] - top[2]) * k))
    return Image.composite(g.resize((W, H)), img, Image.new("L", (W, H), 90))


def glow(img, cx, cy, r, color, strength=0.5):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.55))
    return Image.blend(img, Image.blend(img, layer, 1.0), strength)


def cover(img, zoom=1.0, ox=0.0, oy=0.0):
    s = (W / img.width) * zoom
    w, h = max(W, int(img.width * s)), max(H, int(img.height * s))
    im = img.resize((w, h), Image.LANCZOS)
    x = int((w - W) / 2 + ox * (w - W) / 2)
    y = int((h - H) / 2 + oy * (h - H) / 2)
    x = max(0, min(x, w - W))
    y = max(0, min(y, h - H))
    return im.crop((x, y, x + W, y + H))


def dim(img, a=0.55):
    d = Image.new("RGB", (W, H), BG)
    return Image.blend(img, d, a)


def text(img, s, xy, size, color=WHITE, bold=True, anchor="la", alpha=1.0, spacing=0):
    """用 textbbox 精确居中，不用 Pillow 的 anchor（TTC 字体下不准）"""
    if alpha <= 0:
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = F(size, bold)
    bb = d.textbbox((0, 0), s, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = xy
    if "m" in anchor[0:1] or anchor.startswith("m"):
        x = x - tw / 2 - bb[0]
    elif anchor.startswith("r"):
        x = x - tw - bb[0]
    else:
        x = x - bb[0]
    if anchor.endswith("m"):
        y = y - th / 2 - bb[1]
    elif anchor.endswith("s") or anchor.endswith("a"):
        y = y - bb[3]
    else:
        y = y - bb[1]
    d.text((x, y), s, font=f, fill=color + (int(255 * alpha),))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def callout(img, x, y, label, prog, side="right", color=CYAN, up=False):
    """细线 + 圆点 + 标签；空间不够时自动翻到另一侧，保证文字不出画面"""
    if prog <= 0:
        return img
    f = F(26, False)
    probe = ImageDraw.Draw(img)
    bb = probe.textbbox((0, 0), label, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    L = 130
    pad = 18
    # 自动翻边
    if side == "right" and x + L + pad + tw > W - 28:
        side = "left"
    elif side == "left" and x - L - pad - tw < 28:
        side = "right"
    # 竖直方向也夹紧
    y = max(th, min(y, H - th))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    Le = L * ease_out(prog)
    dx = Le if side == "right" else -Le
    d.line([(x, y), (x + dx, y)], fill=color + (210,), width=2)
    d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color + (255,))
    if prog > 0.45:
        a = int(255 * min(1.0, (prog - 0.45) / 0.4))
        if side == "right":
            tx = x + dx + pad - bb[0]
        else:
            tx = x + dx - pad - tw - bb[0]
        ty = y - th / 2 - bb[1] + 1
        d.text((tx, ty), label, font=f, fill=WHITE + (a,))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def line_grow(img, x0, y0, x1, y1, prog, color=GOLD, w=3):
    if prog <= 0:
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    p = ease_out(prog)
    d.line([(x0, y0), (x0 + (x1 - x0) * p, y0 + (y1 - y0) * p)],
           fill=color + (200,), width=w)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# ---------------------------------------------------------------- 各镜头
def sc_title(t):
    img = canvas()
    img = vgrad(img, (14, 11, 24), (4, 3, 8))
    img = glow(img, W // 2, 240, 520, (70, 45, 18), 0.6)
    k = ease_out(t / 1.4)
    img = text(img, "JUJUTSU KAISEN  ·  PHANTOM PARADE  ·  FAN AUTO CHESS",
               (W // 2, 300), 24, GRAY, False, "mm", alpha=k)
    k2 = ease_out((t - 0.5) / 1.2)
    img = text(img, "咒 术 回 战", (W // 2, int(400 + 26 * (1 - k2))), 104, GOLD, True, "mm", alpha=k2)
    k3 = ease_out((t - 1.1) / 1.2)
    img = text(img, "幻影夜行 · 自走棋", (W // 2, int(500 + 22 * (1 - k3))), 52, WHITE, True, "mm", alpha=k3)
    k4 = ease_out((t - 2.0) / 1.2)
    img = text(img, "浏览器直接开玩", (W // 2, 600), 28, GRAY, False, "mm", alpha=k4)
    return img


def sc_statement(t, headline, sub=None, dur=5.5):
    img = canvas()
    img = vgrad(img, (12, 10, 22), (4, 3, 8))
    img = glow(img, W // 2, H // 2, 460, (48, 34, 70), 0.45)
    k = ease_out(t / 0.9)
    img = text(img, headline, (W // 2, int(430 + 24 * (1 - k))), 58, WHITE, True, "mm", alpha=k)
    if sub:
        k2 = ease_out((t - 0.7) / 1.0)
        img = text(img, sub, (W // 2, int(510 + 18 * (1 - k2))), 30, GRAY, False, "mm", alpha=k2)
    return img


def sc_stats(t):
    img = canvas()
    img = vgrad(img, (12, 10, 22), (4, 3, 8))
    img = glow(img, W // 2, 380, 520, (46, 40, 80), 0.4)
    img = text(img, "这一盘里有什么", (W // 2, 150), 28, GRAY, False, "mm", alpha=ease_out(t / 0.8))
    data = [(111, "名术师与咒灵"), (10, "条羁绊"), (20, "件咒具"), (5, "组异格联动")]
    xs = [W // 2 + (i - 1.5) * 350 for i in range(4)]
    for i, (n, lab) in enumerate(data):
        st = 0.5 + i * 0.55
        p = (t - st) / 1.5
        if p <= 0:
            continue
        e = ease_out(min(1.0, p))
        val = int(round(n * e))
        img = text(img, str(val), (xs[i], 400), 108, GOLD if i == 0 else WHITE, True, "mm", alpha=min(1.0, p * 2))
        img = text(img, lab, (xs[i], 500), 24, GRAY, False, "mm", alpha=ease_out((p - 0.5) / 0.6))
    return img


def sc_shot(t, shot, zoom0, zoom1, pan=(0, 0), calls=None, dur=8.0):
    """截图推镜 + 依次出现的标注"""
    img = dim(cover(shot, zoom0 + (zoom1 - zoom0) * ease_in_out(t / dur), pan[0], pan[1]), 0.30)
    if calls:
        for i, c in enumerate(calls):
            p = (t - c.get("at", 0.6 + i * 0.9)) / 0.8
            img = callout(img, c["x"], c["y"], c["label"], p,
                          c.get("side", "right"), c.get("color", CYAN))
    return img


def sc_merge(t):
    """咒具合成演示：两个组件 → 成品"""
    img = canvas()
    img = vgrad(img, (12, 10, 22), (4, 3, 8))
    img = glow(img, W // 2, H // 2, 420, (40, 60, 70), 0.35)
    img = text(img, "咒具可以合体", (W // 2, 190), 46, WHITE, True, "mm",
               alpha=ease_out(t / 0.8))

    cards = [(W // 2 - 300, "咒力结晶", 0.0), (W // 2 + 300, "体术卷轴", 0.35)]
    cyber = 240
    for i, (cx, name, st) in enumerate(cards):
        p = (t - 0.6 - st) / 0.9
        if p <= 0:
            continue
        e = ease_out(p)
        x = int(cx + (W // 2 - 210 if i == 0 else W // 2 + 210 - cx) * (e * 0.55))
        y = 400
        box = [x - cyber // 2, y - cyber // 2, x + cyber // 2, y + cyber // 2]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle(box, 18, fill=(255, 255, 255, 14),
                            outline=(120, 200, 255, 150), width=2)
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        img = text(img, name, (x, y), 26, WHITE, True, "mm", alpha=min(1.0, p * 1.5))

    if t > 2.1:
        k = ease_out((t - 2.1) / 0.5)
        img = text(img, "+", (W // 2, 400), 64, CYAN, True, "mm", alpha=k)

    if t > 2.7:
        k = ease_out((t - 2.7) / 0.9)
        img = text(img, "合 成", (W // 2, 300), 26, GRAY, False, "mm", alpha=k)
        img = text(img, "咒具 · 屠坐魔", (W // 2, 620), 44, GOLD, True, "mm", alpha=k)
        img = glow(img, W // 2, 400, 200, (90, 70, 20), 0.5 * k)
        img = text(img, "两件组件即可成型", (W // 2, 690), 24, GRAY, False, "mm", alpha=k)
    return img


def sc_end(t):
    img = canvas()
    img = vgrad(img, (16, 12, 26), (4, 3, 8))
    img = glow(img, W // 2, 260, 520, (70, 45, 18), 0.6)
    k = ease_out(t / 1.0)
    img = text(img, "JUJUTSU KAISEN · PHANTOM PARADE · FAN AUTO CHESS",
               (W // 2, 250), 24, GRAY, False, "mm", alpha=k)
    img = text(img, "咒 术 回 战", (W // 2, int(360 + 20 * (1 - ease_out((t - .3) / 1.0)))), 96, GOLD, True, "mm",
               alpha=ease_out((t - 0.3) / 1.0))
    img = text(img, "幻影夜行 · 自走棋", (W // 2, 456), 50, WHITE, True, "mm", alpha=ease_out((t - 0.8) / 1.0))
    img = text(img, "浏览器直接开玩 · 无需下载", (W // 2, 548), 28, GRAY, False, "mm", alpha=ease_out((t - 1.3) / 1.0))
    k5 = ease_out((t - 1.8) / 1.0)
    img = text(img, "jjk-autochess.netlify.app", (W // 2, 626), 42, CYAN, True, "mm", alpha=k5)
    img = text(img, "非商业同人作品 · 角色与世界版权归芥见下下 / 集英社 / 东宝 / サムザップ 所有",
               (W // 2, 812), 21, (150, 144, 160), False, "mm", alpha=ease_out((t - 2.4) / 1.0))
    return img


# ---------------------------------------------------------------- 时间线
def build():
    shots = {}
    for name in ("01_title.png", "02_buy.png", "03_battle.png", "04_result.png"):
        p = os.path.join(SHOTS, name)
        shots[name] = Image.open(p).convert("RGB") if os.path.exists(p) else None

    S = []
    def add(kind, dur, **kw):
        S.append(dict(kind=kind, dur=dur, **kw))

    add("title", 5.5)
    add("statement", 2.8, headline="把《幻影夜行》", sub="做成了一盘能自己下完的自走棋")
    add("statement", 2.8, headline="一局十五分钟", sub="组队 · 布阵 · 看他们自己打")
    add("stats", 5.2)
    add("shot", 7.5, shot="02_buy.png", zoom0=1.06, zoom1=1.16, pan=(-0.1, 0),
        calls=[dict(x=300, y=700, label="角色卡：可升星时高亮", at=0.7),
               dict(x=1290, y=760, label="咒具区：能合体时绿框", at=1.5, color=(120, 255, 190)),
               dict(x=1430, y=380, label="羁绊实时统计", at=2.3)])
    add("merge", 5.0)
    add("shot", 8.5, shot="03_battle.png", zoom0=1.10, zoom1=1.22, pan=(0.08, 0.05),
        calls=[dict(x=1420, y=140, label="羁绊档位", at=0.6),
               dict(x=230, y=300, label="棋子必杀槽", at=1.4),
               dict(x=900, y=250, label="属性克制 · 行克幻 / 夜克影", at=2.2, color=(255, 170, 120))])
    add("statement", 3.0, headline="站位、克制、羁绊", sub="三者叠加才是赢法")
    add("shot", 7.0, shot="04_result.png", zoom0=1.05, zoom1=1.14, pan=(0.0, -0.05),
        calls=[dict(x=800, y=250, label="利息 + 连胜 + 血量", at=0.6),
               dict(x=800, y=560, label="赢了继续滚，输了掉血", at=1.5, color=(255, 170, 120))])
    add("end", 7.5)
    return S, shots


def main():
    seq, shots = build()
    for s in seq:
        if s["kind"] == "shot" and shots.get(s["shot"]) is None:
            print("缺截图:", s["shot"])
            return 1
    total = sum(s["dur"] for s in seq) - 0.55 * (len(seq) - 1)
    print("总时长 %.1fs / %d 镜" % (total, len(seq)))

    # 起点时间
    t0, starts = 0.0, []
    for s in seq:
        starts.append(t0)
        t0 += s["dur"] - 0.55

    n = int(total * FPS)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(n):
        t = i / FPS
        idx = 0
        for k, st in enumerate(starts):
            if t >= st - 1e-6:
                idx = k
        s = seq[idx]
        lt = t - starts[idx]
        if s["kind"] == "title":
            img = sc_title(lt)
        elif s["kind"] == "statement":
            img = sc_statement(lt, s["headline"], s.get("sub"))
        elif s["kind"] == "stats":
            img = sc_stats(lt)
        elif s["kind"] == "merge":
            img = sc_merge(lt)
        elif s["kind"] == "end":
            img = sc_end(lt)
        else:
            img = sc_shot(lt, shots[s["shot"]], s["zoom0"], s["zoom1"],
                          s.get("pan", (0, 0)), s.get("calls"), s["dur"])

        # 交叉溶解
        if idx + 1 < len(seq):
            nt = starts[idx + 1]
            if t >= nt:
                a = ease_in_out((t - nt) / 0.55)
                nsl = seq[idx + 1]
                if nsl["kind"] == "shot":
                    nimg = sc_shot(0, shots[nsl["shot"]], nsl["zoom0"], nsl["zoom1"],
                                   nsl.get("pan", (0, 0)), None, nsl["dur"])
                elif nsl["kind"] == "title":
                    nimg = sc_title(0)
                elif nsl["kind"] == "stats":
                    nimg = sc_stats(0)
                elif nsl["kind"] == "merge":
                    nimg = sc_merge(0)
                elif nsl["kind"] == "end":
                    nimg = sc_end(0)
                else:
                    nimg = sc_statement(0, nsl["headline"], nsl.get("sub"))
                img = Image.blend(img, nimg, a)

        proc.stdin.write(img.tobytes())
        if i % 300 == 0:
            print("  %d/%d" % (i, n))

    proc.stdin.close()
    proc.wait()
    print("输出 %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main())
