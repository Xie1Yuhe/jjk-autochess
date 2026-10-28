# -*- coding: utf-8 -*-
r"""
make_promo.py —— 用真实游戏截图合成宣传视频（MP4）

面向粉丝的宣传片：只讲成品与玩法，不讲开发过程。
  1600x900 / 30fps / 约 42 秒
  每镜：缓慢推镜（Ken Burns）+ 淡入文案 + 0.6s 交叉溶解
  结尾：网址 + 同人声明

依赖：Pillow、imageio-ffmpeg（自带 ffmpeg 二进制）
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

W, H, FPS = 1600, 900, 30
SHOTS = os.path.join(os.environ.get("TEMP", "."), "promo")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "promo.mp4")

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size, bold=False):
    path = FONT_BOLD if bold and os.path.exists(FONT_BOLD) else FONT_REG
    return ImageFont.truetype(path, size)


def cover(img, zoom=1.0, dx=0.0, dy=0.0):
    """等比裁剪填满画布，并按 zoom 放大"""
    base = W / img.width
    scale = base * zoom
    w, h = int(img.width * scale), int(img.height * scale)
    im = img.resize((w, h), Image.LANCZOS)
    x = (w - W) // 2 + int(dx)
    y = (h - H) // 2 + int(dy)
    x = max(0, min(x, w - W))
    y = max(0, min(y, h - H))
    return im.crop((x, y, x + W, y + H))


def shade(img, bottom=0.82):
    """底部压暗，保证文字可读"""
    ov = Image.new("L", (1, H), 0)
    px = ov.load()
    for y in range(H):
        t = y / H
        v = int(255 * (bottom * max(0.0, (t - 0.42) / 0.58) ** 1.5))
        px[0, y] = min(255, v)
    mask = ov.resize((W, H))
    dark = Image.new("RGB", (W, H), (4, 3, 8))
    return Image.composite(dark, img, mask.point(lambda v: int(v * 0.9)))


def text_layer(title, sub, tag=None):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 96
    y = H - 250
    if tag:
        f = font(28, False)
        d.text((x, y - 62), tag, font=f, fill=(255, 209, 102, 235))
    f1 = font(62, True)
    d.text((x + 2, y + 2), title, font=f1, fill=(0, 0, 0, 160))
    d.text((x, y), title, font=f1, fill=(255, 250, 240, 255))
    if sub:
        f2 = font(30, False)
        d.text((x, y + 86), sub, font=f2, fill=(206, 198, 214, 235))
    return layer


def end_card():
    img = Image.new("RGB", (W, H), (8, 6, 14))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = (int(10 + 26 * t), int(8 + 12 * t), int(18 + 40 * t))
        d.line([(0, y), (W, y)], fill=c)
    # 光晕
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W // 2 - 520, -260, W // 2 + 520, 340], fill=(90, 60, 20))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.55)

    d = ImageDraw.Draw(img)
    f0 = font(30, False)
    d.text((W // 2, 250), "JUJUTSU KAISEN · PHANTOM PARADE · FAN AUTO CHESS",
           font=f0, fill=(200, 190, 210), anchor="mm")
    f1 = font(96, True)
    d.text((W // 2, 356), "咒 术 回 战", font=f1, fill=(255, 226, 150), anchor="mm")
    f1b = font(54, True)
    d.text((W // 2, 452), "幻影夜行 · 自走棋", font=f1b, fill=(255, 246, 232), anchor="mm")

    f2 = font(30, False)
    d.text((W // 2, 556), "浏览器直接开玩 · 无需下载", font=f2, fill=(210, 202, 218), anchor="mm")
    f3 = font(40, True)
    d.text((W // 2, 636), "jjk-autochess.netlify.app", font=f3, fill=(140, 230, 255), anchor="mm")

    f4 = font(22, False)
    d.text((W // 2, 812), "非商业同人作品 · 角色与世界版权归芥见下下 / 集英社 / 东宝 / サムザップ 所有",
           font=f4, fill=(150, 144, 160), anchor="mm")
    return img


SCENES = [
    dict(img="01_title.png", tag="JUJUTSU KAISEN · FAN AUTO CHESS",
         title="咒术回战 · 幻影夜行 自走棋",
         sub="111 名术师与咒灵  ·  10 条羁绊  ·  5 组异格联动", dur=5.0, zoom=1.02),
    dict(img="02_buy.png", tag="① 组建队伍",
         title="商店同时出售术师与咒具",
         sub="同名牌自动合成升星 · 咒具两件组件即可合体", dur=7.5, zoom=1.06),
    dict(img="03_battle.png", tag="② 自动战斗",
         title="站位、属性克制、羁绊档位决定胜负",
         sub="每张棋子都有独立招牌技与专属必杀", dur=8.0, zoom=1.05),
    dict(img="04_result.png", tag="③ 连胜滚雪球",
         title="利息 + 连胜 + 血量，一路打到 0 血",
         sub="三档难度 · 每局约 15 分钟", dur=7.0, zoom=1.04),
]


def main():
    frames_seq = []
    for sc in SCENES:
        p = os.path.join(SHOTS, sc["img"])
        if not os.path.exists(p):
            print("缺少截图:", p)
            return 1
        frames_seq.append((Image.open(p).convert("RGB"), sc))
    end = (end_card(), dict(tag=None, title=None, sub=None, dur=6.5, zoom=1.0))

    timeline = []
    t = 0.0
    for img, sc in frames_seq + [end]:
        timeline.append(dict(start=t, dur=sc["dur"], img=img, sc=sc))
        t += sc["dur"] - 0.6        # 0.6s 交叠
    total = timeline[-1]["start"] + timeline[-1]["dur"]

    # 预渲染每镜的文案层与静帧
    for item in timeline:
        sc = item["sc"]
        item["base"] = shade(cover(item["img"], 1.0))
        if sc.get("title"):
            item["text"] = text_layer(sc["title"], sc.get("sub"), sc.get("tag"))
        else:
            item["text"] = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    n_frames = int(total * FPS)
    print("总时长 %.1fs，%d 帧" % (total, n_frames))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(n_frames):
        t = i / FPS
        idx = 0
        for k, item in enumerate(timeline):
            if t >= item["start"]:
                idx = k
        cur = timeline[idx]
        k = (t - cur["start"]) / cur["dur"]
        k = max(0.0, min(1.0, k))
        img = cover(cur["img"], 1.0 + (cur["sc"]["zoom"] - 1.0) * k)
        if cur["sc"].get("title"):
            img = shade(img)
        # 文案淡入
        alpha = min(1.0, max(0.0, (t - cur["start"]) / 0.6))
        if alpha > 0:
            txt = cur["text"]
            if alpha < 1.0:
                txt = txt.copy()
                a = txt.split()[3].point(lambda v: int(v * alpha))
                txt.putalpha(a)
            img = Image.alpha_composite(img.convert("RGBA"), txt).convert("RGB")
        # 交叉溶解
        nxt = timeline[idx + 1] if idx + 1 < len(timeline) else None
        if nxt:
            fade_start = nxt["start"]
            if t >= fade_start:
                a = min(1.0, (t - fade_start) / 0.6)
                nimg = cover(nxt["img"], 1.0)
                if nxt["sc"].get("title"):
                    nimg = shade(nimg)
                img = Image.blend(img, nimg, a)
        proc.stdin.write(img.tobytes())
        if i % 150 == 0:
            print("  帧 %d/%d" % (i, n_frames))

    proc.stdin.close()
    proc.wait()
    size = os.path.getsize(OUT) / 1048576 if os.path.exists(OUT) else 0
    print("输出: %s (%.1f MB, %.1fs)" % (OUT, size, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
